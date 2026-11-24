import unittest

import spice_engine as spice
from app import app

SIM = dict(vcc="12.0", r1="100", r2="22", rc="2.2", re="1.0", rl="10",
           cin="10", cout="10", amp="10", freq="1000", beta="100")

HAS_ENGINE = spice.engine_info()["available"]


class TestSimulatorPage(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_get_page_returns_form_and_engine_badge(self):
        resp = self.client.get("/simulator")
        html = resp.get_data(as_text=True)
        self.assertEqual(resp.status_code, 200)
        for field in ("vcc", "r1", "r2", "rc", "re", "rl", "cin", "cout", "amp", "freq"):
            self.assertIn(f'name="{field}"', html)
        self.assertIn("ngspice", html)
        self.assertIn("No simulation has run yet", html)

    def test_get_page_for_each_analysis(self):
        for analysis in ("dc", "ac", "tran"):
            with self.subTest(analysis=analysis):
                resp = self.client.get(f"/simulator?analysis={analysis}")
                self.assertEqual(resp.status_code, 200)
                self.assertIn(spice.ANALYSES[analysis], resp.get_data(as_text=True))

    def test_unknown_analysis_returns_400(self):
        resp = self.client.get("/simulator?analysis=fft")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Unknown analysis mode", resp.get_data(as_text=True))

    def test_unknown_analysis_on_post_returns_400(self):
        resp = self.client.post("/simulate", data={**SIM, "analysis": "fft"})
        self.assertEqual(resp.status_code, 400)

    def test_lab3_page_still_works_and_links_here(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn('name="vcc"', html)
        self.assertIn("/simulator", html)


class TestSimulatorValidation(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_zero_re_is_rejected_before_any_run(self):
        resp = self.client.post("/simulate", data={**SIM, "re": "0"})
        html = resp.get_data(as_text=True)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("RE must be greater than", html)
        self.assertNotIn(">Success<", html)

    def test_missing_field_is_reported(self):
        data = dict(SIM)
        data.pop("rc")
        resp = self.client.post("/simulate", data=data)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("RC is required", resp.get_data(as_text=True))

    def test_non_numeric_frequency_is_reported(self):
        resp = self.client.post("/simulate", data={**SIM, "freq": "1kHz"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Source frequency must be a number",
                      resp.get_data(as_text=True))

    def test_out_of_range_frequency_is_reported(self):
        resp = self.client.post("/simulate", data={**SIM, "freq": "99999999"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Source frequency must not exceed",
                      resp.get_data(as_text=True))

    def test_submitted_values_are_kept_on_error(self):
        resp = self.client.post("/simulate", data={**SIM, "re": "0"})
        self.assertIn('value="0"', resp.get_data(as_text=True))


@unittest.skipUnless(HAS_ENGINE, "ngspice is not installed")
class TestSimulatorRuns(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_dc_run_shows_spice_values_and_comparison(self):
        resp = self.client.post("/simulate", data={**SIM, "analysis": "dc"})
        html = resp.get_data(as_text=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Success", html)
        self.assertIn("Analytical vs SPICE", html)
        self.assertIn("VCE", html)
        self.assertIn("ngspice", html)

    def test_ac_run_draws_a_bode_plot(self):
        resp = self.client.post("/simulate", data={**SIM, "analysis": "ac"})
        html = resp.get_data(as_text=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Midband gain", html)
        self.assertIn("Bode plot from ngspice .ac run", html)
        self.assertIn("<polyline", html)

    def test_tran_run_draws_waveforms(self):
        resp = self.client.post("/simulate", data={**SIM, "analysis": "tran"})
        html = resp.get_data(as_text=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Phase relation", html)
        self.assertIn("Transient waveforms from ngspice .tran run", html)

    def test_changing_re_changes_the_operating_point(self):
        first = self.client.post("/simulate", data={**SIM, "analysis": "dc"})
        second = self.client.post("/simulate", data={**SIM, "analysis": "dc", "re": "2.0"})
        self.assertNotEqual(first.get_data(as_text=True),
                            second.get_data(as_text=True))

    def test_changing_source_amplitude_changes_the_waveform(self):
        small = self.client.post("/simulate", data={**SIM, "analysis": "tran", "amp": "10"})
        large = self.client.post("/simulate", data={**SIM, "analysis": "tran", "amp": "20"})
        self.assertIn("0.010 V", small.get_data(as_text=True))
        self.assertIn("0.020 V", large.get_data(as_text=True))

    def test_netlist_is_shown_as_provenance(self):
        html = self.client.post("/simulate", data={**SIM, "analysis": "dc"}).get_data(as_text=True)
        self.assertIn("Generated netlist", html)
        self.assertIn("Q1 coll base emit Q2N3904", html)


if __name__ == "__main__":
    unittest.main()
