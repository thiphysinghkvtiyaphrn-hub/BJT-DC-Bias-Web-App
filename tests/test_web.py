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


if __name__ == "__main__":
    unittest.main()
