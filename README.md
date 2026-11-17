# BJT DC Bias Web App

Flask Web Application สำหรับคำนวณ **DC Operating Point** ของวงจรขยาย BJT
Common-Emitter ในโหมดไบอัสสามแบบ: **Voltage Divider Bias**, **Fixed Bias**
และ **Emitter Bias** (แหล่งจ่ายเดียว)

| | |
|---|---|
| รายวิชา | ENG29 2121 Computer Programming for Electrical Engineers |
| ภาคการศึกษา | 2/2569 |
| Lab | 02 — First DC Bias Web App → 03 — Three Bias Modes |
| เจ้าของ repo | [@thiphysinghkvtiyaphrn-hub](https://github.com/thiphysinghkvtiyaphrn-hub) |
| สถานะ | ✅ Implemented — 29 automated tests ผ่านทั้งหมด |

> **สถานะปัจจุบัน:** แอปพลิเคชันทำงานครบตามขอบเขต Lab 03
> (เลือกโหมดผ่านแท็บ → Python คำนวณตามโหมด → แสดงผล + region warning)
> ผ่านการทดสอบ 29 tests และตรวจสอบกับ[การคำนวณด้วยมือ](docs/validation.md)แล้ว
> โดยผลของ Voltage Divider ยังคงเหมือน Lab 02 ทุกค่า

---

## ขอบเขต (Scope)

**อยู่ในขอบเขต Lab 2–3**

- เลือกโหมดได้ 3 แบบผ่านแท็บ `Divider | Fixed | Emitter` (ไม่ใช้ JavaScript)
- ฟอร์มแสดงเฉพาะช่องที่โหมดนั้นใช้
  - Divider: `VCC, R1, R2, RC, RE, β, VBE`
  - Fixed: `VCC, RB, RC, β, VBE`
  - Emitter: `VCC, RB, RE, RC, β, VBE`
- คำนวณ `VB, VE, VC, VCE, IC` (แสดง `IB`, `IE` ด้วย) ด้วย Python backend
- แสดงหน่วยกำกับทุกค่า; `IC` เป็น mA เสมอ; `IB`/`IE` ใช้ µA เมื่อต่ำกว่า 1 mA
- ตรวจสอบข้อมูลเข้า (validation) และเตือนเมื่ออยู่นอก Forward-Active Region
- Automated tests: engineering math + Flask HTTP route (28 tests)

**นอกขอบเขต (จะทำในสัปดาห์ถัดไป)**

- SPICE / ngspice, DC Load Line (W4)
- AC small-signal, Gain, Bode Plot (W5)
- Transient, Signal Generator (W6)
- Interactive schematic, DC/AC overlay (W7)
- FET (W9–10)

---

## โครงสร้างโปรเจกต์

```
BJT DC Bias Web App/
├── app.py                  # Flask application & HTTP routes
├── dc_bias.py              # engineering calculations (ไม่รู้จัก HTML/HTTP)
├── templates/
│   └── index.html          # input form + DC results (Jinja)
├── static/
│   └── style.css           # responsive layout
├── tests/
│   ├── test_dc_bias.py     # unit tests for engineering logic
│   └── test_web.py         # Flask HTTP route tests
├── docs/
│   ├── validation.md       # independent reference calculation + A1–A5
│   └── evidence/           # ภาพหน้าจอผลตรวจ A1–A5 (OpenCode Browser)
├── requirements.txt
├── AGENTS.md               # conventions สำหรับ AI coding agent
├── .gitignore
└── README.md
```

---

## สิ่งที่ต้องมีในเครื่อง

| ซอฟต์แวร์ | เวอร์ชันที่ทดสอบแล้ว |
|---|---|
| Python | 3.15.2 (ใช้ได้ตั้งแต่ 3.9) |
| Git | 2.56.0 |
| GitHub Desktop | 3.6.10 (ใช้ commit/push) |

---

## การติดตั้ง

```powershell
# 1. clone (หรือเปิดผ่าน GitHub Desktop)
git clone https://github.com/thiphysinghkvtiyaphrn-hub/BJT-DC-Bias-Web-App.git
cd "BJT DC Bias Web App"

# 2. สร้าง virtual environment
python -m venv .venv

# 3. เปิดใช้งาน (Windows PowerShell)
.venv\Scripts\Activate.ps1
# macOS / Linux: source .venv/bin/activate

# 4. ติดตั้ง dependencies
python -m pip install -r requirements.txt
```

> `.venv/` ถูก ignore ไว้แล้วใน `.gitignore` — จะไม่ถูก commit

---

## การรัน

```powershell
python -m flask --app app run --debug
```

เปิดเบราว์เซอร์ที่ <http://127.0.0.1:5000/>

เลือกโหมดได้จากแท็บหรือ URL โดยตรง:

- <http://127.0.0.1:5000/?mode=divider> — Voltage Divider Bias
- <http://127.0.0.1:5000/?mode=fixed> — Fixed Bias
- <http://127.0.0.1:5000/?mode=emitter> — Emitter Bias

> ⚠️ ต้องเปิดผ่าน Local Web Server เท่านั้น
> **ห้าม** double-click เปิด `templates/index.html` ด้วย `file://`
> เพราะฟอร์มต้องส่ง HTTP Request ไปให้ Python คำนวณ

---

## การทดสอบ

```powershell
python -m unittest discover -s tests -v
```

ผลที่คาดหวัง: `Ran 29 tests ... OK`
(engineering math 13 tests + Flask HTTP 16 tests)

รายละเอียดการตรวจสอบค่ากับการคำนวณด้วยมืออยู่ใน [`docs/validation.md`](docs/validation.md)

---

## แบบจำลองและสมการ

Forward-Active Approximation (β คงที่, VBE คงที่) — เลือกสมการกระแสเบสตามโหมด

```
Fixed Bias:
    IB = (VCC − VBE) / RB

Emitter Bias (แหล่งจ่ายเดียว):
    IB = (VCC − VBE) / [RB + (β+1)·RE]

Voltage Divider Bias:
    VTH = VCC × R2 / (R1 + R2)
    RTH = R1·R2 / (R1 + R2)
    IB  = (VTH − VBE) / (RTH + (β+1)·RE)

ใช้ร่วมกันทุกโหมด:
    IC  = β·IB
    IE  = (β+1)·IB
    VE  = IE·RE            (Fixed Bias: VE = 0)
    VB  = VE + VBE
    VC  = VCC − IC·RC
    VCE = VC − VE
```

### ค่าอ้างอิงสำหรับตรวจสอบ

ทุกโหมดใช้ `VCC = 12 V`, `RC = 2.2 kΩ`, `β = 100`, `VBE = 0.70 V`

| โหมด | อินพุตเพิ่มเติม | IB | IC | VCE |
|---|---|---|---|---|
| Divider | R1 = 100 kΩ, R2 = 22 kΩ, RE = 1 kΩ | 12.30 µA | 1.230 mA | 8.052 V |
| Fixed | RB = 1 MΩ (= 1000 kΩ) | 11.30 µA | 1.130 mA | 9.514 V |
| Emitter | RB = 1 MΩ, RE = 1 kΩ | 10.26 µA | 1.026 mA | 8.705 V |
| Emitter | RB = 1 MΩ, RE = 2 kΩ | 9.40 µA | 0.940 mA | 8.033 V |

Voltage Divider แสดงรายละเอียดครบทุกปริมาณ:

| ปริมาณ | ค่า |
|---|---|
| VTH | 2.164 V |
| RTH | 18.03 kΩ |
| IB | 12.30 µA |
| IC | 1.230 mA |
| IE | 1.242 mA |
| VE | 1.242 V |
| VB | 1.942 V |
| VC | 9.294 V |
| VCE | 8.052 V |
| Region | Forward Active |

---

## ข้อจำกัดของแบบจำลอง

- เป็น **DC Bias แบบ Forward-Active Approximation** ไม่ใช่ผลจาก ngspice
- ถ้า `IB ≤ 0` (เช่น `VTH ≤ VBE` ในโหมด Divider) ทรานซิสเตอร์อาจอยู่ใน **Cutoff**
- ถ้า `VCE ≤ 0.2 V` ทรานซิสเตอร์อาจอยู่ใน **Saturation**
- ทั้งสองกรณี เว็บต้องแสดง **Warning** และไม่รายงานผลราวกับว่าแม่นยำ
- ไม่มี AC / transient / Bode / DC load line / bypass capacitor ใน Lab นี้

---

## เอกสารและ Commit

| | |
|---|---|
| GitHub | <https://github.com/thiphysinghkvtiyaphrn-hub/BJT-DC-Bias-Web-App> |
| Commit SHA (Lab 03) | _เติมหลัง commit รอบสุดท้ายผ่าน GitHub Desktop_ |
| หลักฐานผลตรวจ A1–A5 | [`docs/validation.md`](docs/validation.md) + [`docs/evidence/`](docs/evidence) |

### ส่วนที่ AI ช่วย และส่วนที่นักศึกษาตรวจ

- **AI ช่วย:** ร่างโค้ด `dc_bias.py`/`app.py`, เทมเพลต/SVG, ชุดทดสอบ และเอกสาร
- **นักศึกษาตรวจ:** ตรวจสมการกับใบงาน, ตรวจค่าอ้างอิงด้วยการคำนวณมือ,
  รัน A1–A5 ในเบราว์เซอร์จริง, ตรวจ diff และ commit เองผ่าน GitHub Desktop

---

## Workflow การ Commit (GitHub Desktop)

1. เปิด GitHub Desktop → เลือก repo นี้
2. แท็บ **Changes** → ไล่ดู diff ทีละไฟล์
3. ตรวจว่าไม่มี `.venv/`, `__pycache__/`, `.env` ถูกเลือก
4. ใส่ Summary → **Commit to main**
5. กด **Push origin**

---

## เอกสารอ้างอิง

- [Flask — Project Layout](https://flask.palletsprojects.com/en/stable/tutorial/layout/)
- [Flask — Quickstart](https://flask.palletsprojects.com/en/stable/quickstart/)
- [Flask — Testing](https://flask.palletsprojects.com/en/stable/testing/)
