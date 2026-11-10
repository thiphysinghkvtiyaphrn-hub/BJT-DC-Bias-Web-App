# BJT DC Bias Web App

Flask Web Application สำหรับคำนวณ **DC Operating Point** ของวงจรขยาย BJT
Common-Emitter แบบ **Voltage-Divider Bias**

| | |
|---|---|
| รายวิชา | ENG29 2121 Computer Programming for Electrical Engineers |
| ภาคการศึกษา | 2/2569 |
| Lab | 02 — First DC Bias Web App |
| เจ้าของ repo | [@thiphysinghkvtiyaphrn-hub](https://github.com/thiphysinghkvtiyaphrn-hub) |
| สถานะ | 🚧 Scaffolding — รอ Design Approval ก่อน implement |

> **สถานะปัจจุบัน:** repo นี้ยังไม่มีโค้ดแอปพลิเคชัน
> มีเพียงโครงสร้าง โปรเจกต์ เอกสาร และการตั้งค่า Python Environment
> โค้ดจะถูกเพิ่มหลังผ่านขั้น Brainstorming → Design Approval → Plan Review
> ตาม workflow ของ Superpowers

---

## ขอบเขต (Scope)

**อยู่ในขอบเขต Lab 2**

- ฟอร์มรับค่า `VCC, R1, R2, RC, RE, β, VBE`
- คำนวณ `VB, VE, VC, VCE, IC` (แสดง `IB`, `IE` ด้วย) ด้วย Python backend
- แสดงหน่วยกำกับทุกค่า
- ตรวจสอบข้อมูลเข้า (validation) และเตือนเมื่ออยู่นอก Forward-Active Region
- Automated tests: engineering math + Flask HTTP route

**นอกขอบเขต (จะทำในสัปดาห์ถัดไป)**

- Fixed Bias / Emitter Bias templates (W3)
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
│   └── validation.md       # independent reference calculation
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

> ⚠️ ต้องเปิดผ่าน Local Web Server เท่านั้น
> **ห้าม** double-click เปิด `templates/index.html` ด้วย `file://`
> เพราะฟอร์มต้องส่ง HTTP Request ไปให้ Python คำนวณ

---

## การทดสอบ

```powershell
python -m unittest discover -s tests -v
```

---

## แบบจำลองและสมการ

Forward-Active Approximation (β คงที่, VBE คงที่)

```
VTH = VCC × R2 / (R1 + R2)
RTH = R1·R2 / (R1 + R2)
IB  = (VTH − VBE) / (RTH + (β+1)·RE)
IC  = β·IB
IE  = (β+1)·IB
VE  = IE·RE
VB  = VE + VBE
VC  = VCC − IC·RC
VCE = VC − VE
```

### ค่าอ้างอิงสำหรับตรวจสอบ

VCC = 12 V, R1 = 100 kΩ, R2 = 22 kΩ, RC = 2.2 kΩ, RE = 1 kΩ, β = 100, VBE = 0.70 V

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
| VCE | 8.05 V |
| Region | Forward Active |

---

## ข้อจำกัดของแบบจำลอง

- เป็น **DC Bias แบบ Forward-Active Approximation** ไม่ใช่ผลจาก ngspice
- ถ้า `VTH ≤ VBE` ทรานซิสเตอร์อาจอยู่ใน **Cutoff** — ผลที่คำนวณไม่ถูกต้อง
- ถ้า `VCE` ต่ำมาก (ใกล้ 0.2 V) ทรานซิสเตอร์อาจอยู่ใน **Saturation**
- ทั้งสองกรณี เว็บต้องแสดง **Warning** และไม่รายงานผลราวกับว่าแม่นยำ

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
