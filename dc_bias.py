"""DC bias calculations for a BJT common-emitter voltage-divider bias circuit.

Pure engineering module: it knows nothing about Flask, HTML or HTTP.
All internal values are SI units (V, A, ohm).
"""

from dataclasses import dataclass, field

VCE_SATURATION_V = 0.2

CUTOFF_WARNING = (
    "Base-emitter junction is not forward biased (VTH <= VBE). "
    "Forward-active results are not valid."
)
SATURATION_WARNING = (
    "VCE is below 0.2 V; the transistor may be saturated. "
    "Forward-active results are not valid."
)


@dataclass(frozen=True)
class BiasResult:
    """Solved DC operating point plus the assumptions it was solved under."""

    vth_v: float
    rth_ohm: float
    ib_a: float
    ic_a: float
    ie_a: float
    ve_v: float
    vb_v: float
    vc_v: float
    vce_v: float
    region: str
    warnings: list[str] = field(default_factory=list)


def _require_positive(value, name):
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero.")


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
    if vbe_v < 0:
        raise ValueError("VBE must not be negative.")

    vth_v = vcc_v * r2_ohm / (r1_ohm + r2_ohm)
    rth_ohm = r1_ohm * r2_ohm / (r1_ohm + r2_ohm)
    ib_a = (vth_v - vbe_v) / (rth_ohm + (beta + 1.0) * re_ohm)
    ic_a = beta * ib_a
    ie_a = (beta + 1.0) * ib_a
    ve_v = ie_a * re_ohm
    vb_v = ve_v + vbe_v
    vc_v = vcc_v - ic_a * rc_ohm
    vce_v = vc_v - ve_v

    # Order matters: a negative IB makes every downstream value meaningless.
    warnings = []
    if vth_v <= vbe_v or ib_a <= 0:
        region = "cutoff"
        warnings.append(CUTOFF_WARNING)
    elif vce_v < VCE_SATURATION_V:
        region = "saturation"
        warnings.append(SATURATION_WARNING)
    else:
        region = "active"

    return BiasResult(
        vth_v=vth_v,
        rth_ohm=rth_ohm,
        ib_a=ib_a,
        ic_a=ic_a,
        ie_a=ie_a,
        ve_v=ve_v,
        vb_v=vb_v,
        vc_v=vc_v,
        vce_v=vce_v,
        region=region,
        warnings=warnings,
    )
