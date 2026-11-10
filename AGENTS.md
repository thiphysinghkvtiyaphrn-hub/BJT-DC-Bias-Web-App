# AGENTS.md — Conventions for AI coding agents

โปรเจกต์: BJT DC Bias Web App (ENG29 2121 Lab 02)

## ขอบเขตที่ห้ามขยาย

ทำ **DC Bias ของ BJT Common-Emitter Voltage-Divider Bias เท่านั้น**
ห้ามเพิ่ม: AC analysis, Transient, Bode plot, Signal generator,
Fixed/Emitter bias templates, circuit editor, FET, SPICE solver

ถ้างานที่ขอต้องขยายขอบเขต ให้หยุดและถามก่อน

## การแบ่งความรับผิดชอบของไฟล์

| ไฟล์ | รับผิดชอบ | ห้าม |
|---|---|---|
| `dc_bias.py` | สมการวิศวกรรม, validation, region detection | import flask, อ่าน request, รู้จัก HTML |
| `app.py` | HTTP routes, แปลง/form parsing, เรียก `dc_bias` | ฝังสมการฟิสิกส์, hardcode ผลลัพธ์ |
| `templates/index.html` | แสดง form และผลลัพธ์ (Jinja) | คำนวณ, ฝังสมการ |
| `static/style.css` | การจัดหน้า | — |
| `tests/` | unittest | เรียก network |

## กติกาการเขียนโค้ด

1. **ห้าม hardcode ผลลัพธ์** — ค่าทุกค่าต้องมาจากการคำนวณจริง
2. **หน่วยต้องชัด** — ภายในใช้ SI (V, A, Ω) แปลงเป็น mA/µA/kΩ เฉพาะตอนแสดงผล
3. **แปลง kΩ → Ω** ก่อนคำนวณทุกครั้ง
4. ฟังก์ชันคำนวณคืนค่าเป็น dict หรือ dataclass ที่มีหน่วยในชื่อคีย์
5. ข้อผิดพลาดของผู้ใช้ → คืนข้อความที่อ่านรู้เรื่อง **ห้ามให้หน้าเว็บ 500**
6. ค่า `R ≤ 0`, `β ≤ 0`, `VCC ≤ 0`, non-numeric → validation error
7. `VTH ≤ VBE` หรือ `VCE` ต่ำใกล้ 0.2 V → คืน warning ห้ามอ้างว่าแม่นยำ

## การทดสอบ

- ใช้ `unittest` (stdlib) — ไม่เพิ่ม dependency ใหม่
- ทุกฟีเจอร์ใหม่ต้องมี test ที่เขียนก่อน implement
- รัน: `python -m unittest discover -s tests -v`
- ต้องมีอย่างน้อย 3 tests สำหรับ engineering math และ 1 test ผ่าน Flask test client

## Git

- commit ผ่าน **GitHub Desktop** เท่านั้น
- ห้าม commit `.venv/`, `__pycache__/`, `.env`, token, API key
- ทำงานบน branch `main` เท่านั้น (สำหรับ Lab 2)
- ข้อความ commit: `feat:`, `fix:`, `test:`, `docs:`, `chore:` ตามด้วยคำอธิบายสั้น
