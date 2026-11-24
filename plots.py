"""Server-side SVG charts for the Lab 04 simulator.

The charts are drawn from the arrays returned by :mod:`spice_engine`, so an
image can only exist when a real ngspice run produced the numbers behind it.
No charting library and no JavaScript are involved: the browser receives plain
SVG with labelled axes, units and legends.
"""

from __future__ import annotations

import math

INK = "#17344b"
MUTED = "#546d83"
GRID = "#e3ecf4"
AXIS = "#9db4c6"
TEAL = "#0c8078"
ORANGE = "#b26a2b"
NAVY = "#103658"


def _eng(value: float, unit: str = "") -> str:
    """Compact engineering notation for tick labels."""
    if value == 0:
        return f"0{(' ' + unit) if unit else ''}"
    magnitude = abs(value)
    for scale, prefix in ((1e9, "G"), (1e6, "M"), (1e3, "k"), (1.0, ""),
                          (1e-3, "m"), (1e-6, "µ"), (1e-9, "n")):
        if magnitude >= scale * 0.999:
            text = f"{value / scale:.3g}"
            return f"{text}{(' ' + prefix + unit) if unit else ''}"
    return f"{value:.3g}"


def _nice_ticks(low: float, high: float, count: int = 5) -> list[float]:
    if high <= low:
        high = low + 1.0
    raw = (high - low) / max(count, 1)
    exponent = math.floor(math.log10(raw)) if raw > 0 else 0
    base = 10 ** exponent
    for step in (1, 2, 2.5, 5, 10):
        if base * step >= raw:
            step_size = base * step
            break
    start = math.ceil(low / step_size) * step_size
    ticks = []
    value = start
    while value <= high + step_size * 1e-9:
        ticks.append(round(value, 12))
        value += step_size
    return ticks


def _decade_ticks(low: float, high: float) -> list[float]:
    ticks = []
    exponent = math.floor(math.log10(low))
    while 10 ** exponent <= high * 1.0001:
        value = 10 ** exponent
        if value >= low * 0.9999:
            ticks.append(value)
        exponent += 1
    return ticks


class _Panel:
    """One plotting rectangle with linear or log x and linear y."""

    def __init__(self, x, y, width, height, xmin, xmax, ymin, ymax, log_x=False):
        self.x, self.y = x, y
        self.w, self.h = width, height
        self.xmin, self.xmax = xmin, xmax
        self.ymin, self.ymax = ymin, ymax
        self.log_x = log_x

    def px(self, value: float) -> float:
        if self.log_x:
            lo, hi = math.log10(self.xmin), math.log10(self.xmax)
            ratio = (math.log10(max(value, 1e-12)) - lo) / (hi - lo)
        else:
            ratio = (value - self.xmin) / (self.xmax - self.xmin)
        return self.x + ratio * self.w

    def py(self, value: float) -> float:
        ratio = (value - self.ymin) / (self.ymax - self.ymin)
        return self.y + self.h - ratio * self.h

    def polyline(self, xs, ys, colour, width=2.2, dash=None):
        points = " ".join(
            f"{self.px(x):.1f},{self.py(y):.1f}"
            for x, y in zip(xs, ys)
            if math.isfinite(x) and math.isfinite(y)
        )
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        return (
            f'<polyline points="{points}" fill="none" stroke="{colour}" '
            f'stroke-width="{width}" stroke-linejoin="round" '
            f'stroke-linecap="round"{extra}/>'
        )

    def y_grid(self, ticks, unit="", label_fmt=None):
        parts = []
        for tick in ticks:
            yy = self.py(tick)
            parts.append(
                f'<line x1="{self.x:.1f}" y1="{yy:.1f}" x2="{self.x + self.w:.1f}" '
                f'y2="{yy:.1f}" stroke="{GRID}" stroke-width="1"/>'
            )
            text = label_fmt(tick) if label_fmt else _eng(tick, unit)
            parts.append(
                f'<text x="{self.x - 8:.1f}" y="{yy + 4:.1f}" text-anchor="end" '
                f'font-size="13" fill="{MUTED}">{text}</text>'
            )
        return "".join(parts)

    def x_grid(self, ticks, label_fmt, labels=True):
        parts = []
        for tick in ticks:
            xx = self.px(tick)
            parts.append(
                f'<line x1="{xx:.1f}" y1="{self.y:.1f}" x2="{xx:.1f}" '
                f'y2="{self.y + self.h:.1f}" stroke="{GRID}" stroke-width="1"/>'
            )
            if labels:
                parts.append(
                    f'<text x="{xx:.1f}" y="{self.y + self.h + 17:.1f}" '
                    f'text-anchor="middle" font-size="13" fill="{MUTED}">'
                    f"{label_fmt(tick)}</text>"
                )
        return "".join(parts)

    def frame(self):
        return (
            f'<rect x="{self.x:.1f}" y="{self.y:.1f}" width="{self.w:.1f}" '
            f'height="{self.h:.1f}" fill="none" stroke="{AXIS}" stroke-width="1.2"/>'
        )


def _wrap(width, height, inner, title, desc):
    return (
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" '
        f'aria-labelledby="{title} {desc}" xmlns="http://www.w3.org/2000/svg">'
        f"<title id=\"{title}\">{title}</title>"
        f"<desc id=\"{desc}\">{desc}</desc>"
        f"{inner}</svg>"
    )


def bode_svg(freqs, gain_db, phase_deg, cutoff=None, width=760, height=470) -> str:
    """Magnitude + phase versus log frequency, from one .ac run."""
    if not freqs:
        return ""

    left, right, top, gap, bottom = 66, 18, 22, 34, 44
    plot_w = width - left - right
    mag_h = 190
    phase_h = 130
    fmin, fmax = min(freqs), max(freqs)

    g_lo = math.floor(min(gain_db) / 5) * 5
    g_hi = math.ceil(max(gain_db) / 5) * 5
    if g_hi - g_lo < 5:
        g_hi = g_lo + 5

    mag = _Panel(left, top, plot_w, mag_h, fmin, fmax, g_lo, g_hi, log_x=True)
    phase_top = top + mag_h + gap
    p_lo = min(-180.0, math.floor(min(phase_deg) / 45) * 45)
    p_hi = max(0.0, math.ceil(max(phase_deg) / 45) * 45)
    if p_hi - p_lo < 45:
        p_hi = p_lo + 45
    phase = _Panel(left, phase_top, plot_w, phase_h, fmin, fmax, p_lo, p_hi, log_x=True)

    parts = [mag.frame(), phase.frame()]
    parts.append(mag.y_grid(_nice_ticks(g_lo, g_hi, 4), "dB"))
    parts.append(phase.y_grid(_nice_ticks(p_lo, p_hi, 4), "°"))
    parts.append(mag.x_grid(_decade_ticks(fmin, fmax), lambda f: _eng(f, "Hz"), labels=False))
    parts.append(phase.x_grid(_decade_ticks(fmin, fmax), lambda f: _eng(f, "Hz")))

    parts.append(mag.polyline(freqs, gain_db, TEAL, 2.4))
    parts.append(phase.polyline(freqs, phase_deg, NAVY, 2.0))

    # -3 dB reference line and corners, when the sweep contains them.
    if cutoff:
        target = cutoff.get("target_db")
        if target is not None and g_lo <= target <= g_hi:
            yy = mag.py(target)
            parts.append(
                f'<line x1="{mag.x:.1f}" y1="{yy:.1f}" x2="{mag.x + mag.w:.1f}" '
                f'y2="{yy:.1f}" stroke="{ORANGE}" stroke-width="1.4" '
                f'stroke-dasharray="6 4"/>'
            )
            parts.append(
                f'<text x="{mag.x + 6:.1f}" y="{yy - 6:.1f}" '
                f'text-anchor="start" font-size="12" fill="{ORANGE}">'
                f'−3 dB ({target:.1f} dB)</text>'
            )
        for key, label in (("f_low_hz", "fL"), ("f_high_hz", "fH")):
            value = cutoff.get(key)
            if value and fmin <= value <= fmax:
                xx = mag.px(value)
                parts.append(
                    f'<line x1="{xx:.1f}" y1="{mag.y:.1f}" x2="{xx:.1f}" '
                    f'y2="{mag.y + mag.h:.1f}" stroke="{ORANGE}" '
                    f'stroke-width="1.2" stroke-dasharray="4 4"/>'
                )
                anchor = "end" if xx > mag.x + mag.w * 0.55 else "start"
                offset = -4 if anchor == "end" else 4
                parts.append(
                    f'<text x="{xx + offset:.1f}" y="{mag.y + 14:.1f}" '
                    f'text-anchor="{anchor}" font-size="12" fill="{ORANGE}">'
                    f'{label} {_eng(value, "Hz")}</text>'
                )

    # Axis titles
    parts.append(
        f'<text x="{left}" y="{top - 6}" font-size="13" font-weight="600" '
        f'fill="{NAVY}">Gain magnitude</text>'
    )
    parts.append(
        f'<text x="{left}" y="{phase_top - 6}" font-size="13" font-weight="600" '
        f'fill="{NAVY}">Phase</text>'
    )
    parts.append(
        f'<text x="{left + plot_w / 2:.1f}" y="{height - 6}" text-anchor="middle" '
        f'font-size="13" fill="{MUTED}">Frequency (Hz, log scale)</text>'
    )

    inner = "".join(parts)
    return _wrap(
        width,
        height,
        inner,
        "Bode plot from ngspice .ac run",
        "Gain magnitude in dB and phase in degrees against logarithmic frequency.",
    )


def wave_svg(time_s, vin_v, vout_v, width=760, height=330) -> str:
    """Input and output voltage versus time, from one .tran run."""
    if not time_s:
        return ""

    left, right, top, bottom = 66, 18, 26, 46
    plot_w = width - left - right
    plot_h = height - top - bottom

    tmax = max(time_s) or 1e-3
    values = list(vin_v) + list(vout_v)
    peak = max(abs(v) for v in values) if values else 1.0
    peak = peak or 1.0
    span = peak * 1.12

    panel = _Panel(left, top, plot_w, plot_h, 0.0, tmax, -span, span)
    parts = [panel.frame()]
    parts.append(panel.y_grid(_nice_ticks(-span, span, 4), "V"))
    ticks = _nice_ticks(0.0, tmax, 5)
    parts.append(panel.x_grid(ticks, lambda t: f"{t * 1e3:g}"))
    parts.append(panel.polyline(time_s, vin_v, TEAL, 1.8))
    parts.append(panel.polyline(time_s, vout_v, ORANGE, 2.0))

    parts.append(
        f'<line x1="{left}" y1="{panel.py(0):.1f}" x2="{left + plot_w}" '
        f'y2="{panel.py(0):.1f}" stroke="{AXIS}" stroke-width="1"/>'
    )
    parts.append(
        f'<text x="{left + plot_w / 2:.1f}" y="{height - 8}" text-anchor="middle" '
        f'font-size="13" fill="{MUTED}">Time (ms)</text>'
    )
    # Legend
    legend_x = left + plot_w - 150
    parts.append(
        f'<rect x="{legend_x - 10}" y="{top + 6}" width="160" height="38" rx="5" '
        f'fill="#ffffff" fill-opacity="0.88" stroke="{GRID}"/>'
    )
    parts.append(
        f'<line x1="{legend_x}" y1="{top + 19}" x2="{legend_x + 22}" y2="{top + 19}" '
        f'stroke="{TEAL}" stroke-width="2.4"/>'
    )
    parts.append(
        f'<text x="{legend_x + 28}" y="{top + 23}" font-size="12" fill="{INK}">Vin</text>'
    )
    parts.append(
        f'<line x1="{legend_x}" y1="{top + 35}" x2="{legend_x + 22}" y2="{top + 35}" '
        f'stroke="{ORANGE}" stroke-width="2.4"/>'
    )
    parts.append(
        f'<text x="{legend_x + 28}" y="{top + 39}" font-size="12" fill="{INK}">Vout</text>'
    )

    inner = "".join(parts)
    return _wrap(
        width,
        height,
        inner,
        "Transient waveforms from ngspice .tran run",
        "Input and output voltage in volts against time in milliseconds.",
    )
