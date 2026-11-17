"""DC bias calculations for BJT common-emitter bias circuits.

Supports two-supply-free (single VCC) Fixed Bias, Emitter Bias and
Voltage Divider Bias. Pure engineering module: it knows nothing about
Flask, HTML or HTTP. All internal values are SI units (V, A, ohm).
"""

import math

VCE_SATURATION_V = 0.2

CUTOFF_WARNING = (
    "Base current is not positive (IB <= 0). "
    "Forward-active results are not valid."
)
SATURATION_WARNING = (
    "VCE is at or below 0.2 V; the transistor may be saturated. "
    "Forward-active results are not valid."
)


class BiasResult(dict):
    """Solved DC operating point as a dict, readable as attributes too."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name) from None


def _require_finite(value, name):
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number.")


def _require_positive(value, name):
    _require_finite(value, name)
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero.")


def _require_non_negative(value, name):
    _require_finite(value, name)
    if value < 0:
        raise ValueError(f"{name} must not be negative.")


def _solve(vcc_v, rc_ohm, beta, vbe_v, ib_a, mode, extra, re_ohm=None):
    """Finish the operating point once the base current is known.

    ``re_ohm`` is None for Fixed Bias, where the emitter is grounded.
    """
    ic_a = beta * ib_a
    ie_a = (beta + 1.0) * ib_a
    ve_v = ie_a * re_ohm if re_ohm is not None else 0.0
    vb_v = ve_v + vbe_v
    vc_v = vcc_v - ic_a * rc_ohm
    vce_v = vc_v - ve_v

    # Order matters: a non-positive IB makes every downstream value meaningless.
    warnings = []
    if ib_a <= 0:
        region = "cutoff"
        warnings.append(CUTOFF_WARNING)
    elif vce_v <= VCE_SATURATION_V:
        region = "saturation"
        warnings.append(SATURATION_WARNING)
    else:
        region = "active"

    result = BiasResult(
        mode=mode,
        ib_a=ib_a,
        ic_a=ic_a,
        ie_a=ie_a,
        ic_ma=ic_a * 1000.0,
        vb_v=vb_v,
        ve_v=ve_v,
        vc_v=vc_v,
        vce_v=vce_v,
        region=region,
        warnings=warnings,
    )
    result.update(extra)
    return result


def compute_dc_bias(
    vcc_v: float,
    r1_ohm: float,
    r2_ohm: float,
    rc_ohm: float,
    re_ohm: float,
    beta: float,
    vbe_v: float,
) -> BiasResult:
    """Solve the forward-active DC operating point of a voltage-divider bias circuit."""
    _require_positive(vcc_v, "VCC")
    _require_positive(r1_ohm, "R1")
    _require_positive(r2_ohm, "R2")
    _require_positive(rc_ohm, "RC")
    _require_positive(re_ohm, "RE")
    _require_positive(beta, "Beta")
    _require_non_negative(vbe_v, "VBE")

    vth_v = vcc_v * r2_ohm / (r1_ohm + r2_ohm)
    rth_ohm = r1_ohm * r2_ohm / (r1_ohm + r2_ohm)
    ib_a = (vth_v - vbe_v) / (rth_ohm + (beta + 1.0) * re_ohm)
    return _solve(
        vcc_v, rc_ohm, beta, vbe_v, ib_a, "divider",
        {"vth_v": vth_v, "rth_ohm": rth_ohm},
        re_ohm=re_ohm,
    )


def compute_fixed_bias(
    vcc_v: float,
    rb_ohm: float,
    rc_ohm: float,
    beta: float,
    vbe_v: float,
) -> BiasResult:
    """Solve the forward-active DC operating point of a fixed bias circuit."""
    _require_positive(vcc_v, "VCC")
    _require_positive(rb_ohm, "RB")
    _require_positive(rc_ohm, "RC")
    _require_positive(beta, "Beta")
    _require_non_negative(vbe_v, "VBE")

    ib_a = (vcc_v - vbe_v) / rb_ohm
    return _solve(vcc_v, rc_ohm, beta, vbe_v, ib_a, "fixed", {})


def compute_emitter_bias(
    vcc_v: float,
    rb_ohm: float,
    re_ohm: float,
    rc_ohm: float,
    beta: float,
    vbe_v: float,
) -> BiasResult:
    """Solve the forward-active DC operating point of an emitter bias circuit."""
    _require_positive(vcc_v, "VCC")
    _require_positive(rb_ohm, "RB")
    _require_positive(re_ohm, "RE")
    _require_positive(rc_ohm, "RC")
    _require_positive(beta, "Beta")
    _require_non_negative(vbe_v, "VBE")

    ib_a = (vcc_v - vbe_v) / (rb_ohm + (beta + 1.0) * re_ohm)
    return _solve(vcc_v, rc_ohm, beta, vbe_v, ib_a, "emitter", {}, re_ohm=re_ohm)
