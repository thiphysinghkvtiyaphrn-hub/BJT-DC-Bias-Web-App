"""Flask HTTP layer for the BJT DC bias web app.

Responsibilities: read the form, pick the bias mode, convert units, call the
engineering module, format numbers for display. No physics lives here.
"""

import math

from flask import Flask, render_template, request

import spice_engine as spice
from dc_bias import compute_dc_bias, compute_emitter_bias, compute_fixed_bias
from plots import bode_svg, wave_svg

app = Flask(__name__)

MODES = {
    "divider": "Voltage Divider Bias",
    "fixed": "Fixed Bias",
    "emitter": "Emitter Bias",
}

# (form field, label, unit shown next to the input)
FIELD_DEFS = {
    "vcc": ("VCC", "V"),
    "r1": ("R1", "kΩ"),
    "r2": ("R2", "kΩ"),
    "rb": ("RB", "kΩ"),
    "rc": ("RC", "kΩ"),
    "re": ("RE", "kΩ"),
    "beta": ("β", ""),
    "vbe": ("VBE", "V"),
}

MODE_FIELDS = {
    "divider": ("vcc", "r1", "r2", "rc", "re", "beta", "vbe"),
    "fixed": ("vcc", "rb", "rc", "beta", "vbe"),
    "emitter": ("vcc", "rb", "re", "rc", "beta", "vbe"),
}

FIELDS = {
    mode: tuple((field, *FIELD_DEFS[field]) for field in names)
    for mode, names in MODE_FIELDS.items()
}

DEFAULTS = {
    "divider": {
        "vcc": "12.0",
        "r1": "100",
        "r2": "22",
        "rc": "2.2",
        "re": "1.0",
        "beta": "100",
        "vbe": "0.70",
    },
    "fixed": {
        "vcc": "12.0",
        "rb": "1000",
        "rc": "2.2",
        "beta": "100",
        "vbe": "0.70",
    },
    "emitter": {
        "vcc": "12.0",
        "rb": "1000",
        "re": "1.0",
        "rc": "2.2",
        "beta": "100",
        "vbe": "0.70",
    },
}

KILO_OHM_FIELDS = ("r1", "r2", "rb", "rc", "re")

REGION_LABELS = {
    "active": "Active",
    "cutoff": "Cutoff",
    "saturation": "Saturation",
}


def format_voltage(volts):
    return f"{volts:.3f} V"


def format_current(amps):
    if abs(amps) >= 1e-3:
        return f"{amps * 1e3:.3f} mA"
    return f"{amps * 1e6:.2f} µA"


def format_ic(amps):
    """Collector current is always reported in mA, as the lab sheet asks."""
    return f"{amps * 1e3:.3f} mA"


def build_display(result):
    display = {
        "vb": format_voltage(result.vb_v),
        "ve": format_voltage(result.ve_v),
        "vc": format_voltage(result.vc_v),
        "vce": format_voltage(result.vce_v),
        "ib": format_current(result.ib_a),
        "ic": format_ic(result.ic_a),
        "ie": format_current(result.ie_a),
    }
    if result["mode"] == "divider":
        display["vth"] = format_voltage(result.vth_v)
        display["rth"] = f"{result.rth_ohm / 1000.0:.3f} kΩ"
    return display


def parse_fields(form, mode):
    """Return (values in form units, human readable errors) for one mode."""
    values = {}
    errors = []
    for field, label, _unit in FIELDS[mode]:
        raw = (form.get(field) or "").strip()
        if not raw:
            errors.append(f"{label} is required.")
            continue
        try:
            value = float(raw)
        except ValueError:
            errors.append(f"{label} must be a number.")
            continue
        if not math.isfinite(value):
            errors.append(f"{label} must be a finite number.")
            continue
        values[field] = value
    return values, errors


def to_si(values):
    """Convert every kΩ form field to Ω. The only unit conversion in the app."""
    si = dict(values)
    for field in KILO_OHM_FIELDS:
        if field in si:
            si[f"{field}_ohm"] = si.pop(field) * 1000.0
    return si


def compute_for_mode(mode, values):
    si = to_si(values)
    if mode == "divider":
        return compute_dc_bias(
            vcc_v=si["vcc"],
            r1_ohm=si["r1_ohm"],
            r2_ohm=si["r2_ohm"],
            rc_ohm=si["rc_ohm"],
            re_ohm=si["re_ohm"],
            beta=si["beta"],
            vbe_v=si["vbe"],
        )
    if mode == "fixed":
        return compute_fixed_bias(
            vcc_v=si["vcc"],
            rb_ohm=si["rb_ohm"],
            rc_ohm=si["rc_ohm"],
            beta=si["beta"],
            vbe_v=si["vbe"],
        )
    if mode == "emitter":
        return compute_emitter_bias(
            vcc_v=si["vcc"],
            rb_ohm=si["rb_ohm"],
            re_ohm=si["re_ohm"],
            rc_ohm=si["rc_ohm"],
            beta=si["beta"],
            vbe_v=si["vbe"],
        )
    raise ValueError("Unknown bias mode.")


def render_page(mode, form, result=None, errors=(), status=200, banner_title=None):
    if banner_title is None:
        banner_title = f"Check your input — {MODES[mode]}"
    return (
        render_template(
            "index.html",
            mode=mode,
            mode_label=MODES[mode],
            modes=MODES,
            form=form,
            result=result,
            errors=list(errors),
            banner_title=banner_title,
            defaults=DEFAULTS[mode],
            fields=FIELDS[mode],
            region_label=REGION_LABELS.get(result.region) if result else None,
            display=build_display(result) if result else None,
        ),
        status,
    )


@app.get("/")
def index():
    mode = request.args.get("mode") or "divider"
    if mode not in MODES:
        return render_page(
            "divider",
            DEFAULTS["divider"],
            errors=["Unknown bias mode. Choose Divider, Fixed or Emitter."],
            status=400,
            banner_title="Check your input",
        )
    return render_page(mode, DEFAULTS[mode])


@app.post("/calculate")
def calculate():
    mode = request.form.get("mode") or "divider"
    if mode not in MODES:
        return render_page(
            "divider",
            DEFAULTS["divider"],
            errors=["Unknown bias mode. Choose Divider, Fixed or Emitter."],
            status=400,
            banner_title="Check your input",
        )

    form = {field: (request.form.get(field) or "") for field in MODE_FIELDS[mode]}
    values, errors = parse_fields(request.form, mode)
    if errors:
        return render_page(mode, form, errors=errors, status=400)

    try:
        result = compute_for_mode(mode, values)
    except ValueError as exc:
        return render_page(mode, form, errors=[str(exc)], status=400)

    return render_page(mode, form, result=result)


# ---------------------------------------------------------------------------
# Lab 04 - CE amplifier simulator (ngspice)
# ---------------------------------------------------------------------------

SIM_FIELD_ORDER = ("vcc", "r1", "r2", "rc", "re", "rl", "cin", "cout", "amp", "freq")

SIM_FIELDS = tuple((field, spice.LABELS[field], spice.UNITS[field])
                   for field in SIM_FIELD_ORDER)

SIM_DEFAULTS = {
    "vcc": "12.0",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1.0",
    "rl": "10",
    "cin": "10",
    "cout": "10",
    "amp": "10",
    "freq": "1000",
}

SIM_ANALYSES = spice.ANALYSES

ANALYTICAL_BETA_DEFAULT = "100"
ANALYTICAL_VBE_V = 0.70


def format_frequency(hz):
    if hz is None:
        return "not determined in sweep range"
    if hz >= 1e6:
        return f"{hz / 1e6:.3f} MHz"
    if hz >= 1e3:
        return f"{hz / 1e3:.3f} kHz"
    return f"{hz:.1f} Hz"


def format_gain(value):
    return f"{value:.2f} V/V" if value is not None else "—"


def parse_sim_form(form):
    """Return (SI-ready floats, raw strings for redisplay, beta, errors)."""
    values = {}
    raw_values = {}
    errors = []
    for field, label, _unit in SIM_FIELDS:
        raw = (form.get(field) or "").strip()
        raw_values[field] = raw
        if not raw:
            errors.append(f"{label} is required.")
            continue
        try:
            value = float(raw)
        except ValueError:
            errors.append(f"{label} must be a number.")
            continue
        if not math.isfinite(value):
            errors.append(f"{label} must be a finite number.")
            continue
        values[field] = value

    beta = None
    raw_beta = (form.get("beta") or ANALYTICAL_BETA_DEFAULT).strip()
    raw_values["beta"] = raw_beta
    try:
        beta = float(raw_beta)
        if not math.isfinite(beta) or beta <= 0:
            errors.append("β must be greater than zero.")
            beta = None
    except ValueError:
        errors.append("β must be a number.")

    return values, raw_values, beta, errors


def sim_params(values):
    """Convert the display units of the form into SI units for the engine."""
    si = dict(values)
    for field in spice.KILO_FIELDS:
        si[field] *= 1e3
    for field in spice.MICRO_FIELDS:
        si[field] *= 1e-6
    for field in spice.MILLI_FIELDS:
        si[field] *= 1e-3
    return spice.CeParams(**{name: si[name] for name in SIM_FIELD_ORDER})


def build_chart(run):
    if run is None:
        return None
    data = run.data
    if run.analysis == "ac":
        return bode_svg(data["freq_hz"], data["gain_db"], data["phase_deg"],
                        data.get("cutoff"))
    if run.analysis == "tran":
        return wave_svg(data["time_s"], data["vin_v"], data["vout_v"])
    return None


def dc_result_rows(data):
    return [
        ("VB", format_voltage(data["vb_v"])),
        ("VE", format_voltage(data["ve_v"])),
        ("VC", format_voltage(data["vc_v"])),
        ("VCE", format_voltage(data["vce_v"])),
        ("VBE", format_voltage(data["vbe_v"])),
        ("IC", format_ic(data["ic_a"])),
        ("IB", format_current(data["ib_a"])),
        ("IE", format_current(data["ie_a"])),
    ]


def ac_result_rows(data):
    cutoff = data.get("cutoff") or {}
    midband_gain = cutoff.get("midband_gain")
    midband_db = cutoff.get("midband_db")
    gain_text = "—"
    if midband_gain is not None and midband_db is not None:
        gain_text = f"{format_gain(midband_gain)} ({midband_db:.2f} dB)"
    return [
        ("Midband gain", gain_text),
        ("fL (−3 dB)", format_frequency(cutoff.get("f_low_hz"))),
        ("fH (−3 dB)", format_frequency(cutoff.get("f_high_hz"))),
        ("Bandwidth", format_frequency(cutoff.get("bandwidth_hz"))),
        ("Sweep", f"{format_frequency(min(data['freq_hz']))} – "
                  f"{format_frequency(max(data['freq_hz']))}"),
        ("Points", str(len(data["freq_hz"]))),
    ]


def tran_result_rows(data):
    summary = spice.tran_summary(data["time_s"], data["vin_v"], data["vout_v"])
    phase_text = "—"
    if summary:
        phase_text = ("inverted (≈180°), as expected for CE"
                      if summary["inverted"] else "in phase")
    return [
        ("Vin peak", format_voltage(summary.get("vin_peak_v", 0.0))),
        ("Vout peak", format_voltage(summary.get("vout_peak_v", 0.0))),
        ("Gain (pp)", format_gain(summary.get("gain_v_per_v"))),
        ("Phase relation", phase_text),
        ("Run length", f"{summary.get('duration_s', 0.0) * 1e3:.2f} ms"),
        ("Points", str(len(data["time_s"]))),
    ]


def build_comparison(params, beta, run):
    """Analytical Lab 3 reference next to the SPICE operating point."""
    if beta is None or run is None or run.analysis != "dc":
        return None
    try:
        ref = compute_dc_bias(
            vcc_v=params.vcc,
            r1_ohm=params.r1,
            r2_ohm=params.r2,
            rc_ohm=params.rc,
            re_ohm=params.re,
            beta=beta,
            vbe_v=ANALYTICAL_VBE_V,
        )
    except ValueError:
        return None

    data = run.data
    pairs = [
        ("VB", ref.vb_v, data["vb_v"], format_voltage),
        ("VE", ref.ve_v, data["ve_v"], format_voltage),
        ("VC", ref.vc_v, data["vc_v"], format_voltage),
        ("VCE", ref.vce_v, data["vce_v"], format_voltage),
        ("IC", ref.ic_a, data["ic_a"], format_ic),
    ]
    rows = []
    for label, reference, simulated, formatter in pairs:
        delta = "—"
        if reference:
            delta = f"{(simulated - reference) / reference * 100:+.1f} %"
        rows.append({
            "label": label,
            "reference": formatter(reference),
            "simulated": formatter(simulated),
            "delta": delta,
        })
    return {
        "beta": beta,
        "vbe": ANALYTICAL_VBE_V,
        "region": ref.region,
        "rows": rows,
    }


def render_simulator(analysis, form_values, run=None, errors=(), status=200,
                     banner_title=None, beta=None, params=None):
    if banner_title is None:
        banner_title = f"Check your input — {SIM_ANALYSES.get(analysis, 'Simulator')}"

    rows = []
    if run is not None:
        if run.analysis == "dc":
            rows = dc_result_rows(run.data)
        elif run.analysis == "ac":
            rows = ac_result_rows(run.data)
        else:
            rows = tran_result_rows(run.data)

    comparison = build_comparison(params, beta, run)

    return (
        render_template(
            "simulator.html",
            analysis=analysis,
            analyses=SIM_ANALYSES,
            analysis_label=SIM_ANALYSES.get(analysis, ""),
            fields=SIM_FIELDS,
            form=form_values,
            defaults=SIM_DEFAULTS,
            errors=list(errors),
            banner_title=banner_title,
            run=run,
            rows=rows,
            comparison=comparison,
            chart=build_chart(run),
            engine=spice.engine_info(),
            ac_sweep=spice.AC_SWEEP,
            ac_sweep_text=(
                f"{format_frequency(spice.AC_SWEEP['fstart'])} – "
                f"{format_frequency(spice.AC_SWEEP['fstop'])}, "
                f"{spice.AC_SWEEP['dec']} points/decade"
            ),
            model_name=spice.BJT_MODEL_NAME,
            model_source=spice.BJT_MODEL_SOURCE,
            analytical_beta=(beta if beta is not None else ANALYTICAL_BETA_DEFAULT),
            analytical_vbe=ANALYTICAL_VBE_V,
        ),
        status,
    )


@app.get("/simulator")
def simulator():
    analysis = request.args.get("analysis") or "dc"
    if analysis not in SIM_ANALYSES:
        return render_simulator(
            "dc",
            SIM_DEFAULTS,
            errors=["Unknown analysis mode. Choose DC, AC or Transient."],
            status=400,
            banner_title="Check your input",
        )
    return render_simulator(analysis, SIM_DEFAULTS)


@app.post("/simulate")
def simulate():
    analysis = (request.form.get("run_analysis")
                or request.form.get("analysis")
                or "dc")
    if analysis not in SIM_ANALYSES:
        return render_simulator(
            "dc",
            SIM_DEFAULTS,
            errors=["Unknown analysis mode. Choose DC, AC or Transient."],
            status=400,
            banner_title="Check your input",
        )

    form_values, raw_values, beta, errors = parse_sim_form(request.form)
    if errors:
        return render_simulator(analysis, raw_values, errors=errors, status=400)

    params = sim_params(form_values)
    errors = params.validate()
    if errors:
        return render_simulator(analysis, raw_values, errors=errors, status=400,
                                beta=beta, params=params)

    try:
        run = spice.run_analysis(params, analysis)
    except spice.SpiceNotFound as exc:
        return render_simulator(analysis, raw_values, errors=[str(exc)], status=503,
                                banner_title="Simulation engine unavailable",
                                beta=beta, params=params)
    except spice.SpiceTimeout as exc:
        return render_simulator(analysis, raw_values, errors=[str(exc)], status=504,
                                banner_title="Simulation timed out",
                                beta=beta, params=params)
    except spice.SpiceError as exc:
        return render_simulator(analysis, raw_values, errors=[str(exc)], status=502,
                                banner_title="ngspice run failed",
                                beta=beta, params=params)

    return render_simulator(analysis, raw_values, run=run, beta=beta, params=params)


if __name__ == "__main__":
    app.run(debug=True)
