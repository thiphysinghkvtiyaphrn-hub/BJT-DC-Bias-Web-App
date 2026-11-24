import unittest

from plots import bode_svg, wave_svg

GAIN = [0.1, 1.0, 10.0, 100.0]
GAIN_DB = [40.0, 20.0, 6.0, 0.0]
PHASE = [0.0, -10.0, -30.0, -45.0]
CUTOFF = {
    "midband_db": 20.0,
    "midband_gain": 10.0,
    "target_db": 17.0,
    "f_low_hz": 1.0,
    "f_high_hz": 100.0,
    "bandwidth_hz": 99.0,
    "in_sweep": True,
}


class TestBodeSvg(unittest.TestCase):
    def test_renders_gain_and_phase_curves(self):
        svg = bode_svg(GAIN, GAIN_DB, PHASE, cutoff=CUTOFF)
        self.assertIn("<svg", svg)
        self.assertIn("<polyline", svg)
        self.assertIn("Gain magnitude", svg)
        self.assertIn("Phase", svg)
        self.assertIn("Frequency (Hz, log scale)", svg)

    def test_minus_3db_label_is_drawn_inside_the_panel(self):
        svg = bode_svg(GAIN, GAIN_DB, PHASE, cutoff=CUTOFF)
        self.assertIn("−3 dB", svg)
        # regression: label used to sit at the right edge of the panel and get
        # clipped; it must now be anchored at the start (left) inside the plot.
        self.assertIn('x="72.0"', svg)
        self.assertIn('text-anchor="start"', svg)


class TestWaveSvg(unittest.TestCase):
    def test_renders_input_and_output_waveforms(self):
        svg = wave_svg([0.0, 1e-3, 2e-3], [0.0, 0.005, 0.01], [0.0, 0.004, 0.009])
        self.assertIn("<svg", svg)
        self.assertIn("<polyline", svg)
        self.assertIn("Vin", svg)
        self.assertIn("Vout", svg)
        self.assertIn("Time (ms)", svg)


if __name__ == "__main__":
    unittest.main()
