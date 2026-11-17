# Lab 03 — BJT Three Bias Modes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (Native) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** เพิ่ม Fixed Bias และ Emitter Bias ให้เว็บ Flask เดิม โดยคงผล Voltage Divider เดิมไว้ และเลือกโหมดได้ผ่านแท็บ

**Architecture:** `dc_bias.py` เป็นโมดูลวิศวกรรมล้วน (คืน `BiasResult` ที่เป็น dict) → `app.py` เลือกฟังก์ชันตาม `mode`, ตรวจเฉพาะช่องที่ใช้, แปลง kΩ→Ω จุดเดียว → `templates/index.html` แสดงแท็บ ฟอร์มตามโหมด ผลลัพธ์ และ SVG 3 แบบ

**Tech Stack:** Python 3.15 (ใช้ได้ 3.9+), Flask 3.1, Jinja2, `unittest`, CSS Grid

**Spec:** `docs/superpowers/specs/2026-11-17-bjt-three-bias-modes-design.md`

## Global Constraints

- `dc_bias.py` ห้าม import Flask/HTML/HTTP
- `app.py` ห้ามมีสมการฟิสิกส์ และห้าม hardcode ผลลัพธ์
- `templates/index.html` ห้ามคำนวณ — รับค่าที่จัดรูปแบบแล้ว
- หน่วย SI ภายใน (V, A, Ω); แปลง kΩ → Ω ด้วย `* 1000.0` จุดเดียว
- ฟอร์มใช้ kΩ คงที่; `1 MΩ = 1000 kΩ`
- UI ภาษาอังกฤษ; `label for` ตรงกับ `id`
- โหมด: `divider` | `fixed` | `emitter`
- Region: `IB <= 0` → cutoff; `VCE <= 0.2` → saturation; อื่น ๆ active
- อินพุตต้อง `math.isfinite`; ค่าที่ต้องเป็นบวก ≤ 0 → error
- `POST /calculate` ไม่ส่ง `mode` → ถือเป็น `divider`; ส่งค่าที่ไม่รู้จัก → 400
- ทุก error path ต้องไม่แสดงผลรอบก่อน (`result=None`)
- IC แสดงเป็น mA เสมอ; IB/IE ใช้ µA เมื่อ < 1 mA
- ไม่เพิ่ม dependency; ไม่แตะ `requirements.txt`
- Commit ทำโดยผู้ใช้ผ่าน GitHub Desktop — executor หยุดที่รายการ commit
- รันคำสั่งจาก repo root ด้วย `.venv\Scripts\python.exe`

## Review Focus

1. **`mode` ไม่ถูกส่งมา** (client เก่า/tests เดิม) → ต้องทำงานเป็น Divider ไม่ใช่ 400 — Task 2
2. **`mode=foo`** → ต้องได้ 400 และไม่ถูกตีความเป็น Divider — Task 2
3. **Fixed mode ที่ไม่มีช่อง RE** → ต้องคำนวณได้โดยไม่เรียก `re` — Task 1/Task 2
4. **`RB=0`** → 400 พร้อมข้อความ RB และไม่มีผลค้าง — Task 2
5. **`inf`/`nan`** ในช่องใดก็ได้ → 400 ไม่ใช่ 500 — Task 1/Task 2
6. **Divider ต้องคงผลเดิม** หลัง refactor เป็น dict — Task 1/Task 2

---

### Task 1: Engineering core — dict contract + Fixed/Emitter

**Files:**
- Modify: `dc_bias.py`
- Test: `tests/test_dc_bias.py` (เพิ่มคลาส)

**Interfaces:**
- Consumes: ไม่มี
- Produces:
  - `class BiasResult(dict)` — อ่าน attribute ได้ (`r.vb_v`) และ `r["vb_v"]` ได้
  - `compute_dc_bias(vcc_v, r1_ohm, r2_ohm, rc_ohm, re_ohm, beta, vbe_v) -> BiasResult` (signature เดิม)
  - `compute_fixed_bias(vcc_v, rb_ohm, rc_ohm, beta, vbe_v) -> BiasResult`
  - `compute_emitter_bias(vcc_v, rb_ohm, re_ohm, rc_ohm, beta, vbe_v) -> BiasResult`
  - คีย์: `mode, ib_a, ic_a, ie_a, ic_ma, vb_v, ve_v, vc_v, vce_v, region, warnings` (+ `vth_v, rth_ohm` เฉพาะ divider)

- [ ] **Step 1: เขียน failing tests**

```python
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
```

- [ ] **Step 2: รันให้เห็นว่า fail**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_dc_bias.py" -v`
Expected: FAIL — `ImportError: cannot import name 'compute_fixed_bias'`

- [ ] **Step 3: implement `dc_bias.py`**

- เปลี่ยน `BiasResult` เป็น `class BiasResult(dict)` พร้อม `__getattr__` ที่อ่าน key และ raise `AttributeError` เมื่อไม่มี
- เพิ่ม `_require_finite(value, name)` เรียกก่อน `_require_positive`
- แชร์ `_solve(vcc_v, rc_ohm, beta, vbe_v, ib_a, mode, ve_v, extra)` ที่คำนวณ `ic_a, ie_a, ve_v, vb_v, vc_v, vce_v, region, warnings` และคืน `BiasResult` (คีย์ `ic_ma = ic_a * 1000.0`)
- `compute_dc_bias` คง signature เดิม แต่คำนวณ `vth_v, rth_ohm` แล้วส่งเข้า `_solve`
- Fixed: `ib_a = (vcc_v - vbe_v) / rb_ohm`, `ve_v = 0.0`
- Emitter: `ib_a = (vcc_v - vbe_v) / (rb_ohm + (beta+1)*re_ohm)`, `ve_v = ie_a * re_ohm`
- Region: `ib_a <= 0` → cutoff, `vce_v <= 0.2` → saturation
- Warning ใช้ข้อความกลาง: "Base current is not positive (IB <= 0). Forward-active results are not valid." และ "VCE is at or below 0.2 V; the transistor may be saturated. Forward-active results are not valid."

- [ ] **Step 4: รันให้ผ่าน**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_dc_bias.py" -v`
Expected: PASS ทุกตัว (13 เดิม + ใหม่)

- [ ] **Step 5: หยุดรอ commit** — `feat: add fixed and emitter bias calculations`

---

### Task 2: Flask mode dispatch และ conditional fields

**Files:**
- Modify: `app.py`
- Test: `tests/test_web.py` (เพิ่มคลาส)

**Interfaces:**
- Consumes: `compute_dc_bias`, `compute_fixed_bias`, `compute_emitter_bias` จาก Task 1
- Produces:
  - `MODES: dict[str,str]`, `MODE_FIELDS: dict[str,tuple[str,...]]`
  - `GET /?mode=<divider|fixed|emitter>`
  - `POST /calculate` รับ `mode` (ไม่บังคับ, ค่าเริ่มต้น divider)
  - template vars: `mode, mode_label, modes, fields, form, result, errors, defaults, display`

- [ ] **Step 1: เขียน failing tests**

```python
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
```

- [ ] **Step 2: รันให้เห็นว่า fail**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_web.py" -v`
Expected: FAIL — `name="rb"` ไม่มี / mode ถูกเมิน

- [ ] **Step 3: implement `app.py`**

- `MODES = {"divider": "Voltage Divider Bias", "fixed": "Fixed Bias", "emitter": "Emitter Bias"}`
- `MODE_FIELDS` ตาม design §7.2
- `DEFAULTS` แยกตามโหมด (divider ค่าเดิม; fixed/emitter `rb="1000"`)
- `parse_fields(form, mode)` วนเฉพาะ `MODE_FIELDS[mode]`; ตรวจ `math.isfinite`
- `to_si(values)` แปลง kΩ → Ω (`vcc`, `vbe` เป็น V ตรง ๆ; `beta` ไม่แปลง)
- `compute_for_mode(mode, si)` dispatch; โหมดอื่น raise `ValueError("Unknown bias mode.")`
- `index()`: `mode = request.args.get("mode", "divider")`; ถ้าไม่รู้จัก → `render_page(..., errors=[...], status=400)`
- `calculate()`: `mode = request.form.get("mode") or "divider"`; ถ้าไม่รู้จัก → 400; parse ตามโหมด; error → 400 `result=None`
- `render_page` ส่ง context ครบ; `build_display` สร้าง `vth`/`rth` เฉพาะ `result["mode"] == "divider"`
- `format_current` เดิม; เพิ่ม `format_ic(amps)` ที่บังคับ mA 3 ตำแหน่ง

- [ ] **Step 4: รันให้ผ่าน**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_web.py" -v`
Expected: PASS ทุกตัว (6 เดิม + ใหม่)

- [ ] **Step 5: หยุดรอ commit** — `feat: dispatch bias mode in Flask routes`

---

### Task 3: หน้าเว็บ — แท็บโหมด + 3 SVG + ผลลัพธ์

**Files:**
- Modify: `templates/index.html`
- Modify: `static/style.css`
- Test: `tests/test_web.py` (เพิ่ม)

**Interfaces:**
- Consumes: template vars จาก Task 2
- Produces: HTML ที่ tests ทั้งหมดผ่าน

- [ ] **Step 1: เขียน failing test**

```python
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
```

- [ ] **Step 2: รันให้เห็นว่า fail**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_web.py" -v`
Expected: FAIL 2 tests

- [ ] **Step 3: implement template + CSS**

- หัวเรื่อง **Lab 03**; subtitle ระบุสามโหมด
- แท็บ: `{% for mode_id, label in modes %}` เป็น `<a href="{{ url_for('index', mode=mode_id) }}" aria-current="page">`
- hidden `<input type="hidden" name="mode" value="{{ mode }}">`
- ฟอร์มวน `fields` ตามโหมด; ปุ่ม Calculate ใต้ช่อง
- hint: `RB = 1 MΩ → enter 1000 (kΩ)` เฉพาะ fixed/emitter
- ผลลัพธ์: 7 แถว; IC ใช้ `display.ic` (mA); region guard เดิม (`—` เมื่อไม่ใช่ active)
- แสดง `mode_label` ในผลลัพธ์และ error banner
- details: divider → VTH/RTH; fixed → `VE = 0 V by definition`; emitter → `VE = IE × RE`
- SVG 3 แบบ: divider (ของเดิม), fixed (RB/RC/emitter→ground), emitter (RB/RE/RC)
- CSS: `.mode-tabs`, `.mode-tab`, `.mode-tab[aria-current="page"]`

- [ ] **Step 4: รันให้ผ่านทั้งหมด**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: PASS ทุกตัว

- [ ] **Step 5: ตรวจด้วยตา** — เปิด Flask ทุกโหมด ดูว่า SVG ตรงโหมดและไม่มี label ทับ

- [ ] **Step 6: หยุดรอ commit** — `feat: add bias mode tabs and circuit diagrams`

---

### Task 4: เอกสารตรวจรับ A1–A5

**Files:**
- Modify: `docs/validation.md`

**Interfaces:**
- Consumes: ผลจริงจาก Task 3
- Produces: หลักฐานสำหรับ rubric 3 คะแนน

- [ ] **Step 1: เพิ่มค่าอ้างอิงอิสระ (คำนวณมือ)** — Fixed (A2), Emitter (A3), Emitter RE=2k (A4) พร้อมสมการทีละขั้นและหน่วย
- [ ] **Step 2: เพิ่มตาราง A1–A5** — อินพุต, ค่าคาดหมาย, ผลจริง, หน่วย, วิธีตรวจ, สถานะ, หลักฐาน
- [ ] **Step 3: ระบุวิธีจริง** — `Playwright MCP = NOT RUN (Node.js/npx not installed)`, ใช้ `OpenCode Browser`
- [ ] **Step 4: ตรวจว่าไม่มีอะไรหลุด** — `git status --short` เห็นเฉพาะไฟล์ที่ตั้งใจ
- [ ] **Step 5: หยุดรอ commit** — `docs: add Lab 03 acceptance results`

---

### Task 5: README + ตรวจรวม

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: ทุก task ก่อนหน้า
- Produces: เอกสารส่งงาน

- [ ] **Step 1: อัปเดต README** — ชื่อ Lab 03, ขอบเขตสามโหมด, วิธีรัน, GitHub URL, Commit SHA (เติมหลัง commit), ส่วนที่ AI ช่วย/นักศึกษาตรวจ, คำสั่ง tests
- [ ] **Step 2: รัน tests ทั้งหมด** — `.venv\Scripts\python.exe -m unittest discover -s tests -v` → PASS
- [ ] **Step 3: ตรวจ A1–A5 ผ่าน Browser** — บันทึกผลจริงลง `docs/validation.md` และเก็บภาพอย่างน้อย 1 กรณี
- [ ] **Step 4: หยุดรอ commit** — `docs: update README for Lab 03`

---

## Acceptance Checklist

- [ ] A1 Divider ยังได้ `IC 1.230 mA`, `VCE 8.052 V`
- [ ] A2 Fixed RB=1000 kΩ คำนวณได้โดยไม่มีช่อง RE
- [ ] A3 Emitter ใช้ RE จริง
- [ ] A4 Emitter RE=2k → IC ลด, VCE ลด (บันทึกคำทำนายก่อนรัน)
- [ ] A5 Fixed RB=0 → 400 + ข้อความ RB + ไม่มีผลค้าง
- [ ] `mode=foo` → 400; ไม่ส่ง mode → Divider
- [ ] tests เดิม + ใหม่ผ่านทั้งหมด
- [ ] `docs/validation.md` มีตาราง A1–A5 + หลักฐาน
- [ ] README มีวิธีรัน + URL + SHA
