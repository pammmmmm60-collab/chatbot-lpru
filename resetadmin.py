"""
reset_admin_password.py
------------------------
ใช้รีเซ็ตรหัสผ่าน (และ/หรืออีเมล) ของบัญชีแอดมิน กรณีลืมรหัสผ่าน

ระบบนี้อนุญาตให้มีผู้ดูแลระบบได้เพียง "บัญชีเดียว" เท่านั้น (ดู main.py) จึงไม่มีปุ่ม
"ลืมรหัสผ่าน" บนหน้าเว็บและไม่มีการส่งอีเมลกู้คืนใดๆ — การรีเซ็ตทำได้เฉพาะผู้ที่มีสิทธิ์
เข้าถึงไฟล์บนเครื่อง/เซิร์ฟเวอร์ที่รันระบบอยู่เท่านั้น (เจตนาเพื่อความปลอดภัย: ผู้ที่ไม่มี
สิทธิ์เข้าเซิร์ฟเวอร์จะรีเซ็ตรหัสผ่านแอดมินไม่ได้)

วิธีใช้:
    python reset_admin_password.py <รหัสผ่านใหม่>
    python reset_admin_password.py <รหัสผ่านใหม่> --email newadmin@gmail.com

ตัวอย่าง:
    python reset_admin_password.py "MyN3wP@ssw0rd"

หลังรันเสร็จ ต้อง "restart เซิร์ฟเวอร์ (main.py)" ใหม่ 1 ครั้ง เพื่อให้ session แอดมินเก่า
ทั้งหมดถูกล้าง (เนื่องจาก session เก็บอยู่ใน memory ของโปรเซสเดิม)
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
ADMIN_CONFIG_FILE = BASE_DIR / "admin_config.json"


def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description="รีเซ็ตรหัสผ่านแอดมิน (กรณีลืมรหัสผ่าน)")
    parser.add_argument("new_password", help="รหัสผ่านใหม่ที่ต้องการตั้ง")
    parser.add_argument("--email", default=None,
                         help="เปลี่ยนอีเมลแอดมินด้วย (ไม่ระบุ = ใช้อีเมลเดิม/ค่าเริ่มต้น admin@gmail.com)")
    args = parser.parse_args()

    if len(args.new_password) < 6:
        print("รหัสผ่านใหม่ควรมีความยาวอย่างน้อย 6 ตัวอักษร")
        sys.exit(1)

    if ADMIN_CONFIG_FILE.exists():
        try:
            cfg = json.loads(ADMIN_CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            cfg = {}
    else:
        cfg = {}

    email = args.email or cfg.get("email") or "admin@gmail.com"
    cfg = {"email": email, "password_hash": _hash(args.new_password)}

    ADMIN_CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"ตั้งรหัสผ่านแอดมินใหม่เรียบร้อยแล้ว (อีเมล: {email})")
    print("กรุณา restart เซิร์ฟเวอร์ (main.py) เพื่อให้มีผล และล้าง session แอดมินเก่าทั้งหมด")


if __name__ == "__main__":
    main()