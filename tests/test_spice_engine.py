import math
import unittest

import spice_engine as spice


class TestCeParams(unittest.TestCase):
    def test_default_reference_is_valid(self):
        self.assertEqual(spice.CeParams().validate(), [])

    def test_zero_re_blocks_the_run(self):
        errors = spice.CeParams(re=0.0).validate()
        self.assertTrue(any("RE" in e for e in errors), errors)

    def test_negative_and_non_finite_values_are_rejected(self):
        self.assertTrue(spice.CeParams(vcc=-1).validate())
        self.assertTrue(spice.CeParams(r1=float("inf")).validate())
        self.assertTrue(spice.CeParams(amp=0.0).validate())
        self.assertTrue(spice.CeParams(freq=5e6).validate())


class TestNetlist(unittest.TestCase):
    def setUp(self):
        self.params = spice.CeParams()

    def test_dc_netlist_has_circuit_and_analysis(self):
        netlist = spice.build_netlist(self.params, "dc")
        for fragment in ("VCC vcc 0 DC 12", "R1 vcc base 100000",
                         "R2 base 0 22000", "RC vcc coll 2200",
                         "RE emit 0 1000", "Q1 coll base emit Q2N3904",
                         ".model Q2N3904 NPN", "op", "@q1[ic]"):
            self.assertIn(fragment, netlist)

    def test_ac_netlist_requests_the_configured_sweep(self):
        netlist = spice.build_netlist(self.params, "ac")
        self.assertIn(f"ac dec {spice.AC_SWEEP['dec']}", netlist)
        self.assertIn("wrdata ac.txt vdb(out) vp(out)", netlist)

    def test_tran_netlist_covers_five_cycles(self):
        netlist = spice.build_netlist(spice.CeParams(freq=1000.0), "tran")
        tstep, tstop = spice.tran_settings(1000.0)
        self.assertAlmostEqual(tstop, 5e-3)
        self.assertIn(f"tran {tstep:.6g} {tstop:.6g}", netlist)
        self.assertIn("wrdata tran.txt v(in) v(out)", netlist)

    def test_netlist_uses_si_units_and_never_echoes_raw_text(self):
        netlist = spice.build_netlist(spice.CeParams(r1=100e3, cin=10e-6), "dc")
        self.assertIn("R1 vcc base 100000", netlist)
        self.assertIn("CIN in base 1e-05", netlist)

    def test_unknown_analysis_is_rejected(self):
        with self.assertRaises(ValueError):
            spice.build_netlist(self.params, "fft")


OP_LOG = """
No. of Data Rows : 1
v(base) = 2.003674e+00
v(emit) = 1.332880e+00
v(coll) = 9.087216e+00
@q1[ic] = 1.324035e-03
@q1[ib] = 8.887366e-06
"""


class TestParsers(unittest.TestCase):
    def test_parse_op_computes_derived_quantities(self):
        data = spice.parse_op(OP_LOG)
        self.assertAlmostEqual(data["vb_v"], 2.003674)
        self.assertAlmostEqual(data["vce_v"], 9.087216 - 1.332880)
        self.assertAlmostEqual(data["ic_a"], 1.324035e-3)
        self.assertAlmostEqual(data["ie_a"], 1.324035e-3 + 8.887366e-6)

    def test_parse_op_rejects_incomplete_output(self):
        with self.assertRaises(spice.SpiceRunError):
            spice.parse_op("v(base) = 1\n")

    def test_parse_ac_returns_arrays_and_cutoff(self):
        text = (
            " frequency  vdb(out)  vp(out)\n"
            " 1.0e+00  -20.0  -10.0\n"
            " 1.0e+01  0.0  0.0\n"
            " 1.0e+02  0.0  -20.0\n"
            " 1.0e+03  0.0  -60.0\n"
            " 1.0e+04  -20.0  -80.0\n"
        )
        data = spice.parse_ac(text)
        self.assertEqual(len(data["freq_hz"]), 5)
        self.assertAlmostEqual(data["gain_db"][2], 0.0)
        self.assertEqual(data["cutoff"]["midband_db"], 0.0)
        self.assertIsNotNone(data["cutoff"]["f_low_hz"])
        self.assertIsNotNone(data["cutoff"]["f_high_hz"])

    def test_parse_ac_rejects_empty_output(self):
        with self.assertRaises(spice.SpiceRunError):
            spice.parse_ac(" frequency vdb(out)\n")

    def test_parse_tran_returns_time_and_signals(self):
        text = " time v(in) v(out)\n0 0 0\n1e-3 0.01 -0.017\n2e-3 0 0\n"
        data = spice.parse_tran(text)
        self.assertEqual(data["time_s"], [0.0, 1e-3, 2e-3])
        self.assertEqual(data["vout_v"][1], -0.017)

    def test_parse_tran_rejects_empty_output(self):
        with self.assertRaises(spice.SpiceRunError):
            spice.parse_tran(" time v(in) v(out)\n")


class TestCutoff(unittest.TestCase):
    def test_flat_curve_reports_no_corner(self):
        freqs = [10 ** i for i in range(6)]
        gain = [20.0] * 6
        result = spice.cutoff_frequencies(freqs, gain)
        self.assertIsNone(result["f_low_hz"])
        self.assertIsNone(result["f_high_hz"])
        self.assertFalse(result["in_sweep"])

    def test_corner_is_interpolated_between_samples(self):
        freqs = [1.0, 10.0, 100.0, 1000.0]
        gain = [-30.0, 0.0, 0.0, -30.0]
        result = spice.cutoff_frequencies(freqs, gain)
        # -3 dB lies 90 % of the way from 1 Hz to 10 Hz, and 10 % of the way
        # from 100 Hz to 1 kHz, on a log-frequency axis.
        self.assertAlmostEqual(result["f_low_hz"], 10 ** 0.9, places=6)
        self.assertAlmostEqual(result["f_high_hz"], 10 ** 2.1, places=6)


class TestTranSummary(unittest.TestCase):
    def test_inverted_signal_is_detected(self):
        n = 100
        time_s = [i * 1e-5 for i in range(n)]
        vin = [math.sin(2 * math.pi * 1000 * t) for t in time_s]
        vout = [-2.0 * math.sin(2 * math.pi * 1000 * t) for t in time_s]
        summary = spice.tran_summary(time_s, vin, vout)
        self.assertTrue(summary["inverted"])
        self.assertAlmostEqual(summary["gain_v_per_v"], 2.0, places=2)

    def test_short_run_returns_nothing(self):
        self.assertEqual(spice.tran_summary([0.0], [0.0], [0.0]), {})


class TestEngineProbe(unittest.TestCase):
    def test_engine_info_is_a_dict(self):
        info = spice.engine_info()
        self.assertIn("available", info)
        self.assertEqual(info["model"], spice.BJT_MODEL_NAME)


@unittest.skipUnless(spice.engine_info()["available"], "ngspice is not installed")
class TestRealRuns(unittest.TestCase):
    """Integration checks: these only run when a solver is present."""

    def test_dc_run_matches_forward_active_expectations(self):
        run = spice.run_analysis(spice.CeParams(), "dc")
        data = run.data
        self.assertEqual(run.analysis, "dc")
        self.assertGreater(data["vb_v"], data["ve_v"])
        self.assertGreater(data["vce_v"], 0.2)
        self.assertTrue(0.0 < data["ic_a"] < 0.01)
        self.assertIn("VCC vcc 0 DC 12", run.netlist)
        self.assertIn("ngspice", run.log.lower())

    def test_ac_run_returns_a_full_sweep(self):
        run = spice.run_analysis(spice.CeParams(), "ac")
        self.assertGreater(len(run.data["freq_hz"]), 100)
        self.assertGreater(max(run.data["gain_db"]), 0.0)
        self.assertLess(run.data["freq_hz"][0], run.data["freq_hz"][-1])

    def test_tran_run_shows_gain_and_inversion(self):
        run = spice.run_analysis(spice.CeParams(), "tran")
        summary = spice.tran_summary(run.data["time_s"], run.data["vin_v"],
                                     run.data["vout_v"])
        self.assertTrue(summary["inverted"])
        self.assertGreater(summary["gain_v_per_v"], 1.0)

    def test_changing_re_changes_the_result(self):
        first = spice.run_analysis(spice.CeParams(), "dc").data["ic_a"]
        second = spice.run_analysis(spice.CeParams(re=2e3), "dc").data["ic_a"]
        self.assertNotAlmostEqual(first, second, places=6)


if __name__ == "__main__":
    unittest.main()
