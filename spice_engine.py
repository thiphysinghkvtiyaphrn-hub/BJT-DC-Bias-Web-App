"""ngspice adapter for the Lab 04 Common-Emitter amplifier simulator.

This module owns everything that touches the external simulator: it locates
the ``ngspice`` executable, writes a netlist, runs it in an isolated working
directory, and parses the ASCII results back into Python lists. It knows
nothing about Flask, HTML or charts.

Every number returned here comes from a real ngspice run; nothing is
hard-coded. When the engine is missing, fails or times out, the caller gets a
``SpiceError`` subclass instead of partial or invented data.
"""

from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ENGINE_NAME = "ngspice"
DEFAULT_TIMEOUT_S = 30.0

# AC sweep used for every Bode run. It spans 0.1 Hz .. 500 MHz so that both
# -3 dB corners of the reference circuit fall inside the sweep; if a corner
# still falls outside, the app says so instead of inventing a number.
AC_SWEEP = {"dec": 20, "fstart": 0.1, "fstop": 500e6}

# The Lab 04 handout says to use the model named by the instructor starter
# kit. No starter kit was available for this build, so one documented vendor
# model is used instead and reported in the UI, README and validation notes.
BJT_MODEL_NAME = "Q2N3904"
BJT_MODEL_CARD = (
    "IS=6.734f XTI=3 EG=1.11 VAF=74.03 BF=416.4 NE=1.259 ISE=6.734f "
    "IKF=66.78m XTB=1.5 BR=.7371 NC=2 ISC=0 IKR=0 RC=1 CJC=3.638p "
    "MJC=.3085 VJC=.75 FC=.5 CJE=4.493p MJE=.2593 VJE=.75 TR=239.5n "
    "TF=301.2p ITF=.4 VTF=4 XTF=2 RB=10"
)
BJT_MODEL_SOURCE = (
    "ON Semiconductor 2N3904 Gummel-Poon card (the vendor model distributed "
    "with ngspice examples); not the course starter kit"
)

# Hard limits that keep a student typo from becoming a 20-minute simulation.
LIMITS = {
    "vcc": (0.0, 60.0),
    "r1": (1.0, 1e7),
    "r2": (1.0, 1e7),
    "rc": (1.0, 1e7),
    "re": (1.0, 1e7),
    "rl": (1.0, 1e7),
    "cin": (1e-12, 1e-2),
    "cout": (1e-12, 1e-2),
    "amp": (1e-6, 5.0),
    "freq": (1.0, 1e6),
}

LABELS = {
    "vcc": "VCC",
    "r1": "R1",
    "r2": "R2",
    "rc": "RC",
    "re": "RE",
    "rl": "RL",
    "cin": "Cin",
    "cout": "Cout",
    "amp": "Source amplitude",
    "freq": "Source frequency",
}

UNITS = {
    "vcc": "V",
    "r1": "kΩ",
    "r2": "kΩ",
    "rc": "kΩ",
    "re": "kΩ",
    "rl": "kΩ",
    "cin": "µF",
    "cout": "µF",
    "amp": "mV",
    "freq": "Hz",
}

KILO_FIELDS = ("r1", "r2", "rc", "re", "rl")
MICRO_FIELDS = ("cin", "cout")
MILLI_FIELDS = ("amp",)

ANALYSES = {
    "dc": "DC operating point (.op)",
    "ac": "AC sweep (.ac)",
    "tran": "Transient (.tran)",
}


class SpiceError(RuntimeError):
    """Base class: the run produced no trustworthy data."""


class SpiceNotFound(SpiceError):
    """The ngspice executable could not be located."""


class SpiceTimeout(SpiceError):
    """The solver exceeded the wall-clock budget."""


class SpiceRunError(SpiceError):
    """The solver started but exited badly or wrote no usable output."""


# --------------------------------------------------------------------------
# Parameters
# --------------------------------------------------------------------------


@dataclass
class CeParams:
    """One CE voltage-divider operating point, all values in SI units."""

    vcc: float = 12.0
    r1: float = 100e3
    r2: float = 22e3
    rc: float = 2.2e3
    re: float = 1e3
    rl: float = 10e3
    cin: float = 10e-6
    cout: float = 10e-6
    amp: float = 10e-3
    freq: float = 1e3

    def validate(self) -> list[str]:
        """Return human readable problems; an empty list means valid."""
        errors = []
        for name, (low, high) in LIMITS.items():
            value = getattr(self, name)
            label = LABELS[name]
            if not math.isfinite(value):
                errors.append(f"{label} must be a finite number.")
            elif value <= low:
                errors.append(f"{label} must be greater than {low:g} {UNITS[name]}.")
            elif value > high:
                errors.append(f"{label} must not exceed {high:g} {UNITS[name]}.")
        return errors


# --------------------------------------------------------------------------
# Engine discovery
# --------------------------------------------------------------------------

_ENGINE_CACHE: dict[str, str] | None = None


def _candidate_paths() -> list[str]:
    paths = []
    env = os.environ.get("NGSPICE_BIN")
    if env:
        paths.append(env)
    for name in ("ngspice_con", "ngspice"):
        found = shutil.which(name)
        if found:
            paths.append(found)
    project = Path(__file__).resolve().parent
    for rel in (
        Path("tools") / "ngspice" / "ucrt64" / "bin" / "ngspice_con.exe",
        Path("tools") / "ngspice" / "bin" / "ngspice_con.exe",
        Path("tools") / "ngspice" / "bin" / "ngspice",
    ):
        candidate = project / rel
        if candidate.exists():
            paths.append(str(candidate))
    return paths


def find_ngspice() -> str:
    """Absolute path of the solver, or raise :class:`SpiceNotFound`."""
    for candidate in _candidate_paths():
        if candidate and Path(candidate).exists():
            return str(Path(candidate).resolve())
    raise SpiceNotFound(
        "ngspice was not found. Install it, put ngspice on PATH, or set the "
        "NGSPICE_BIN environment variable to the executable."
    )


def engine_info() -> dict:
    """Describe the engine once; safe to call on every request."""
    global _ENGINE_CACHE
    if _ENGINE_CACHE is None:
        info = {
            "name": ENGINE_NAME,
            "available": False,
            "version": None,
            "path": None,
            "model": BJT_MODEL_NAME,
            "model_source": BJT_MODEL_SOURCE,
            "error": None,
        }
        try:
            path = find_ngspice()
            proc = subprocess.run(
                [path, "-v"],
                capture_output=True,
                text=True,
                timeout=15,
                shell=False,
            )
            match = re.search(r"ngspice-(\d+[.\d]*)", proc.stdout + proc.stderr)
            info.update(
                available=True,
                path=path,
                version=match.group(1) if match else "unknown",
            )
        except SpiceNotFound as exc:
            info["error"] = str(exc)
        except (OSError, subprocess.SubprocessError) as exc:
            info["error"] = f"ngspice could not be executed: {exc}"
        _ENGINE_CACHE = info
    return dict(_ENGINE_CACHE)


def reset_engine_cache() -> None:
    """Drop the cached engine probe (used by tests)."""
    global _ENGINE_CACHE
    _ENGINE_CACHE = None


# --------------------------------------------------------------------------
# Netlist
# --------------------------------------------------------------------------


def _num(value: float) -> str:
    """Format a validated float for a netlist: no separators, no surprises."""
    return f"{value:.6g}"


def tran_settings(freq: float) -> tuple[float, float]:
    """Pick (tstep, tstop) covering five cycles of the source."""
    tstop = min(max(5.0 / freq, 1e-6), 0.5)
    tstep = tstop / 2000.0
    return tstep, tstop


def build_netlist(params: CeParams, analysis: str) -> str:
    """Return a complete batch netlist for one analysis mode."""
    if analysis not in ANALYSES:
        raise ValueError(f"Unknown analysis {analysis!r}")

    if analysis == "dc":
        commands = [
            "op",
            "print v(base) v(emit) v(coll) @q1[ic] @q1[ib]",
        ]
    elif analysis == "ac":
        commands = [
            f"ac dec {AC_SWEEP['dec']} {_num(AC_SWEEP['fstart'])} "
            f"{_num(AC_SWEEP['fstop'])}",
            "wrdata ac.txt vdb(out) vp(out)",
        ]
    else:
        tstep, tstop = tran_settings(params.freq)
        commands = [
            f"tran {_num(tstep)} {_num(tstop)}",
            "wrdata tran.txt v(in) v(out)",
        ]

    lines = [
        "* ENG29 2121 Lab 04 - CE voltage-divider amplifier",
        f"* analysis: {analysis}",
        "* generated by spice_engine.py; values are SI units",
        f"VCC vcc 0 DC {_num(params.vcc)}",
        f"VIN in 0 DC 0 AC 1 SIN(0 {_num(params.amp)} {_num(params.freq)})",
        f"R1 vcc base {_num(params.r1)}",
        f"R2 base 0 {_num(params.r2)}",
        f"RC vcc coll {_num(params.rc)}",
        f"RE emit 0 {_num(params.re)}",
        f"CIN in base {_num(params.cin)}",
        f"COUT coll out {_num(params.cout)}",
        f"RL out 0 {_num(params.rl)}",
        f"Q1 coll base emit {BJT_MODEL_NAME}",
        f".model {BJT_MODEL_NAME} NPN ({BJT_MODEL_CARD})",
        "",
        ".control",
        "set wr_singlescale",
        "set wr_vecnames",
        *commands,
        "quit",
        ".endc",
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Running
# --------------------------------------------------------------------------


@dataclass
class SpiceRun:
    """Everything one solver invocation produced, for display and auditing."""

    run_id: str
    analysis: str
    started_utc: str
    netlist: str
    log: str
    elapsed_ms: int
    engine: dict
    data: dict = field(default_factory=dict)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _tail(text: str, limit: int = 6000) -> str:
    text = text.strip()
    return text if len(text) <= limit else "…\n" + text[-limit:]


def _solver_failed(log: str) -> str | None:
    """Return the first fatal-looking solver message, if any."""
    for line in log.splitlines():
        stripped = line.strip()
        if "code model" in stripped.lower():
            # XSPICE .cm files are optional for this circuit; ngspice warns
            # when it cannot find them and continues normally.
            continue
        if re.match(r"^(Error|Fatal error|doAnalyses:)\b", stripped):
            return stripped
        if "singular matrix" in stripped.lower():
            return stripped
    return None


def _engine_env(exe: str, workdir: Path) -> dict:
    """Environment that lets a portable ngspice find its own support files.

    The MSYS2 build ships a ``spinit`` with absolute ``/ucrt64/...`` code-model
    paths. This circuit uses none of those XSPICE models, so a minimal spinit is
    written into the run directory instead of patching the vendored tool.
    """
    env = dict(os.environ)
    root = Path(exe).resolve().parent.parent
    lib = root / "lib" / "ngspice"
    if lib.is_dir():
        env["SPICE_LIB_DIR"] = str(lib)
    (workdir / "spinit").write_text(
        "* Lab 04 minimal spinit: no XSPICE code models are used.\n"
        "unset osdi_enabled\n",
        encoding="utf-8",
    )
    env["SPICE_SCRIPTS"] = str(workdir)
    return env


def run_analysis(params: CeParams, analysis: str, timeout: float | None = None) -> SpiceRun:
    """Execute one analysis and parse the result. Raises SpiceError on failure."""
    errors = params.validate()
    if errors:
        raise ValueError("; ".join(errors))

    exe = find_ngspice()
    timeout = timeout if timeout is not None else float(
        os.environ.get("NGSPICE_TIMEOUT", DEFAULT_TIMEOUT_S)
    )
    netlist = build_netlist(params, analysis)
    run_id = uuid.uuid4().hex[:8]
    started = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")

    workdir = Path(tempfile.mkdtemp(prefix=f"ce_{analysis}_{run_id}_"))
    try:
        cir = workdir / "circuit.cir"
        cir.write_text(netlist, encoding="utf-8")
        clock = time.perf_counter()
        try:
            proc = subprocess.run(
                [exe, "-b", "-o", "run.log", cir.name],
                cwd=str(workdir),
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
                env=_engine_env(exe, workdir),
            )
        except subprocess.TimeoutExpired as exc:
            raise SpiceTimeout(
                f"ngspice did not finish within {timeout:.0f} s. "
                "Reduce the frequency or try again."
            ) from exc
        elapsed_ms = int((time.perf_counter() - clock) * 1000)

        log = _read_text(workdir / "run.log") or (proc.stdout or "")
        if proc.returncode != 0:
            raise SpiceRunError(
                f"ngspice exited with code {proc.returncode}.\n{_tail(log, 1200)}"
            )
        fatal = _solver_failed(log)
        if fatal:
            raise SpiceRunError(f"ngspice reported a solver error: {fatal}")

        if analysis == "dc":
            data = parse_op(log)
        elif analysis == "ac":
            data = parse_ac(_read_text(workdir / "ac.txt"))
        else:
            data = parse_tran(_read_text(workdir / "tran.txt"))

        return SpiceRun(
            run_id=run_id,
            analysis=analysis,
            started_utc=started,
            netlist=netlist,
            log=_tail(log),
            elapsed_ms=elapsed_ms,
            engine=engine_info(),
            data=data,
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


# --------------------------------------------------------------------------
# Parsers
# --------------------------------------------------------------------------

_OP_LINE = re.compile(
    r"^(?:v\((?P<node>\w+)\)|@q1\[(?P<param>\w+)\])\s*=\s*(?P<value>[-+]?[\d.]+(?:[eE][-+]?\d+)?)\s*$"
)


def parse_op(log: str) -> dict:
    """Parse ``print`` output of an operating-point run."""
    nodes: dict[str, float] = {}
    params: dict[str, float] = {}
    for line in log.splitlines():
        match = _OP_LINE.match(line.strip())
        if not match:
            continue
        if match.group("node"):
            nodes[match.group("node")] = float(match.group("value"))
        else:
            params[match.group("param")] = float(match.group("value"))

    missing = [name for name in ("base", "emit", "coll") if name not in nodes]
    if missing:
        raise SpiceRunError(
            "ngspice output did not contain the expected node voltages "
            f"({', '.join(missing)})."
        )

    ic = params.get("ic")
    ib = params.get("ib")
    if ic is None or ib is None:
        raise SpiceRunError("ngspice output did not contain Q1 collector/base current.")

    vb, ve, vc = nodes["base"], nodes["emit"], nodes["coll"]
    return {
        "vb_v": vb,
        "ve_v": ve,
        "vc_v": vc,
        "vce_v": vc - ve,
        "vbe_v": vb - ve,
        "ic_a": ic,
        "ib_a": ib,
        "ie_a": ic + ib,
        "vcc_node_v": nodes.get("vcc"),
        "out_node_v": nodes.get("out"),
    }


def _numeric_rows(text: str) -> list[list[float]]:
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line[0].isalpha():
            continue
        parts = line.split()
        try:
            rows.append([float(part) for part in parts])
        except ValueError:
            continue
    return rows


def parse_ac(text: str) -> dict:
    """Parse ``wrdata`` output: frequency, gain (dB), phase (deg)."""
    rows = _numeric_rows(text)
    if len(rows) < 3:
        raise SpiceRunError("ngspice wrote no usable AC data.")
    rows = [row for row in rows if len(row) >= 3]
    freqs = [row[0] for row in rows]
    gain_db = [row[1] for row in rows]
    phase_deg = [row[2] for row in rows]
    if any(f <= 0 for f in freqs):
        raise SpiceRunError("ngspice wrote a non-positive frequency in the AC data.")
    return {
        "freq_hz": freqs,
        "gain_db": gain_db,
        "phase_deg": phase_deg,
        "gain_v_per_v": [10 ** (g / 20.0) for g in gain_db],
        "cutoff": cutoff_frequencies(freqs, gain_db),
    }


def parse_tran(text: str) -> dict:
    """Parse ``wrdata`` output: time, input voltage, output voltage."""
    rows = _numeric_rows(text)
    if len(rows) < 3:
        raise SpiceRunError("ngspice wrote no usable transient data.")
    rows = [row for row in rows if len(row) >= 3]
    return {
        "time_s": [row[0] for row in rows],
        "vin_v": [row[1] for row in rows],
        "vout_v": [row[2] for row in rows],
    }


# --------------------------------------------------------------------------
# Small engineering helpers
# --------------------------------------------------------------------------


def cutoff_frequencies(freqs: list[float], gain_db: list[float], drop_db: float = 3.0) -> dict:
    """Locate the -3 dB corners of a Bode magnitude curve.

    Returns ``None`` for a corner that is not inside the sweep, so the caller
    can say "not determined in sweep range" instead of inventing a number.
    """
    if len(freqs) < 3 or len(freqs) != len(gain_db):
        return None
    peak_db = max(gain_db)
    target = peak_db - drop_db
    peak_index = gain_db.index(peak_db)

    def interp(i: int, j: int) -> float:
        """Log-frequency interpolation between two samples."""
        g0, g1 = gain_db[i], gain_db[j]
        if g1 == g0:
            return freqs[j]
        ratio = (target - g0) / (g1 - g0)
        log_f = math.log10(freqs[i]) + ratio * (
            math.log10(freqs[j]) - math.log10(freqs[i])
        )
        return 10 ** log_f

    f_low = None
    if peak_index > 0 and gain_db[0] < target:
        for i in range(1, peak_index + 1):
            if gain_db[i] >= target:
                f_low = interp(i - 1, i)
                break

    f_high = None
    if peak_index < len(gain_db) - 1 and gain_db[-1] < target:
        for i in range(len(gain_db) - 2, peak_index - 1, -1):
            if gain_db[i] >= target:
                f_high = interp(i, i + 1)
                break

    bandwidth = None
    if f_low is not None and f_high is not None:
        bandwidth = f_high - f_low

    return {
        "midband_db": peak_db,
        "midband_gain": 10 ** (peak_db / 20.0),
        "target_db": target,
        "f_low_hz": f_low,
        "f_high_hz": f_high,
        "bandwidth_hz": bandwidth,
        "in_sweep": f_low is not None or f_high is not None,
    }


def tran_summary(time_s: list[float], vin_v: list[float], vout_v: list[float]) -> dict:
    """Peak-to-peak amplitudes and phase relation of the settled waveform.

    Only the last 40 % of the run is measured so the coupling capacitors have
    time to charge and the numbers describe steady state, not the start-up.
    """
    n = len(time_s)
    if n < 10:
        return {}
    start = int(n * 0.6)
    tail_in = vin_v[start:]
    tail_out = vout_v[start:]
    if not tail_in or not tail_out:
        return {}

    vin_pp = max(tail_in) - min(tail_in)
    vout_pp = max(tail_out) - min(tail_out)
    gain = vout_pp / vin_pp if vin_pp else None

    mean_in = sum(tail_in) / len(tail_in)
    mean_out = sum(tail_out) / len(tail_out)
    cov = sum((a - mean_in) * (b - mean_out) for a, b in zip(tail_in, tail_out))
    var_in = sum((a - mean_in) ** 2 for a in tail_in)
    var_out = sum((b - mean_out) ** 2 for b in tail_out)
    correlation = None
    if var_in > 0 and var_out > 0:
        correlation = cov / math.sqrt(var_in * var_out)

    return {
        "vin_peak_v": max(abs(v) for v in tail_in),
        "vout_peak_v": max(abs(v) for v in tail_out),
        "vin_pp_v": vin_pp,
        "vout_pp_v": vout_pp,
        "gain_v_per_v": gain,
        "correlation": correlation,
        "inverted": correlation is not None and correlation < 0,
        "settled_samples": len(tail_in),
        "duration_s": time_s[-1],
    }
