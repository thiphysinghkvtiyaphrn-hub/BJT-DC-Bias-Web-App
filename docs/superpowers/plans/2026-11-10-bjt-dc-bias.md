# BJT DC Bias Web App — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (native, recommended for this size) or superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Flask Web App หลายไฟล์ที่รับพารามิเตอร์วงจร BJT แล้วคำนวณ DC Operating Point ด้วย Python พร้อม validation, region warning และ tests

**Architecture:** `dc_bias.py` เป็น pure-Python engineering module (ไม่มี Flask) → `app.py` เป็นชั้น HTTP ที่ parse/format แล้วเรียก module → `templates/index.html` + `static/style.css` แสดงผลแบบ 3 คอลัมน์ มี inline SVG ที่ป้ายผูกกับค่าที่กรอก

**Tech Stack:** Python 3.9+ (ทดสอบ 3.15.2), Flask 3.1.3, `unittest` (stdlib), Jinja2, CSS Grid

**Spec:** `docs/superpowers/specs/2026-11-10-bjt-dc-bias-design.md`

## Global Constraints

- `dc_bias.py` **ห้าม** import flask และห้ามรู้จัก HTML/HTTP/request
- `app.py` **ห้าม** มีสมการฟิสิกส์ และห้าม hardcode ผลลัพธ์
- `templates/index.html` **ห้าม** คำนวณ — รับค่าที่จัดรูปแบบแล้วเท่านั้น
- ภายในใช้ SI (V, A, Ω); แปลง kΩ → Ω ด้วย `* 1000.0` ก่อนเรียก `compute_dc_bias`
- หน่วย kΩ คงที่ ไม่มี dropdown; UI ภาษาอังกฤษ
- Region: `"active"` | `"cutoff"` | `"saturation"`; cutoff เมื่อ `vth_v <= vbe_v` หรือ `ib_a <= 0`; saturation เมื่อ `vce_v < 0.2`
- เมื่อ `region != "active"`: ตารางแสดง `—` และมี warning; ค่าดิบอยู่ใน details block
- ค่าอ้างอิง (ห้ามแก้): VCC=12, R1=100k, R2=22k, RC=2.2k, RE=1k, β=100, VBE=0.70
  → VTH=2.163934426, RTH=18032.786885, IB=1.229858e-05, IC=1.229858e-03,
    IE=1.2421567e-03, VE=1.2421567, VB=1.9421567, VC=9.2943121, VCE=8.0521554
- Dependency ใหม่: **ห้าม** เพิ่ม (ใช้ stdlib `unittest` เท่านั้น)
- Commit ทำโดยมนุษย์ผ่าน **GitHub Desktop** — executor หยุดที่ขั้น commit และขอให้ผู้ใช้กด
- รันคำสั่งทั้งหมดจาก repo root `C:\Users\b6806828\Documents\GitHub\BJT DC Bias Web App`
  ด้วย `.venv\Scripts\python.exe`

## Review Focus

1. **ช่องว่างหรือค่าที่ไม่ใช่ตัวเลข** (`""`, `"abc"`, `"12V"`) → ต้องได้ 400 + ข้อความอ่านรู้เรื่อง ไม่ใช่ 500 — Task 3, test `test_non_numeric_value_returns_400`
2. **ตัวต้านทานเป็น 0 หรือติดลบ** (`r1=0` ทำให้ `R1+R2` เป็น 0 → หารด้วยศูนย์) → ต้องได้ 400 ไม่ใช่ 500 — Task 1 `test_zero_resistance_raises` + Task 3 `test_zero_resistance_returns_400`
3. **`VBE` สูงจนเกิน `VTH`** → ต้องได้ region `cutoff` + warning และ **ไม่แสดงตัวเลขที่คำนวณได้** — Task 2 `test_cutoff_region`, Task 4 `test_cutoff_page_hides_values`
4. **`RC` ใหญ่จน `VCE` ติดลบ** → ต้องได้ `saturation` + warning — Task 2 `test_saturation_region`
5. **ค่าที่กรอกต้องคงอยู่ในฟอร์มหลัง error** (ไม่ล้างเป็นค่าเริ่มต้น) — Task 3 `test_form_keeps_submitted_values_on_error`

---

### Task 1: Engineering core — สมการและ input validation

**Files:**
- Create: `dc_bias.py`
- Test: `tests/test_dc_bias.py`

**Interfaces:**
- Consumes: ไม่มี
- Produces:
  - `@dataclass(frozen=True) class BiasResult` — fields: `vth_v, rth_ohm, ib_a, ic_a, ie_a, ve_v, vb_v, vc_v, vce_v: float`, `region: str`, `warnings: list[str]`
  - `compute_dc_bias(vcc_v: float, r1_ohm: float, r2_ohm: float, rc_ohm: float, re_ohm: float, beta: float, vbe_v: float) -> BiasResult`

- [ ] **Step 1: เขียน failing tests**

```python
# tests/test_dc_bias.py
import unittest

from dc_bias import compute_dc_bias

REFERENCE = dict(
    vcc_v=12.0, r1_ohm=100_000.0, r2_ohm=22_000.0, rc_ohm=2_200.0,
    re_ohm=1_000.0, beta=100.0, vbe_v=0.70,
)


class TestReferencePoint(unittest.TestCase):
    def test_reference_values(self):
        r = compute_dc_bias(**REFERENCE)
        self.assertAlmostEqual(r.vth_v, 2.163934426, places=8)
        self.assertAlmostEqual(r.rth_ohm, 18032.786885, places=5)
        self.assertAlmostEqual(r.ib_a, 1.229858e-05, delta=1e-12)
        self.assertAlmostEqual(r.ic_a, 1.229858e-03, delta=1e-12)
        self.assertAlmostEqual(r.ie_a, 1.242157e-03, delta=1e-12)
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
```

- [ ] **Step 2: รันให้เห็นว่า fail**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_dc_bias.py" -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dc_bias'`

- [ ] **Step 3: implement `dc_bias.py`**

`compute_dc_bias` ตรวจ `vcc_v<=0`, `r1_ohm<=0`, `r2_ohm<=0`, `rc_ohm<=0`, `re_ohm<=0`, `beta<=0`, `vbe_v<0` แล้ว raise `ValueError` (ข้อความอังกฤษ เช่น `"VCC must be greater than zero."`) จากนั้นคำนวณตามสมการใน spec §7.4 และคืน `BiasResult` โดย `region="active"` และ `warnings=[]` (region logic จริงอยู่ใน Task 2)

- [ ] **Step 4: รันให้ผ่าน**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_dc_bias.py" -v`
Expected: PASS 3 tests

- [ ] **Step 5: หยุดรอ commit** — แจ้งผู้ใช้ commit ผ่าน GitHub Desktop: `feat: add dc bias calculation core`

---

### Task 2: Region detection และ warnings

**Files:**
- Modify: `dc_bias.py` (หลังคำนวณค่าเสร็จ ก่อนคืน `BiasResult`)
- Test: `tests/test_dc_bias.py` (เพิ่มคลาส)

**Interfaces:**
- Consumes: `compute_dc_bias(...)` จาก Task 1
- Produces: `BiasResult.region` ∈ `{"active","cutoff","saturation"}`, `BiasResult.warnings: list[str]`

- [ ] **Step 1: เขียน failing tests**

```python
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
```

- [ ] **Step 2: รันให้เห็นว่า fail**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_dc_bias.py" -v`
Expected: FAIL — region เป็น `"active"` ในทั้งสองเคสใหม่

- [ ] **Step 3: implement region logic ตามลำดับใน spec §7.5**

cutoff ต้องตรวจก่อน saturation เสมอ

- [ ] **Step 4: รันให้ผ่าน**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_dc_bias.py" -v`
Expected: PASS 6 tests

- [ ] **Step 5: หยุดรอ commit** — `feat: detect cutoff and saturation regions`

---

### Task 3: Flask routes, parsing และ formatting

**Files:**
- Create: `app.py`
- Test: `tests/test_web.py`

**Interfaces:**
- Consumes: `compute_dc_bias(...)` และ `BiasResult` จาก Task 1–2
- Produces:
  - `app` (module-level `Flask` instance) สำหรับ test client
  - template variables: `form: dict[str,str]`, `result: BiasResult | None`, `errors: list[str]`, `defaults: dict[str,str]`, `display: dict[str,str] | None`
  - `display` keys: `vth, rth, ib, ic, ie, ve, vb, vc, vce` (ค่าที่จัดรูปแบบแล้วพร้อมหน่วย)

- [ ] **Step 1: เขียน failing tests**

```python
# tests/test_web.py
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
        self.assertIn("8.052", html)     # VCE
        self.assertIn("12.30", html)     # IB
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
```

- [ ] **Step 2: รันให้เห็นว่า fail**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_web.py" -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 3: implement `app.py`**

`GET /` → `render_template("index.html", form=defaults, result=None, errors=[], defaults=defaults, display=None)`
`POST /calculate` → อ่าน `request.form.get(name, "")` ทั้ง 7 ช่อง → `float()` ต่อช่อง (error ระบุชื่อช่อง) → เรียก `compute_dc_bias` (จับ `ValueError` เป็น error) → สร้าง `display` แล้ว render
ตัวจัดรูปแบบ: แรงดัน `f"{x:.3f} V"`; กระแส `f"{a*1e3:.3f} mA"` เมื่อ `abs(a) >= 1e-3` มิฉะนั้น `f"{a*1e6:.2f} µA"`

- [ ] **Step 4: รันให้ผ่าน**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_web.py" -v`
Expected: FAIL เท่านั้นที่ `test_get_index_returns_form` และ `test_calculate_returns_reference_values` เพราะยังไม่มี `templates/index.html` — อีก 3 tests ต้อง PASS

- [ ] **Step 5: หยุดรอ commit** — `feat: add Flask routes with validation`

---

### Task 4: หน้าเว็บ (3 คอลัมน์ + SVG + details)

**Files:**
- Create: `templates/index.html`, `static/style.css`
- Test: `tests/test_web.py` (เพิ่ม)

**Interfaces:**
- Consumes: `form`, `result`, `errors`, `defaults`, `display` จาก Task 3
- Produces: HTML ที่ test ทั้งหมดใน Task 3 ผ่าน

- [ ] **Step 1: เขียน failing test**

```python
    def test_cutoff_page_hides_values(self):
        resp = self.client.post("/calculate", data={**VALID, "r2": "1"})
        html = resp.get_data(as_text=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Cutoff", html)
        self.assertIn("—", html)                    # ตารางแสดง — แทนตัวเลข
        self.assertNotIn("13.5", html)              # ไม่โชว์ VCE ที่คำนวณได้ (13.6 V)
```

- [ ] **Step 2: รันให้เห็นว่า fail**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_web.py" -v`
Expected: FAIL 3 tests (ยังไม่มี template)

- [ ] **Step 3: สร้าง `templates/index.html` และ `static/style.css`**

- 3 คอลัมน์: Input Parameters | Circuit | DC Bias Results (grid, พับเป็นคอลัมน์เดียวต่ำกว่า 900px)
- SVG: `VCC = {{ form.vcc }} V`, `R1 {{ form.r1 }} kΩ`, `R2 {{ form.r2 }} kΩ`, `RC {{ form.rc }} kΩ`, `RE {{ form.re }} kΩ` — **ห้าม**ใส่ node voltage ที่คำนวณได้
- ฟอร์ม: 7 ช่อง `name` ตรงกับ key (`vcc, r1, r2, rc, re, beta, vbe`), `value="{{ form.vcc }}"`, ปุ่ม `Calculate DC Bias`
- ผลลัพธ์: แถว `VB, VE, VC, VCE, IB, IC, IE` ใช้ `display[...]`; ถ้า `result` เป็น `None` แสดง `—`
- Region banner: เขียว `Active`, เหลือง `Cutoff`, แดง `Saturation` + แสดง `result.warnings`
- details block (`<details>`): VTH, RTH, และถ้าไม่ใช่ active ให้แสดงค่าดิบพร้อมข้อความ "computed under forward-active assumption — not a valid operating point"
- error block: แสดง `errors` ทั้งหมดเหนือฟอร์ม

- [ ] **Step 4: รันให้ผ่านทั้งหมด**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: PASS 10 tests

- [ ] **Step 5: ตรวจด้วยตา** — `.venv\Scripts\python.exe -m flask --app app run --debug` แล้วเปิด `http://127.0.0.1:5000/` กรอกค่าอ้างอิง ต้องเห็น VCE 8.052 V และ banner เขียว

- [ ] **Step 6: หยุดรอ commit** — `feat: build three-column DC bias UI`

---

### Task 5: เอกสารตรวจสอบและ README

**Files:**
- Create: `docs/validation.md`
- Modify: `README.md` (บรรทัดสถานะ + ส่วน "การรัน")

**Interfaces:**
- Consumes: ผลลัพธ์จริงจาก Task 4
- Produces: เอกสารสำหรับ A3 และ A7

- [ ] **Step 1: เขียน `docs/validation.md`** — คำนวณด้วยมือทีละขั้น (VTH, RTH, IB, IC, IE, VE, VB, VC, VCE) แสดงเลข intermediate และตารางเทียบค่ามือ vs ค่าเว็บ พร้อม tolerance ที่ใช้

- [ ] **Step 2: อัปเดต `README.md`** — เปลี่ยนสถานะจาก "Scaffolding" เป็น "Implemented", ระบุจำนวน tests และคำสั่งที่ใช้จริง

- [ ] **Step 3: ตรวจว่าไม่มีอะไรหลุด**

Run: `git status --short` และ `git diff --stat`
Expected: เห็นเฉพาะไฟล์ใน Task 1–5 ไม่มี `.venv/`, `__pycache__/`

- [ ] **Step 4: หยุดรอ commit** — `docs: add validation record and update README`

---

## Acceptance checklist หลังจบ Task 5

- [ ] A1 `GET /` → 200 + ฟอร์ม
- [ ] A2 `POST /calculate` → ผลจาก Python (แก้สมการแล้วค่าต้องเปลี่ยน)
- [ ] A3 ตรงกับ `docs/validation.md`
- [ ] A4 `r1=0`, `vcc=abc` → 400 + error
- [ ] A5 cutoff/saturation → warning + ไม่แสดงตัวเลข
- [ ] A6 10 tests ผ่านทั้งหมด
- [ ] A7 clone ใหม่ → `pip install -r requirements.txt` → รัน + test ตาม README ได้
