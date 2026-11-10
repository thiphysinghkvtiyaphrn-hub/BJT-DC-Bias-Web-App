# BJT DC Bias Web App — Design

**Course:** ENG29 2121 · Lab 02 · 2/2569
**Date:** 2026-11-10
**Status:** Awaiting approval

---

## 1. Intent and why

นักศึกษาต้องสร้าง Web Application จริงที่มี Python Backend คำนวณ DC Operating
Point ของวงจรขยาย BJT Common-Emitter แบบ Voltage-Divider Bias แล้วแสดงผลใน
Browser ผ่าน Flask

เหตุผล: ให้เห็นความแตกต่างระหว่าง "HTML ไฟล์เดียว" กับ "Web App ที่มี Server
คำนวณ" และให้มีระบบที่ตรวจสอบได้ (tests) พร้อมส่งต่อยอดในสัปดาห์ถัดไป
(W3 Bias Templates, W4 SPICE, W5 AC) โดยไม่ต้องรื้อโครงสร้าง

งานนี้เป็น **vertical slice แรก** ของ Virtual Transistor Laboratory

## 2. Goals

1. เปิด `http://127.0.0.1:5000/` แล้วเห็นฟอร์มกรอกค่าได้
2. กด **Calculate DC Bias** แล้วได้ผลจาก Python จริง (ไม่ใช่ค่าคงที่ใน HTML)
3. ผลลัพธ์ตรงกับ independent calculation ภายใต้แบบจำลองเดียวกัน
4. ข้อมูลผิด → error ที่อ่านรู้เรื่อง หน้าไม่ล้ม
5. นอก Forward-Active → warning ชัดเจน
6. มี automated tests และ commit ผ่าน GitHub Desktop

## 3. Non-goals

- AC small-signal, gain, Bode plot
- Transient, signal generator
- Fixed bias / emitter bias templates
- SPICE / ngspice integration
- FET
- Interactive schematic (ลากวางอุปกรณ์)
- Login / database / deployment บน server จริง

## 4. Anti-goals (ล้มเหลวแม้ technically ทำงาน)

- ตัวเลขผลลัพธ์ hardcode ใน HTML หรือ JavaScript
- คำนวณใน JavaScript แทน Python backend
- แสดงผลโดยไม่มีหน่วย
- แสดงค่าใน Saturation/Cutoff ราวกับแม่นยำ โดยไม่มี warning
- Test ที่ assert ว่าตัวเอง "ผ่าน" โดยไม่ได้ตรวจค่าจริง

## 5. Constraints

- Python 3.9+ (ทดสอบบน 3.15.2), Flask 3.1.3, `unittest` (stdlib) เท่านั้น
- โครงสร้างหลายไฟล์ตามที่รายวิชากำหนด
- `dc_bias.py` ต้องไม่ import Flask และไม่รู้จัก HTML/HTTP
- Commit ผ่าน GitHub Desktop, branch `main`
- ค่าอ้างอิง: VCC=12 V, R1=100 kΩ, R2=22 kΩ, RC=2.2 kΩ, RE=1 kΩ, β=100, VBE=0.70 V
  → VTH=2.1639 V, RTH=18.033 kΩ, IB=12.298 µA, IC=1.2298 mA, IE=1.2421 mA,
    VE=1.2421 V, VB=1.9421 V, VC=9.2944 V, VCE=8.0524 V (Forward Active)
- แบบจำลอง Forward-Active Approximation: β คงที่, VBE คงที่ ไม่คิด Early effect

## 6. Approaches considered

### A. Route เดียว `/` รองรับ GET + POST

- ข้อดี: โค้ดน้อยที่สุด template เดียว
- ข้อเสีย: แยก "แสดงฟอร์ม" กับ "คำนวณ" ไม่ออกจากกันในระดับ route ทำให้ test
  ต้องแยกด้วย method และกด refresh แล้วส่งซ้ำ (resubmit)

### B. แยก route: `GET /` และ `POST /calculate` ← **เลือกข้อนี้**

- ข้อดี: แต่ละ route มีหน้าที่เดียว, test เขียนตรงไปตรงมา (`client.post("/calculate", data=...)`),
  ตรงกับข้อ A2 ของ Lab ที่ระบุ `POST /calculate หรือ POST /` และขยายเป็น
  `/calculate/<bias_type>` ใน W3 ได้โดยไม่รื้อ
- ข้อเสีย: เพิ่ม route หนึ่งอัน และ template ต้องรับตัวแปรผลลัพธ์แบบ optional

### C. JSON API `/api/calculate` + JavaScript fetch

- ข้อดี: UI อัปเดตโดยไม่ reload เหมาะกับกราฟใน W5+
- ข้อเสีย: ขัดเจตนาของ Lab ที่ต้องการให้ Flask render HTML, เพิ่ม JS ที่ต้อง
  test แยก, เพิ่ม failure mode (fetch error, JSON parse) เกินเวลาคาบ
- เหตุผลที่ไม่เลือก: over-engineering สำหรับ DC Bias หน้าเดียว

**Decision:** B — สมดุลระหว่างความชัดเจนของโครงสร้างกับเวลาที่มี
ทางเลือก A ไม่ผิด แต่ B ทำให้ acceptance test A1/A2 map ตรงกับ route จริง

## 7. Design

### 7.1 หน้าจอ (ผู้ใช้เลือกไว้)

3 คอลัมน์ในการ์ดเดียว: **Input Parameters | Circuit (static SVG) | DC Bias Results**
ด้านล่างเป็นแถบ Region status (เขียว/เหลือง/แดง) และแถบ "Calculation details"
แบบพับได้ที่แสดง VTH, RTH พร้อมสมการ

```
┌──────────────────────────────────────────────────────────────────┐
│ ◈ Lab 02 · BJT DC Bias — ENG29 2121                              │
├──────────────┬───────────────────────────┬───────────────────────┤
│ INPUT        │ CIRCUIT (SVG, static)     │ DC BIAS RESULTS       │
│ VCC [12.0] V │        VCC = 12 V         │  VB   1.942 V         │
│ R1  [100 ]kΩ │    ┌────┬────┐            │  VE   1.242 V         │
│ R2  [22  ]kΩ │   R1   RC                 │  VC   9.294 V         │
│ RC  [2.2 ]kΩ │    │    │                 │  VCE  8.052 V         │
│ RE  [1.0 ]kΩ │    ├── Q1 ──┐             │  IB  12.30 µA         │
│ β   [100 ]   │   R2   RE                 │  IC   1.230 mA        │
│ VBE [0.70] V │    │    │                 │  IE   1.242 mA        │
│ [Calculate]  │   GND  GND                │  Region: Active       │
├──────────────┴───────────────────────────┴───────────────────────┤
│ ✅ Forward active — VCE 8.05 V > 0.2 V                           │
│ ▸ Calculation details: VTH, RTH                                     │
└──────────────────────────────────────────────────────────────────┘
```

**UI language:** English (ตรงกับภาพตัวอย่างของรายวิชา; ตัวเลข/หน่วยเป็นสากล)

### 7.2 Input contract

| ช่อง | ชนิด | หน่วยกรอก | หน่วยภายใน | ค่าเริ่มต้น |
|---|---|---|---|---|
| `vcc` | float | V | V | 12.0 |
| `r1` | float | kΩ | Ω | 100 |
| `r2` | float | kΩ | Ω | 22 |
| `rc` | float | kΩ | Ω | 2.2 |
| `re` | float | kΩ | Ω | 1.0 |
| `beta` | float | – | – | 100 |
| `vbe` | float | V | V | 0.70 |

- หน่วย kΩ **คงที่** ไม่มี dropdown (ผู้ใช้เลือกแล้ว)
- แปลง kΩ → Ω ด้วย `* 1000.0` ก่อนเรียก `compute_dc_bias`
- ค่าที่กรอกต้องคงอยู่ในฟอร์มเมื่อเกิด error (ส่งกลับไปที่ template)

### 7.3 Module API (`dc_bias.py`)

```python
@dataclass(frozen=True)
class BiasResult:
    vth_v: float
    rth_ohm: float
    ib_a: float
    ic_a: float
    ie_a: float
    ve_v: float
    vb_v: float
    vc_v: float
    vce_v: float
    region: str            # "active" | "cutoff" | "saturation"
    warnings: list[str]    # ว่างได้


def compute_dc_bias(vcc_v, r1_ohm, r2_ohm, rc_ohm, re_ohm, beta, vbe_v) -> BiasResult
```

- raise `ValueError` (ข้อความภาษาอังกฤษ) เมื่อ `vcc<=0`, `r1<=0`, `r2<=0`,
  `rc<=0`, `re<=0`, `beta<=0`, หรือ `vbe<0`
- ไม่ import Flask, ไม่แตะ request/template

### 7.4 สมการ (ตามเอกสารรายวิชา)

```
VTH = VCC·R2/(R1+R2)      RTH = R1·R2/(R1+R2)
IB  = (VTH−VBE)/(RTH+(β+1)·RE)
IC  = β·IB                IE = (β+1)·IB
VE  = IE·RE               VB = VE+VBE
VC  = VCC−IC·RC           VCE = VC−VE
```

### 7.5 Region logic

ตรวจตามลำดับ (ลำดับสำคัญ เพราะกรณี cutoff ทำให้ค่าที่เหลือไม่มีความหมาย):

1. `vth_v <= vbe_v` หรือ `ib_a <= 0` → **cutoff**
   warning: "Base-emitter junction is not forward biased (VTH ≤ VBE). Forward-active results are not valid."
2. `vce_v < 0.2` → **saturation**
   warning: "VCE is below 0.2 V; the transistor may be saturated. Forward-active results are not valid."
3. มิฉะนั้น → **active** (ไม่มี warning)

threshold 0.2 V เป็น **ค่าที่เลือกใช้** (ไม่ใช่ค่าที่รายวิชากำหนด) — ระบุใน UI
ว่าเป็น approximation

**สิ่งที่แสดงเมื่ออยู่นอก active (ตัดสินแล้ว):** สมการใน §7.4 ให้ค่าที่ไม่มีความหมาย
ทางฟิสิกส์เมื่อใช้ผิด region (เช่น VCE ติดลบ, VC > VCC) จึง **ไม่นำมาแสดงเป็น
operating point**:

- ตาราง DC Bias Results แสดง `—` ทุกช่อง พร้อม region และ warning
- แถบ "Calculation details" แสดงเฉพาะ **VTH และ RTH** (ปริมาณของ bias network ที่ยัง
  คำนวณได้ถูกต้อง) พร้อมข้อความว่าไม่รายงาน operating point นอก forward-active region
  — **ไม่แสดงค่าดิบของ VB/VE/VC/VCE/IB/IC/IE** แม้จะกำกับว่าไม่ถูกต้อง เพราะตัวเลขที่ขัด
  หลักฟิสิกส์ (เช่น VCE ติดลบ) ทำให้ผู้อ่านเข้าใจผิดได้ง่ายกว่าข้อความอธิบาย
- `BiasResult` ยังคงบรรจุค่าดิบไว้ (ใช้ทดสอบและอธิบาย) แต่ template ไม่แสดง

### 7.6 Template contract (`templates/index.html`)

ตัวแปรที่ `render_template` ส่ง:

| ตัวแปร | ชนิด | ความหมาย |
|---|---|---|
| `form` | dict[str,str] | ค่าดิบจากผู้ใช้ เพื่อคงค่าในช่อง |
| `result` | `BiasResult` หรือ `None` | `None` = ยังไม่คำนวณ |
| `errors` | list[str] | ข้อความ error ระดับฟอร์ม/ฟิลด์ |
| `defaults` | dict | ค่าเริ่มต้นเมื่อเปิดหน้าครั้งแรก |

- ชื่อ field ใน HTML ตรงกับ key ที่ `app.py` อ่าน (`vcc`, `r1`, ...)
- ห้ามมีสมการหรือการคำนวณใน Jinja
- ตัวเลขจัดรูปแบบใน `app.py` (หรือ filter เล็ก ๆ) ไม่ใช่ใน `dc_bias.py`

**ป้ายในแผนผังวงจรผูกกับค่าที่กรอก (ตัดสินแล้ว):** `VCC`, `R1`, `R2`, `RC`, `RE`
ใน SVG เป็นข้อความที่ interpolate จาก `form` ผ่าน Jinja ไม่ใช่ตัวเลขตายตัว
(ถ้าผู้ใช้กรอก 15 V แผนผังต้องแสดง 15 V ไม่ใช่ 12 V) — แต่ **ไม่แสดง node voltage
ที่คำนวณได้** บนแผนผัง เพราะซ้ำกับตารางผลลัพธ์และเสี่ยงทำให้ขัดกันเอง

**ผลลัพธ์นอก active:** template ตรวจ `result.region != "active"` แล้วแสดง `—`
ในตาราง (§7.5)

### 7.7 `app.py`

- `GET /` → `render_template(..., result=None, errors=[])` → 200
- `POST /calculate` → parse → validate → compute → render → 200
- parse/domain error → render หน้าเดิมพร้อม `errors` และ **HTTP 400**
  (หน้าเว็บยังแสดงผลปกติ ไม่ crash — test ยืนยันทั้ง status และข้อความ)
- ไม่มี business logic ใน route

### 7.8 Tests

`tests/test_dc_bias.py` (engineering)
1. ค่าอ้างอิงตรงทุกตัว (tolerance สัมพัทธ์ 1e-6)
2. region == "active" สำหรับชุดอ้างอิง
3. cutoff: R1=100k, R2=1k, VCC=12 → `vth <= vbe`, region == "cutoff", `ib_a <= 0`, มี warning
4. saturation: RE=0.1k, RC=10k → region == "saturation", `vce_v < 0.2`, มี warning
5. invalid: `r1=0`, `beta=-1`, `vcc=0` → `ValueError`

`tests/test_web.py` (HTTP)
6. `GET /` → 200 และมี `name="vcc"` ในฟอร์ม
7. `POST /calculate` ชุดอ้างอิง → 200 และ HTML มี `8.05` (VCE) และ `Active`
8. `POST /calculate` ด้วย `r1=0` → 400 และมีข้อความ error
9. `POST /calculate` ด้วย `vcc=abc` → 400 และมีข้อความ error
10. `POST /calculate` ชุด cutoff (R2=1k) → 200, มี `Cutoff` + warning, และ **ไม่มี**
    ตัวเลข VCE ที่คำนวณได้แสดงในตาราง (ต้องเห็น `—`)

> หมายเหตุ: การ assert ตัวเลขใช้ทศนิยมที่จัดรูปแบบแล้ว (เช่น `1.942`, `8.05`)
> ไม่ assert ค่าดิบจาก float เพื่อกันปัญหาการปัดเศษ

### 7.9 Files

```
app.py                     routes + parsing + formatting
dc_bias.py                 dataclass + compute_dc_bias + region logic
templates/index.html       form + results + inline SVG + details block
static/style.css           3-column grid, responsive < 900px → stack
tests/test_dc_bias.py
tests/test_web.py
docs/validation.md         independent calculation ที่ตรวจด้วยมือ
README.md                  อัปเดตสถานะเป็น implemented
AGENTS.md                  (มีแล้ว)
requirements.txt           (มีแล้ว)
```

## 8. What is left to the builder

- รายละเอียดภาพ SVG (ตำแหน่งเส้น/ป้าย) — ให้ดูสมจริงและอ่านออก
  (ป้ายตัวเลขผูกกับค่าที่กรอกแล้ว ตาม §7.6)
- สีและระยะห่าง (ใช้ palette น้ำเงิน-เทาตามภาพตัวอย่าง)
- ข้อความอธิบายในแต่ละแถวของผลลัพธ์
- วิธีจัดรูปแบบตัวเลข (f-string) และการเลือกหน่วย µA/mA อัตโนมัติ
- การจัด responsive stacking

## 8.1 คำถามจากการตรวจทานพร้อมคำตอบ (ผู้เขียนตัดสิน)

| คำถาม | คำตอบ | เหตุผล |
|---|---|---|
| แสดงค่าอะไรเมื่ออยู่นอก active | ตารางแสดง `—`, ค่าดิบอยู่ใน details | สมการให้ค่าไร้ความหมาย (VCE ติดลบ) การแสดงเป็น operating point ขัด anti-goal |
| ป้ายใน SVG ตายตัวหรือผูกกับ input | ผูกกับ input เฉพาะค่าอุปกรณ์ | ป้าย 12 V ค้างขณะผู้ใช้กรอก 15 V คือการ hardcode ที่ผิด |


## 9. Acceptance mapping

| เกณฑ์ | ถูกครอบด้วย |
|---|---|
| A1 GET / | §7.7, test 6 |
| A2 POST คำนวณจริง | §7.7, test 7 |
| A3 ตรงค่าอ้างอิง | §7.4, test 1, `docs/validation.md` |
| A4 Validation | §7.3, §7.7, tests 5, 8, 9 |
| A5 Warning นอก region | §7.5, tests 3, 4 |
| A6 Tests | §7.8 (9 tests) |
| A7 Reproducibility | README + requirements.txt |
