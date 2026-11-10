import unittest

from dc_bias import compute_dc_bias

REFERENCE = dict(
    vcc_v=12.0,
    r1_ohm=100_000.0,
    r2_ohm=22_000.0,
    rc_ohm=2_200.0,
    re_ohm=1_000.0,
    beta=100.0,
    vbe_v=0.70,
)


class TestReferencePoint(unittest.TestCase):
    def test_reference_values(self):
        r = compute_dc_bias(**REFERENCE)
        self.assertAlmostEqual(r.vth_v, 2.163934426, places=8)
        self.assertAlmostEqual(r.rth_ohm, 18032.786885, places=5)
        self.assertAlmostEqual(r.ib_a, 1.229858e-05, places=9)
        self.assertAlmostEqual(r.ic_a, 1.229858e-03, places=9)
        self.assertAlmostEqual(r.ie_a, 1.242157e-03, places=9)
        self.assertAlmostEqual(r.ve_v, 1.242157, places=6)
        self.assertAlmostEqual(r.vb_v, 1.942157, places=6)
        self.assertAlmostEqual(r.vc_v, 9.294312, places=6)
        self.assertAlmostEqual(r.vce_v, 8.052155, places=6)

    def test_identity_relations(self):
        r = compute_dc_bias(**REFERENCE)
        self.assertAlmostEqual(r.ic_a, REFERENCE["beta"] * r.ib_a, places=12)
        self.assertAlmostEqual(r.ie_a, (REFERENCE["beta"] + 1) * r.ib_a, places=12)
        self.assertAlmostEqual(r.vce_v, r.vc_v - r.ve_v, places=12)


class TestInputValidation(unittest.TestCase):
    def test_zero_resistance_raises(self):
        for key in ("r1_ohm", "r2_ohm", "rc_ohm", "re_ohm"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                compute_dc_bias(**{**REFERENCE, key: 0.0})

    def test_non_positive_supply_and_beta_raise(self):
        with self.assertRaises(ValueError):
            compute_dc_bias(**{**REFERENCE, "vcc_v": 0.0})
        with self.assertRaises(ValueError):
            compute_dc_bias(**{**REFERENCE, "beta": -1.0})
        with self.assertRaises(ValueError):
            compute_dc_bias(**{**REFERENCE, "vbe_v": -0.1})


class TestRegionDetection(unittest.TestCase):
    def test_reference_is_active(self):
        self.assertEqual(compute_dc_bias(**REFERENCE).region, "active")

    def test_cutoff_region(self):
        r = compute_dc_bias(**{**REFERENCE, "r2_ohm": 1_000.0})  # VTH = 0.119 V
        self.assertEqual(r.region, "cutoff")
        self.assertLessEqual(r.vth_v, REFERENCE["vbe_v"])
        self.assertTrue(r.warnings)

    def test_saturation_region(self):
        r = compute_dc_bias(**{**REFERENCE, "re_ohm": 100.0, "rc_ohm": 10_000.0})
        self.assertEqual(r.region, "saturation")
        self.assertLess(r.vce_v, 0.2)
        self.assertTrue(r.warnings)


if __name__ == "__main__":
    unittest.main()
