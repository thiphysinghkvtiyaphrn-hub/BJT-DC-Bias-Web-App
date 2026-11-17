"""Flask HTTP layer for the BJT DC bias web app.

Responsibilities: read the form, pick the bias mode, convert units, call the
engineering module, format numbers for display. No physics lives here.
"""

import math

from flask import Flask, render_template, request

from dc_bias import compute_dc_bias, compute_emitter_bias, compute_fixed_bias

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


if __name__ == "__main__":
    app.run(debug=True)
