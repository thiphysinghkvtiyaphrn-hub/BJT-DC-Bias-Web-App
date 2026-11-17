import unittest

from dc_bias import compute_dc_bias, compute_emitter_bias, compute_fixed_bias

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


class TestFixedBias(unittest.TestCase):
    def test_reference_values(self):
        r = compute_fixed_bias(
            vcc_v=12.0, rb_ohm=1_000_000.0, rc_ohm=2_200.0,
            beta=100.0, vbe_v=0.70,
        )
        self.assertEqual(r["mode"], "fixed")
        self.assertAlmostEqual(r.ib_a, 1.13e-05, places=9)
        self.assertAlmostEqual(r.ic_a, 1.13e-03, places=9)
        self.assertAlmostEqual(r.ie_a, 1.1413e-03, places=9)
        self.assertAlmostEqual(r.ve_v, 0.0, places=12)
        self.assertAlmostEqual(r.vb_v, 0.70, places=9)
        self.assertAlmostEqual(r.vc_v, 9.514, places=9)
        self.assertAlmostEqual(r.vce_v, 9.514, places=9)
        self.assertEqual(r.region, "active")

    def test_dict_contract(self):
        r = compute_fixed_bias(vcc_v=12.0, rb_ohm=1e6, rc_ohm=2200.0,
                               beta=100.0, vbe_v=0.7)
        for key in ("mode", "ib_a", "ic_a", "ie_a", "ic_ma", "vb_v",
                    "ve_v", "vc_v", "vce_v", "region", "warnings"):
            self.assertIn(key, r)
        self.assertAlmostEqual(r["ic_ma"], r["ic_a"] * 1000.0, places=12)


class TestEmitterBias(unittest.TestCase):
    def test_reference_values(self):
        r = compute_emitter_bias(
            vcc_v=12.0, rb_ohm=1_000_000.0, re_ohm=1_000.0,
            rc_ohm=2_200.0, beta=100.0, vbe_v=0.70,
        )
        self.assertEqual(r["mode"], "emitter")
        self.assertAlmostEqual(r.ib_a, 1.026339691e-05, places=9)
        self.assertAlmostEqual(r.ic_a, 1.026339691e-03, places=9)
        self.assertAlmostEqual(r.ie_a, 1.036603088e-03, places=9)
        self.assertAlmostEqual(r.ve_v, 1.036603088, places=6)
        self.assertAlmostEqual(r.vb_v, 1.736603088, places=6)
        self.assertAlmostEqual(r.vc_v, 9.742052680, places=6)
        self.assertAlmostEqual(r.vce_v, 8.705449592, places=6)

    def test_re_higher_lowers_ic_and_vce(self):
        low = compute_emitter_bias(vcc_v=12.0, rb_ohm=1e6, re_ohm=1000.0,
                                   rc_ohm=2200.0, beta=100.0, vbe_v=0.7)
        high = compute_emitter_bias(vcc_v=12.0, rb_ohm=1e6, re_ohm=2000.0,
                                    rc_ohm=2200.0, beta=100.0, vbe_v=0.7)
        self.assertLess(high.ic_a, low.ic_a)
        self.assertLess(high.vce_v, low.vce_v)
        self.assertAlmostEqual(high.ic_a, 9.400998336e-04, places=9)
        self.assertAlmostEqual(high.vce_v, 8.032778702, places=6)


class TestNewModeValidation(unittest.TestCase):
    def test_zero_rb_raises(self):
        with self.assertRaises(ValueError):
            compute_fixed_bias(vcc_v=12.0, rb_ohm=0.0, rc_ohm=2200.0,
                               beta=100.0, vbe_v=0.7)
        with self.assertRaises(ValueError):
            compute_emitter_bias(vcc_v=12.0, rb_ohm=0.0, re_ohm=1000.0,
                                 rc_ohm=2200.0, beta=100.0, vbe_v=0.7)

    def test_non_finite_raises(self):
        with self.assertRaises(ValueError):
            compute_fixed_bias(vcc_v=float("inf"), rb_ohm=1e6, rc_ohm=2200.0,
                               beta=100.0, vbe_v=0.7)
        with self.assertRaises(ValueError):
            compute_emitter_bias(vcc_v=12.0, rb_ohm=float("nan"), re_ohm=1000.0,
                                 rc_ohm=2200.0, beta=100.0, vbe_v=0.7)


if __name__ == "__main__":
    unittest.main()
