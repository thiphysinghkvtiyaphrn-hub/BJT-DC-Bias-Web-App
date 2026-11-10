# Validation — BJT DC Bias Web App

เอกสารนี้ตรวจสอบว่าเว็บคำนวณตรงกับ **การคำนวณด้วยมือ** (independent hand
calculation) ไม่ใช่แค่เอาค่าที่โค้ดให้มาใส่ซ้ำ

- สมการอ้างอิง: `docs/superpowers/specs/2026-11-10-bjt-dc-bias-design.md` §7.4
- โค้ดที่ตรวจ: `dc_bias.py::compute_dc_bias`
- หน้าจอที่ตรวจ: `POST /calculate` (เทมเพลต `templates/index.html`)
- ตรวจเมื่อ: 2026-11-10

## 1. ชุดค่าอ้างอิง

| พารามิเตอร์ | ค่า | หน่วย |
|---|---|---|
| VCC | 12 | V |
| R1 | 100 | kΩ |
| R2 | 22 | kΩ |
| RC | 2.2 | kΩ |
| RE | 1 | kΩ |
| β | 100 | — |
| VBE | 0.70 | V |

## 2. คำนวณด้วยมือทีละขั้น

ขั้นที่ 1 — แปลงหน่วยความต้านทานเป็นโอห์ม

```
R1 = 100 kΩ = 100 000 Ω
R2 =  22 kΩ =  22 000 Ω
RC = 2.2 kΩ =   2 200 Ω
RE =   1 kΩ =   1 000 Ω
```

ขั้นที่ 2 — Thevenin equivalent ของตัวแบ่งแรงดันที่เบส

```
VTH = VCC · R2 / (R1 + R2)
    = 12 · 22 000 / (100 000 + 22 000)
    = 264 000 / 122 000
    = 2.163934 V

RTH = R1 · R2 / (R1 + R2)
    = (100 000 · 22 000) / 122 000
    = 18 032.786885 Ω
```

ขั้นที่ 3 — กระแสเบสจากลูป BE (forward-active, VBE คงที่)

```
IB = (VTH − VBE) / (RTH + (β + 1)·RE)
   = (2.163934 − 0.70) / (18 032.786885 + 101 · 1 000)
   = 1.463934 / (18 032.786885 + 101 000)
   = 1.463934 / 119 032.786885
   = 1.2298581 × 10⁻⁵ A
   = 12.298581 µA
```

ขั้นที่ 4 — กระแส Collector และ Emitter

```
IC = β · IB  = 100 · 12.298581 µA = 1.2298581 mA
IE = (β+1) · IB = 101 · 12.298581 µA = 1.2421567 mA
```

ขั้นที่ 5 — แรงดันที่ขา

```
VE  = IE · RE = 1.2421567 mA · 1 kΩ = 1.242157 V
VB  = VE + VBE = 1.242157 + 0.70     = 1.942157 V
VC  = VCC − IC · RC = 12 − 1.2298581 mA · 2.2 kΩ
    = 12 − 2.705688 = 9.294312 V
VCE = VC − VE = 9.294312 − 1.242157  = 8.052155 V
```

ขั้นที่ 6 — ตรวจ region

```
VTH = 2.164 V > VBE = 0.70 V   → เบส forward bias
IB  = 12.3 µA > 0              → มีกระแสเบส
VCE = 8.052 V > 0.2 V          → ไม่อิ่มตัว
∴ region = Active
```

## 3. เปรียบเทียบ ค่ามือ vs ค่าที่เว็บแสดง

ค่าที่เว็บแสดงถูกจัดรูปแบบ 3 ตำแหน่งทศนิยม (`app.py::build_display`)

| ปริมาณ | ค่ามือ (คำนวณ) | ค่ามือ (ปัด) | เว็บแสดง | ตรงกัน |
|---|---|---|---|---|
| VTH | 2.163934 V | 2.164 V | 2.164 V | ✅ |
| RTH | 18 032.787 Ω | 18.033 kΩ | 18.033 kΩ | ✅ |
| IB | 12.298581 µA | 12.30 µA | 12.30 µA | ✅ |
| IC | 1.2298581 mA | 1.230 mA | 1.230 mA | ✅ |
| IE | 1.2421567 mA | 1.242 mA | 1.242 mA | ✅ |
| VE | 1.242157 V | 1.242 V | 1.242 V | ✅ |
| VB | 1.942157 V | 1.942 V | 1.942 V | ✅ |
| VC | 9.294312 V | 9.294 V | 9.294 V | ✅ |
| VCE | 8.052155 V | 8.052 V | 8.052 V | ✅ |
| Region | Active | Active | Active (เขียว) | ✅ |

> หมายเหตุ: `IB` ปัดเป็น `12.30 µA` ไม่ใช่ `12.299` เพราะค่าจริงคือ 12.298581
> ซึ่งปัดที่ทศนิยม 2 ตำแหน่ง (หน่วย µA) ได้ 12.30

## 4. ยืนยันด้วย automated tests

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

ค่าคงที่ใน `tests/test_dc_bias.py::REFERENCE` ถูก assert ด้วย tolerance ที่เข้มกว่า
ตารางข้างบนมาก:

| กลุ่ม | วิธี assert | tolerance |
|---|---|---|
| IB, IC, IE | `assertAlmostEqual(..., places=9)` | ±5×10⁻¹⁰ (หน่วย A) |
| VTH, RTH, VE, VB, VC, VCE | `assertAlmostEqual(..., places=5–8)` | ±5×10⁻⁶ ถึง ±5×10⁻⁹ |
| ความสัมพันธ์ | `assertAlmostEqual(..., places=12)` | IC = β·IB, IE = (β+1)·IB, VCE = VC − VE |

`places=9` หมายถึงเมื่อปัดผลต่างเป็นทศนิยม 9 ตำแหน่งแล้วต้องเท่ากัน — แน่นกว่าระดับ
ที่หน้าจอแสดง (3 ตำแหน่ง) หลายล้านเท่า ดังนั้นตัวเลขบนหน้าจอจึงไม่ใช่การ hardcode
แต่มาจากสมการจริง

## 5. ตรวจกรณีผิดปกติ (นอก forward-active)

| กรณี | อินพุต | ผลที่คาด | ผลจริง |
|---|---|---|---|
| Cutoff | `R2 = 1 kΩ` → VTH = 0.119 V | region `cutoff`, ตาราง `—` ทุกช่อง, ไม่มีตัวเลข VCE | ✅ ผ่าน (`test_cutoff_region`, `test_cutoff_page_hides_values`) |
| Saturation | `RE = 0.1 kΩ`, `RC = 10 kΩ` → VCE ≈ −45.3 V (< 0.2 V) | region `saturation`, warning | ✅ ผ่าน (`test_saturation_region`) |
| ตัวต้านทานเป็นศูนย์ | `R1 = 0` | HTTP 400 + "R1 must be greater than zero." | ✅ ผ่าน (`test_zero_resistance_returns_400`) |
| ค่าที่ไม่ใช่ตัวเลข | `VCC = "abc"` | HTTP 400 + ฟอร์มคงค่าเดิม | ✅ ผ่าน (`test_non_numeric_value_returns_400`, `test_form_keeps_submitted_values_on_error`) |

## 6. ข้อจำกัดที่ยังเหลือ

- เป็น forward-active approximation (β คงที่, VBE คงที่) ไม่ใช่ผล SPICE
- threshold 0.2 V เป็นค่าที่เลือกใช้ ไม่ใช่ค่าที่รายวิชากำหนด
- ไม่ได้ทดสอบกับ ngspice เพราะอยู่นอกขอบเขต Lab 02
