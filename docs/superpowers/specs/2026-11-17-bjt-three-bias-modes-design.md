# Lab 03 — BJT Three Bias Modes: Design

วันที่: 2026-11-17
สถานะ: รออนุมัติ (ยังไม่เริ่มแก้โค้ด)
ต่อยอดจาก: Lab 02 (`docs/superpowers/specs/2026-11-10-bjt-dc-bias-design.md`)

---

## 1. Intent และเหตุผล

ต่อยอดเว็บ Flask เดิมจาก Lab 02 ให้เลือกวงจรไบอัสได้สามแบบ
(**Voltage Divider**, **Fixed Bias**, **Emitter Bias แหล่งจ่ายเดียว**)
โดยใช้ Python คำนวณ DC Operating Point ตามโหมด และคงผลของ Divider เดิมไว้ทุกค่า
เพื่อใช้ตรวจรับผ่านเบราว์เซอร์จริงตามตาราง A1–A5 ของใบงาน Lab 03

**ผู้ใช้:** นักศึกษา ENG29 2121 (เจ้าของ repo) และผู้สอนที่ตรวจงาน

**ความสำเร็จ:** เลือกโหมด → กรอกเฉพาะช่องของโหมด → กด Calculate → เห็นผลถูกต้องพร้อมหน่วย
และ Divider ให้ผลเดิมเมื่อกรอกค่าเดิม

## 2. Goals

- เพิ่มฟังก์ชัน Fixed Bias และ Emitter Bias ใน `dc_bias.py` ตามสมการใบงาน
- `app.py` เลือกฟังก์ชันตามโหมด, ตรวจเฉพาะช่องที่โหมดใช้, แปลงหน่วยจุดเดียว
- ฟอร์มเลือกโหมดได้โดยไม่ใช้ JavaScript และเห็นเฉพาะช่องที่ใช้
- รูปวงจรตรงกับโหมดที่เลือก (3 แบบ)
- คงผล Divider เดิมและ tests เดิม 13 ตัวให้ผ่าน
- เอกสาร A1–A5 + ค่าอ้างอิงอิสระ + README ที่ระบุวิธีรัน/URL/Commit SHA

## 3. Non-goals

- ไม่ทำ AC / Transient / Bode / SPICE / DC Load Line
- ไม่แตะ Bypass capacitor
- ไม่เพิ่ม dependency ใหม่ (ใช้ Flask + stdlib)
- ไม่เขียน unittest ใหม่ (ใบงานกำหนดให้ตรวจผ่าน Browser)

## 4. Anti-goals (ถือว่าล้มเหลวถ้าเกิดขึ้น)

- Divider ให้ผลต่างจาก Lab 02 เมื่อกรอกค่าเดิม
- ผลของรอบก่อนค้างแสดงเป็นผลของอินพุตที่เพิ่งกรอกผิด
- โหมดที่ไม่รู้จักถูกตีความเป็น Divider เงียบ ๆ
- สมการถูกย้ายไปอยู่ใน HTML/JavaScript
- แสดงผลใน Cutoff/Saturation ราวกับเป็น operating point ที่ใช้ได้

## 5. Constraints (จากใบงาน)

- ทุกโหมดรับ `VCC, RC, β, VBE`; เพิ่ม `RB` (Fixed/Emitter) และ `RE` (Emitter/Divider)
- ฟอร์มใช้ **kΩ คงที่** → `1 MΩ = 1000 kΩ`; แปลง kΩ → Ω ครั้งเดียวที่จุดรับข้อมูล
- แสดง `VB, VE, VC, VCE` เป็น V และ `IC` เป็น mA
- อินพุตผิด (ไม่ครบ / ไม่ใช่ตัวเลข / ไม่จำกัด / ค่าที่ต้องบวก ≤ 0) → error
- อินพุตถูกแต่ `IB ≤ 0` หรือ `VCE ≤ 0.2 V` → warning ว่าแบบจำลอง Forward Active อาจใช้ไม่ได้
- โหมดไม่รู้จัก → error ไม่เดา
- UI ภาษาอังกฤษ (ตาม Lab 02), `label for` ตรงกับ `id`
- Commit ผ่าน GitHub Desktop เท่านั้น (ผู้ใช้กด)

## 6. Approaches ที่พิจารณา

### 6.1 การสลับโหมด (เลือกแล้ว: A)

| ทาง | ลักษณะ | ข้อดี | ข้อเสีย |
|---|---|---|---|
| **A. แท็บโหมด (เลือก)** | ลิงก์ `/?mode=fixed` โหลดหน้าใหม่ เห็นเฉพาะช่องของโหมด | ไม่ใช้ JS, Playwright คลิกแท็บได้ตรง ๆ, กันกรอกช่องผิดโหมด | เปลี่ยนโหมด = โหลดหน้าใหม่ |
| B. Dropdown + ปุ่มโหลด | เลือกแล้วกดปุ่มหนึ่งครั้ง | หน้าตาคุ้นเคย | หลายจังหวะ, ตรวจผ่าน browser ยากกว่า |
| C. แสดงทุกช่อง + disable | ฟอร์มเดียวไม่เปลี่ยน | ไม่ reload | ช่องรก, snapshot ปนช่องที่ใช้ไม่ได้ |

**เหตุผลที่เลือก A:** ตรงกับ "เห็นช่องที่ใช้เท่านั้น" ในใบงานมากที่สุด และตรวจ A1–A5 ผ่าน browser ได้ตรงไปตรงมา

**รายละเอียด UI ที่ตกลง:** แท็บอยู่บนสุดของ panel `Input Parameters`
ปุ่ม `Calculate DC Bias` อยู่ภายใน panel เดียวกัน ปิดท้ายช่องกรอก

### 6.2 รูปวงจร (เลือกแล้ว: a)

| ทาง | ลักษณะ | ข้อดี | ข้อเสีย |
|---|---|---|---|
| **a. SVG แยก 3 แบบ (เลือก)** | Divider ใช้รูปเดิม; Fixed/Emitter วาดใหม่ | ภาพตรงโหมด, ป้ายผูกค่าที่กรอก | ทำงานเพิ่ม |
| b. ซ่อน panel เมื่อไม่ใช่ Divider | แสดงข้อความสั้นแทน | เร็ว | ไม่มีภาพวงจร |
| c. ใช้รูป Divider ทุกโหมด | — | เร็วสุด | ผิดความหมาย |

### 6.3 สัญญาผลลัพธ์ (เลือกแล้ว: dict)

| ทาง | ลักษณะ | ปัญหา |
|---|---|---|
| **dict subclass + attribute access (เลือก)** | คืน `dict` ที่มีคีย์/หน่วยตรงกัน และอ่านแบบ `r.vb_v` ได้ | — |
| เปลี่ยนเป็น dict ล้วน | แก้ tests เดิม 13 ตัว | เสี่ยงทำ Divider พัง |
| คง dataclass เดิม | ไม่ตรง rubric "ส่งผลด้วย dict" | หลักฐานไม่ชัด |

**เหตุผล:** ได้ทั้ง `dict` ตาม rubric และคง tests เดิมโดยไม่ต้องแก้

---

## 7. Design

### 7.1 โมดูล `dc_bias.py`

```python
class BiasResult(dict):
    """ผลลัพธ์เป็น dict ที่อ่านแบบ attribute ได้ (คง API เดิมของ Lab 02)"""
    def __getattr__(self, name): ...
```

**คีย์ร่วมของทั้งสามโหมด**

| คีย์ | หน่วย | ความหมาย |
|---|---|---|
| `mode` | — | `"divider"` / `"fixed"` / `"emitter"` |
| `ib_a`, `ic_a`, `ie_a` | A | กระแส |
| `ic_ma` | mA | กระแส collector สำหรับแสดงผล (ตามตัวอย่างใบงาน) |
| `vb_v`, `ve_v`, `vc_v`, `vce_v` | V | แรงดัน |
| `region` | — | `"active"` / `"cutoff"` / `"saturation"` |
| `warnings` | list[str] | ข้อความเตือน |

**คีย์เพิ่มเฉพาะ Divider:** `vth_v`, `rth_ohm`

> `build_display()` ต้องสร้าง `vth`/`rth` เฉพาะเมื่อ `result["mode"] == "divider"`
> เพราะโหมดอื่นไม่มีคีย์นี้ (การเข้าถึง attribute ที่ไม่มีจะ raise)

**ฟังก์ชัน:**

```python
compute_dc_bias(vcc_v, r1_ohm, r2_ohm, rc_ohm, re_ohm, beta, vbe_v)      # เดิม, คงพฤติกรรม
compute_fixed_bias(vcc_v, rb_ohm, rc_ohm, beta, vbe_v)
compute_emitter_bias(vcc_v, rb_ohm, re_ohm, rc_ohm, beta, vbe_v)
```

**สมการ**

```
Fixed:    IB = (VCC − VBE) / RB
Emitter:  IB = (VCC − VBE) / [RB + (β+1)·RE]
Divider:  IB = (VTH − VBE) / [RTH + (β+1)·RE]

IC = β·IB;  IE = (β+1)·IB
VE = IE·RE        (Emitter, Divider)   |   Fixed: VE = 0
VB = VE + VBE
VC = VCC − IC·RC
VCE = VC − VE
```

**Validation (เหมือนกันทุกโหมด)**

- ทุกอินพุตต้อง `math.isfinite`
- `VCC, RC, β > 0`; `RB/R1/R2/RE > 0` เฉพาะโหมดที่ใช้
- `VBE ≥ 0`
- ละเมิด → `ValueError` ข้อความอังกฤษระบุชื่อช่อง

**Region (ลำดับสำคัญ)**

1. `ib_a <= 0` → `cutoff` + warning
2. `vce_v <= 0.2` → `saturation` + warning  ← ปรับจาก `< 0.2` ตามใบงาน
3. มิฉะนั้น → `active`

> Divider ยังคง cutoff เมื่อ `VTH ≤ VBE` เพราะกรณีนั้นทำให้ `IB ≤ 0` อยู่แล้ว
> และ tests เดิมยังผ่าน

### 7.2 `app.py`

```python
MODES = {
    "divider": "Voltage Divider Bias",
    "fixed":   "Fixed Bias",
    "emitter": "Emitter Bias",
}

MODE_FIELDS = {
    "divider": ("vcc", "r1", "r2", "rc", "re", "beta", "vbe"),
    "fixed":   ("vcc", "rb", "rc", "beta", "vbe"),
    "emitter": ("vcc", "rb", "re", "rc", "beta", "vbe"),
}
```

- `GET /` อ่าน `?mode=`; ไม่ระบุ → `divider`; ค่าไม่รู้จัก → 400 (render ฟอร์ม Divider + error banner)
- `POST /calculate` อ่าน `mode` จาก hidden field:
  - **ไม่ระบุ → ถือเป็น `divider`** (backward compatibility กับ tests เดิม 13 ตัวและ client เก่า)
  - **ระบุแต่ไม่รู้จัก → 400** (ไม่เดาเป็น Divider ตามใบงาน)
- `parse_fields(form, mode)` ตรวจเฉพาะช่องของโหมด + ต้องเป็นจำนวนจำกัด
- แปลงหน่วยที่ฟังก์ชันเดียว `to_si(values)` (kΩ × 1000)
- dispatch ด้วย `if / elif` ตามโหมด; โหมดอื่น → error
- ทุก error path ส่ง `result=None` → ไม่มีผลรอบก่อนค้าง
- error banner แสดงชื่อโหมดที่เลือกเป็นบรรทัดแรก
- `render_page` ส่ง `mode`, `mode_label`, `modes`, `fields`, `form`, `result`, `errors`, `display`

**ค่าเริ่มต้นของฟอร์ม**

| โหมด | ค่าเริ่มต้น |
|---|---|
| divider | VCC 12.0, R1 100, R2 22, RC 2.2, RE 1.0, β 100, VBE 0.70 |
| fixed | VCC 12.0, RB 1000 (=1 MΩ), RC 2.2, β 100, VBE 0.70 |
| emitter | VCC 12.0, RB 1000, RE 1.0, RC 2.2, β 100, VBE 0.70 |

### 7.3 `templates/index.html`

- เปลี่ยนหัวเป็น **Lab 03**
- แท็บโหมด 3 ลิงก์: `Divider | Fixed | Emitter` พร้อม `aria-current="page"`
- การกดแท็บ = โหลดฟอร์มของโหมดนั้นด้วยค่าเริ่มต้น (ไม่คงค่าที่กรอกในโหมดก่อน)
- hidden input `mode`
- ฟอร์มวน `fields` ตามโหมด (โครงเดิมรองรับอยู่แล้ว)
- ปุ่ม Calculate ใต้ช่องกรอกใน panel เดียวกัน
- แสดงชื่อโหมดในผลลัพธ์และ error banner
- ตารางผล 7 แถวเหมือนเดิม; Fixed แสดง `VE = 0.000 V` เมื่อ active
- **IC แสดงเป็น mA เสมอ** (3 ตำแหน่ง); IB/IE ใช้ µA เมื่อ < 1 mA ตามเดิม
- details block: Divider แสดง VTH/RTH; โหมดอื่นแสดงคำอธิบายสั้นของโหมด
- SVG 3 แบบด้วย `{% if mode == ... %}`; ป้ายผูกกับ `form.*` เท่านั้น (ไม่มีค่า calculated)
- Hint: `RB = 1 MΩ → enter 1000 (kΩ)`

### 7.4 `static/style.css`

- เพิ่มสไตล์แท็บ (`.mode-tabs`, `.mode-tab`, `.mode-tab[aria-current="page"]`)
- ใช้คลาส SVG เดิม (`.wire`, `.res`, `.device`, `.arrow`, `.gnd`) กับรูปใหม่

### 7.5 `docs/validation.md`

เพิ่ม:

1. ตาราง A1–A5: อินพุต, ค่าคาดหมาย (คำนวณมือก่อนรัน), ผลจริง, หน่วย, วิธีตรวจ, สถานะ, หลักฐาน
2. ค่าอ้างอิงอิสระของ Fixed (A2) และ Emitter (A3/A4) พร้อมสมการทีละขั้น
3. เหตุผลของทิศทาง A3 → A4: RE เพิ่มขึ้น → ตัวส่วน `RB + (β+1)RE` โต → IB ลด → IC ลด
   ขณะที่ VE = IE·RE เพิ่มขึ้นมากกว่าที่ VC จะเพิ่ม ดังนั้น **VCE ลดลง**
4. ระบุวิธีจริง: **OpenCode Browser** (Playwright MCP = NOT RUN เพราะไม่มี Node.js/npx)

### 7.6 `README.md`

- เปลี่ยนชื่อ/ขอบเขตเป็น Lab 03
- วิธีรัน + URL
- GitHub URL
- Commit SHA (เติมหลังผู้ใช้ commit)
- ระบุส่วนที่ AI ช่วยและส่วนที่นักศึกษาตรวจ
- คำสั่งรัน tests เดิม

### 7.7 MCP / Playwright

- เครื่องนี้ไม่มี `node`/`npx` → **Playwright MCP = NOT RUN** พร้อมเหตุผล
- ใช้ **OpenCode Browser Tool** เป็นวิธีจริง และบันทึกในตาราง A1–A5
- ไม่ใส่ `opencode.json` ที่เรียก `npx` เพราะจะทำให้ MCP เริ่มไม่สำเร็จ
  (ถ้าผู้ใช้ต้องการติดตั้ง Node.js เพิ่มภายหลัง ค่อยเพิ่ม config ตามใบงาน)

---

## 8. โครงสร้างไฟล์ที่เปลี่ยน

```
dc_bias.py                    ← เพิ่ม 2 ฟังก์ชัน + dict contract + region ≤ 0.2
app.py                        ← mode dispatch + conditional fields + finite check
templates/index.html          ← แท็บโหมด + 3 SVG + แสดงชื่อโหมด
static/style.css              ← สไตล์แท็บ
docs/validation.md            ← A1–A5 + ค่าอ้างอิงอิสระ + หลักฐาน
README.md                     ← Lab 03 + วิธีรัน + URL + SHA + AI-assisted
```

ไม่แตะ `requirements.txt` (ไม่เพิ่ม dependency)

---

## 9. แผนตรวจสอบ

1. tests เดิม 13 ตัวต้องผ่านหลังแก้
2. คำนวณมือ A1–A5 ก่อนรัน แล้วบันทึกค่าคาดหมาย
3. เปิด Flask + ตรวจผ่าน OpenCode Browser:
   - A1 Divider → ต้องได้ `IC 1.230 mA`, `VCE 8.052 V`
   - A2 Fixed RB=1000 kΩ → ไม่มีช่อง RE
   - A3 Emitter RB=1000, RE=1 → ใช้ RE
   - A4 Emitter RE=2 → IC ลด, VCE เพิ่ม
   - A5 Fixed RB=0 → error ชัดเจน ไม่มีผลค้าง
4. เก็บหลักฐานอย่างน้อย 1 กรณี (ข้อความผล/ภาพหน้าจอ)

## 10. ความเสี่ยง

| ความเสี่ยง | การลด |
|---|---|
| Divider เปลี่ยนผล | เก็บ 13 tests + เทียบ A1 กับ baseline ที่บันทึกไว้ |
| ผลค้างหลัง error | ทุก error path ตั้ง `result=None` |
| ค่า `inf`/`nan` หลุด | `math.isfinite` ในโมดูล |
| SVG Fixed/Emitter ผิดสัดส่วน | ใช้ layout เดียวกับ Divider และตรวจด้วยตา |
| Playwright MCP ใช้ไม่ได้ | ใช้ OpenCode Browser + บันทึก NOT RUN ตามใบงาน |

## 11. สิ่งที่เหลือให้ผู้สร้างตัดสิน

- ตำแหน่ง/ขนาดของป้ายใน SVG ใหม่ (ให้อ่านง่าย ไม่ทับเส้น)
- ข้อความ warning ที่กระชับขึ้น (ความหมายเดิม)
- การจัดลำดับช่องในฟอร์มให้ตรงกับลำดับการอ่านวงจร
