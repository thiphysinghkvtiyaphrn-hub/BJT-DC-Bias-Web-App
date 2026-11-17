import unittest

from app import app

VALID = dict(vcc="12", r1="100", r2="22", rc="2.2", re="1", beta="100", vbe="0.70")


class TestWeb(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_get_index_returns_form(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn('name="vcc"', resp.get_data(as_text=True))

    def test_calculate_returns_reference_values(self):
        resp = self.client.post("/calculate", data=VALID)
        html = resp.get_data(as_text=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("8.052", html)
        self.assertIn("12.30", html)
        self.assertIn("Active", html)

    def test_zero_resistance_returns_400(self):
        resp = self.client.post("/calculate", data={**VALID, "r1": "0"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("greater than zero", resp.get_data(as_text=True))

    def test_non_numeric_value_returns_400(self):
        for bad in ("abc", "", "12V"):
            with self.subTest(bad=bad):
                resp = self.client.post("/calculate", data={**VALID, "vcc": bad})
                self.assertEqual(resp.status_code, 400)
                self.assertIn("VCC", resp.get_data(as_text=True))

    def test_form_keeps_submitted_values_on_error(self):
        resp = self.client.post("/calculate", data={**VALID, "vcc": "abc"})
        self.assertIn('value="abc"', resp.get_data(as_text=True))

    def test_cutoff_page_hides_values(self):
        resp = self.client.post("/calculate", data={**VALID, "r2": "1"})
        html = resp.get_data(as_text=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Cutoff", html)
        self.assertEqual(html.count('class="value">—'), 7)
        self.assertNotIn("13.8", html)


class TestModes(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_fixed_tab_shows_only_fixed_fields(self):
        html = self.client.get("/?mode=fixed").get_data(as_text=True)
        self.assertIn('name="rb"', html)
        self.assertNotIn('name="r1"', html)
        self.assertNotIn('name="re"', html)
        self.assertIn('name="mode"', html)

    def test_fixed_calculate(self):
        data = dict(mode="fixed", vcc="12", rb="1000", rc="2.2",
                    beta="100", vbe="0.70")
        html = self.client.post("/calculate", data=data).get_data(as_text=True)
        self.assertIn("9.514", html)   # VCE
        self.assertIn("1.130", html)   # IC
        self.assertIn("Fixed Bias", html)

    def test_emitter_calculate(self):
        data = dict(mode="emitter", vcc="12", rb="1000", re="1",
                    rc="2.2", beta="100", vbe="0.70")
        html = self.client.post("/calculate", data=data).get_data(as_text=True)
        self.assertIn("8.705", html)
        self.assertIn("Emitter Bias", html)

    def test_unknown_mode_returns_400(self):
        data = dict(mode="nonsense", vcc="12", rb="1000", rc="2.2",
                    beta="100", vbe="0.70")
        resp = self.client.post("/calculate", data=data)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Unknown", resp.get_data(as_text=True))

    def test_missing_mode_defaults_to_divider(self):
        data = dict(vcc="12", r1="100", r2="22", rc="2.2", re="1",
                    beta="100", vbe="0.70")
        resp = self.client.post("/calculate", data=data)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("8.052", resp.get_data(as_text=True))

    def test_fixed_zero_rb_returns_400_without_result(self):
        data = dict(mode="fixed", vcc="12", rb="0", rc="2.2",
                    beta="100", vbe="0.70")
        resp = self.client.post("/calculate", data=data)
        html = resp.get_data(as_text=True)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("RB", html)
        self.assertNotIn('class="value">9.514', html)

    def test_non_finite_returns_400(self):
        data = dict(mode="fixed", vcc="inf", rb="1000", rc="2.2",
                    beta="100", vbe="0.70")
        resp = self.client.post("/calculate", data=data)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("VCC", resp.get_data(as_text=True))


    def test_page_shows_mode_label_and_fixed_ve_zero(self):
        data = dict(mode="fixed", vcc="12", rb="1000", rc="2.2",
                    beta="100", vbe="0.70")
        html = self.client.post("/calculate", data=data).get_data(as_text=True)
        self.assertIn("Fixed Bias", html)
        self.assertIn("0.000 V", html)          # VE = 0
        self.assertNotIn("VTH =", html)         # details ของ divider ไม่โผล่

    def test_divider_details_still_show_vth(self):
        data = dict(mode="divider", vcc="12", r1="100", r2="22", rc="2.2",
                    re="1", beta="100", vbe="0.70")
        html = self.client.post("/calculate", data=data).get_data(as_text=True)
        self.assertIn("VTH =", html)


    def test_error_banner_names_selected_mode(self):
        data = dict(mode="fixed", vcc="12", rb="0", rc="2.2",
                    beta="100", vbe="0.70")
        html = self.client.post("/calculate", data=data).get_data(as_text=True)
        self.assertIn("Check your input — Fixed Bias", html)


if __name__ == "__main__":
    unittest.main()
