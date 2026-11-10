"""Flask HTTP layer for the BJT DC bias web app.

Responsibilities: read the form, convert units, call the engineering module,
format numbers for display. No physics lives here.
"""

from flask import Flask, render_template, request

from dc_bias import compute_dc_bias

app = Flask(__name__)

# (form field, label, unit shown next to the input)
FIELDS = (
    ("vcc", "VCC", "V"),
    ("r1", "R1", "kΩ"),
    ("r2", "R2", "kΩ"),
    ("rc", "RC", "kΩ"),
    ("re", "RE", "kΩ"),
    ("beta", "β", ""),
    ("vbe", "VBE", "V"),
)

DEFAULTS = {
    "vcc": "12.0",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1.0",
    "beta": "100",
    "vbe": "0.70",
}

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


def build_display(result):
    return {
        "vth": format_voltage(result.vth_v),
        "rth": f"{result.rth_ohm / 1000.0:.3f} kΩ",
        "vb": format_voltage(result.vb_v),
        "ve": format_voltage(result.ve_v),
        "vc": format_voltage(result.vc_v),
        "vce": format_voltage(result.vce_v),
        "ib": format_current(result.ib_a),
        "ic": format_current(result.ic_a),
        "ie": format_current(result.ie_a),
    }


def parse_fields(form):
    """Return (values in form units, human readable errors)."""
    values = {}
    errors = []
    for field, label, _unit in FIELDS:
        raw = (form.get(field) or "").strip()
        if not raw:
            errors.append(f"{label} is required.")
            continue
        try:
            values[field] = float(raw)
        except ValueError:
            errors.append(f"{label} must be a number.")
    return values, errors


def render_page(form, result=None, errors=(), status=200):
    return (
        render_template(
            "index.html",
            form=form,
            result=result,
            errors=list(errors),
            defaults=DEFAULTS,
            fields=FIELDS,
            region_label=REGION_LABELS.get(result.region) if result else None,
            display=build_display(result) if result else None,
        ),
        status,
    )


@app.get("/")
def index():
    return render_page(DEFAULTS)


@app.post("/calculate")
def calculate():
    form = {field: (request.form.get(field) or "") for field, _l, _u in FIELDS}
    values, errors = parse_fields(request.form)
    if errors:
        return render_page(form, errors=errors, status=400)

    try:
        result = compute_dc_bias(
            vcc_v=values["vcc"],
            r1_ohm=values["r1"] * 1000.0,
            r2_ohm=values["r2"] * 1000.0,
            rc_ohm=values["rc"] * 1000.0,
            re_ohm=values["re"] * 1000.0,
            beta=values["beta"],
            vbe_v=values["vbe"],
        )
    except ValueError as exc:
        return render_page(form, errors=[str(exc)], status=400)

    return render_page(form, result=result)


if __name__ == "__main__":
    app.run(debug=True)
