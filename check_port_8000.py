# check_port_8000.py
# ========================
# สคริปต์ตรวจสอบอย่างเดียว (ไม่ฆ่าโปรเซสใดๆ ให้อัตโนมัติ ปลอดภัย 100%) รันด้วยคำสั่ง:
#     python check_port_8000.py
#
# จากผลที่ส่งมา พบสาเหตุที่แท้จริงแล้วครับ — ตอนรัน python main.py ล่าสุด เซิร์ฟเวอร์
# "ไม่ได้เปิดขึ้นมาจริง" เลย ทั้ง 2 ช่องทาง (IPv4 และ IPv6) เพราะขึ้น error:
#   [Errno 10048] error while attempting to bind on address ('0.0.0.0', 8000):
#   only one usage of each socket address (protocol/network address/port)
#   is normally permitted
# แล้วก็ "Application shutdown complete" ทันที — แปลว่าพอร์ต 8000 ถูกโปรเซสอื่นที่ยัง
# ค้างทำงานอยู่ในเครื่องยึดไว้ตั้งแต่ก่อนหน้านี้แล้ว (น่าจะเป็น python main.py ตัวเก่าที่
# เคยเปิดไว้ แล้วปิดหน้าต่าง cmd ด้วยปุ่ม X แทนการกด Ctrl+C ทำให้โปรเซสค้างอยู่เบื้องหลัง
# ไม่ได้ถูกปิดจริง) เวลาเปิดหน้าเว็บแชท เบราว์เซอร์เลยไปคุยกับโปรเซสเก่าที่ค้างอยู่ตัวนั้น
# (ซึ่งอาจค้าง/ไม่ตอบสนองด้วยเหตุผลอื่นอีกที) แทนที่จะเป็นตัวที่เพิ่งสั่งรันใหม่ นี่คือสาเหตุที่
# "ตอบอะไรไม่ได้เลย" ตามที่พบ
#
# สคริปต์นี้จะหาว่าโปรเซสไหนกำลังยึดพอร์ต 8000 อยู่ (แค่ดู ไม่ฆ่า) แล้วบอกคำสั่งที่ต้องรันเอง
# เพื่อปิดโปรเซสนั้น (ให้ผู้ใช้เป็นคนตัดสินใจรันเองหลังเห็นชื่อโปรแกรมแล้วว่าใช่ python จริงๆ)

import subprocess
import re

print("=" * 70)
print("ตรวจสอบว่าพอร์ต 8000 ถูกโปรเซสอะไรยึดอยู่")
print("=" * 70)

try:
    result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, timeout=15)
except Exception as e:
    print(f"[ผิดพลาด] รันคำสั่ง netstat ไม่สำเร็จ: {e}")
    raise SystemExit(1)

lines = [l for l in result.stdout.splitlines() if ":8000" in l]
if not lines:
    print("ไม่พบโปรเซสใดยึดพอร์ต 8000 อยู่ตอนนี้ — พอร์ตว่างแล้ว")
    print("ลองรัน python main.py ใหม่ได้เลย ถ้ายัง error พอร์ตซ้ำอีก ให้รันสคริปต์นี้ซ้ำอีกครั้ง")
    raise SystemExit(0)

print("พบรายการที่เกี่ยวข้องกับพอร์ต 8000 ดังนี้:")
print()
pids = set()
for l in lines:
    print(" ", l.strip())
    parts = l.split()
    if parts and parts[-1].isdigit():
        pids.add(parts[-1])

if not pids:
    print()
    print("หา PID (หมายเลขโปรเซส) จากผลลัพธ์ไม่ได้ ลองดูคอลัมน์ขวาสุดของแต่ละบรรทัดด้านบนเอง")
    raise SystemExit(0)

print()
print("=" * 70)
print("รายละเอียดโปรเซสที่ยึดพอร์ตอยู่ (PID: ชื่อโปรแกรม)")
print("=" * 70)
for pid in sorted(pids):
    try:
        tl = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True, timeout=15)
        info_lines = [l for l in tl.stdout.splitlines() if pid in l]
        name = info_lines[0].split()[0] if info_lines else "(หาไม่เจอ)"
    except Exception:
        name = "(หาไม่เจอ)"
    print(f"PID {pid} -> {name}")

print()
print("=" * 70)
print("วิธีแก้")
print("=" * 70)
print("ถ้าชื่อโปรแกรมด้านบนคือ python.exe (โปรเซส python main.py ตัวเก่าที่ค้างอยู่) ให้ปิดด้วย")
print("คำสั่งนี้ (แทน <PID> ด้วยหมายเลขที่เห็นด้านบน เช่น taskkill /PID 12345 /F):")
print()
for pid in sorted(pids):
    print(f"     taskkill /PID {pid} /F")
print()
print("ปิดให้ครบทุก PID ที่เห็นด้านบน แล้วรันสคริปต์นี้ซ้ำอีกครั้งเพื่อเช็คว่าพอร์ตว่างแล้วจริงๆ")
print("จากนั้นค่อยรัน python main.py ใหม่")
print()
print("(ถ้าไม่มั่นใจว่าโปรแกรมที่เจอคือ python.exe จริงหรือไม่ อย่าเพิ่งสั่งปิด — ")
print(" ส่งผลลัพธ์ด้านบนกลับมาให้ดูก่อนได้เลย)")
