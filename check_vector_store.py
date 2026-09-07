# check_vector_store.py
# ========================
# สคริปต์ตรวจสอบ (ไม่แก้ไข/ไม่ลบอะไรทั้งสิ้น ปลอดภัย 100% รันได้เรื่อยๆ) รันในโฟลเดอร์
# เดียวกับ main.py ด้วยคำสั่ง:
#     python check_vector_store.py
#
# ใช้ตรวจหาสาเหตุที่เป็นไปได้มากที่สุดอย่างหนึ่งของอาการ "AI ค้นข้อมูลมาตอบไม่ได้เลย"
# (ทั้งที่เมื่อก่อนเคยตอบได้) นั่นคือ: ไฟล์ vector_store/faiss_index.index ที่มีอยู่ในเครื่อง
# ตอนนี้ อาจถูกสร้างไว้ตั้งแต่ตอนที่ main.py ยังใช้โมเดล embedding รุ่นเก่า
# (paraphrase-multilingual-MiniLM-L12-v2 มิติเวกเตอร์ = 384) แต่ main.py เวอร์ชันปัจจุบัน
# เปลี่ยนมาใช้โมเดลใหม่แล้ว (intfloat/multilingual-e5-base มิติเวกเตอร์ = 768 — ดูคอมเมนต์
# ในไฟล์ main.py เองบรรทัดแถวๆ EMBEDDING_MODEL ที่อธิบายเหตุผลไว้แล้ว)
#
# ถ้าไม่ได้ลบ index เก่าทิ้งแล้วอัปโหลดเอกสารใหม่หลังเปลี่ยนโมเดล มิติเวกเตอร์ของ index เก่า
# (384) กับมิติที่โมเดลใหม่คำนวณตอนค้นหาคำถาม (768) จะไม่ตรงกัน ทำให้ทุกครั้งที่มีคนถามคำถาม
# ระบบจะพังทันที (error ทันทีตอนค้นหา) เท่ากับ "ตอบอะไรไม่ได้เลยทั้งระบบ" ตรงกับอาการที่พบ
#
# สคริปต์นี้จะเปิดไฟล์ index ขึ้นมาดูอย่างเดียว (ไม่แก้ไข) แล้วเทียบมิติกับโมเดลที่ main.py
# กำหนดไว้ตอนนี้ให้ดูว่าตรงกันหรือไม่ พร้อมบอกวิธีแก้ถ้าไม่ตรงกัน

import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
VS_DIR = BASE_DIR / "vector_store"
FAISS_PATH = str(VS_DIR / "faiss_index")
IDX_FILE = FAISS_PATH + ".index"
META_FILE = FAISS_PATH + ".meta.npy"

print("=" * 70)
print("ตรวจสอบ vector store")
print("=" * 70)

# 1) อ่านค่า EMBEDDING_MODEL ปัจจุบันจาก main.py โดยตรง กันกรณีสคริปต์นี้กับ main.py
#    ไม่ตรงเวอร์ชันกัน (อ่านจากไฟล์จริงที่จะรัน ไม่ใช้ค่า hardcode)
main_py = BASE_DIR / "main.py"
current_model = None
if main_py.exists():
    text = main_py.read_text(encoding="utf-8")
    m = re.search(r'EMBEDDING_MODEL\s*=\s*"([^"]+)"', text)
    if m:
        current_model = m.group(1)
        print(f"โมเดล embedding ที่ main.py ใช้อยู่ตอนนี้: {current_model}")
    else:
        print("[WARN] หาบรรทัด EMBEDDING_MODEL ใน main.py ไม่เจอ (รูปแบบอาจเปลี่ยนไป) ข้ามการเทียบมิติ")
else:
    print("[WARN] ไม่พบไฟล์ main.py ในโฟลเดอร์เดียวกับสคริปต์นี้ — วางสคริปต์นี้ไว้ในโฟลเดอร์เดียวกับ main.py")

# 2) เช็คว่ามีไฟล์ index อยู่จริงไหม
if not Path(IDX_FILE).exists() or not Path(META_FILE).exists():
    print()
    print("ยังไม่พบไฟล์ vector store เลย (vector_store/faiss_index.index / .meta.npy)")
    print("แปลว่าระบบยังไม่เคยมีเอกสารถูกอัปโหลด/index เข้ามาเลย หรือเพิ่งถูกลบไปหมาดๆ")
    print("วิธีแก้: เข้าหน้า upload.html แล้วอัปโหลดไฟล์คู่มือทั้งหมด (ระบุปีการศึกษาให้ครบ)")
    print("ก่อนถึงจะมีข้อมูลให้ AI ค้นหาได้")
    sys.exit(0)

# 3) เปิด index ขึ้นมาดูมิติจริง (ไม่แก้ไขอะไร)
try:
    import faiss
except ImportError:
    print()
    print("[ผิดพลาด] ไม่พบไลบรารี faiss ในเครื่องนี้ (pip install faiss-cpu)")
    print("ถ้า main.py รันได้ปกติ แปลว่าไลบรารีนี้มีอยู่แล้วในสภาพแวดล้อมที่ใช้รันจริง")
    print("ลองรันสคริปต์นี้ด้วย python ตัวเดียวกับที่ใช้รัน main.py (เช่น python -m venv ตัวเดิม)")
    sys.exit(1)

try:
    idx = faiss.read_index(IDX_FILE)
except Exception as e:
    print()
    print(f"[ผิดพลาด] เปิดไฟล์ {IDX_FILE} ไม่สำเร็จ: {e}")
    print("ไฟล์อาจเสียหาย — ถ้าไม่มีทางแก้อื่น อาจต้องลบไฟล์นี้ทิ้งแล้วอัปโหลดเอกสารใหม่ทั้งหมด")
    sys.exit(1)

print()
print(f"จำนวน chunk ที่ index ไว้ (ntotal): {idx.ntotal}")
print(f"มิติเวกเตอร์ของ index ปัจจุบัน (d) : {idx.d}")

if idx.ntotal == 0:
    print()
    print("index มีอยู่แต่ว่างเปล่า (0 chunks) — เหมือนยังไม่เคยอัปโหลดเอกสารสำเร็จเลย")
    print("วิธีแก้: เข้าหน้า upload.html แล้วอัปโหลดไฟล์คู่มือทั้งหมดใหม่")
    sys.exit(0)

# 4) เทียบกับมิติจริงของโมเดลที่ main.py กำหนดไว้ตอนนี้ (โหลดโมเดลจริงเพื่อความชัวร์ที่สุด
#    แทนการเดาจากชื่อโมเดล — ถ้าเครื่องนี้เคยรัน main.py ได้มาก่อน โมเดลนี้ต้องถูกดาวน์โหลด/
#    แคชไว้ในเครื่องแล้ว ขั้นตอนนี้จึงไม่ควรช้าหรือต้องต่อเน็ตใหม่)
expected_dim = None
if current_model:
    try:
        from sentence_transformers import SentenceTransformer
        print()
        print(f"กำลังโหลดโมเดล '{current_model}' เพื่อเช็คมิติจริง (ถ้าเคยรัน main.py มาก่อนจะเร็ว)...")
        embedder = SentenceTransformer(current_model)
        expected_dim = embedder.get_sentence_embedding_dimension()
        print(f"มิติเวกเตอร์ที่โมเดลนี้คำนวณได้จริง: {expected_dim}")
    except Exception as e:
        print(f"[WARN] โหลดโมเดลเพื่อเช็คมิติไม่สำเร็จ: {e}")
        print("ข้ามขั้นตอนเทียบมิติอัตโนมัติ — ดูผลสรุปด้านล่างแทน")

print()
print("=" * 70)
print("สรุปผล")
print("=" * 70)
if expected_dim is not None:
    if idx.d != expected_dim:
        print("*** พบสาเหตุแล้ว: มิติเวกเตอร์ของ index เก่า (%d) กับที่โมเดล embedding ปัจจุบัน "
              "คำนวณได้จริง (%d) ไม่ตรงกัน ***" % (idx.d, expected_dim))
        print()
        print("นี่คือสาเหตุที่ AI ค้นหา/ตอบคำถามอะไรไม่ได้เลยทั้งระบบ (error ทุกครั้งที่มีคนถาม)")
        print("เพราะ index ถูกสร้างไว้ตั้งแต่ก่อนเปลี่ยนโมเดล embedding แต่ยังไม่ได้ล้างแล้ว")
        print("อัปโหลดเอกสารใหม่ตามที่คอมเมนต์ในไฟล์ main.py (แถว EMBEDDING_MODEL) แนะนำไว้")
        print()
        print("วิธีแก้ (ทำตามลำดับ):")
        print("1) ปิดเซิร์ฟเวอร์ (Ctrl+C ในหน้าต่างที่รัน python main.py)")
        print(f"2) ลบไฟล์ 2 ไฟล์นี้ทิ้ง:")
        print(f"     {IDX_FILE}")
        print(f"     {META_FILE}")
        print("3) เปิดเซิร์ฟเวอร์ใหม่ด้วย python main.py (จะสร้าง index ว่างเปล่าให้อัตโนมัติ)")
        print("4) เข้าหน้า upload.html แล้วอัปโหลดไฟล์คู่มือทุกไฟล์ซ้ำใหม่ทั้งหมด")
        print("   (ระบุปีการศึกษาให้ครบเหมือนเดิม) แล้วลองถามคำถามในหน้าแชทอีกครั้ง")
    else:
        print(f"มิติเวกเตอร์ตรงกัน ({idx.d}) — vector store น่าจะ 'ไม่ใช่' สาเหตุของปัญหานี้")
        print()
        print("ควรตรวจสาเหตุอื่นต่อ โดยเฉพาะฝั่ง Ollama (โปรแกรมรันโมเดล AI ในเครื่อง):")
        print("- เปิดโปรแกรม Ollama อยู่หรือไม่")
        print("- รันคำสั่ง: ollama list   (ต้องเห็นชื่อโมเดล gemma3:4b อยู่ในรายการ)")
        print("  ถ้าไม่เจอ ให้รัน: ollama pull gemma3:4b")
        print("- ลองดูข้อความในหน้าต่าง cmd ที่รัน python main.py ตอนเปิดเซิร์ฟเวอร์ครั้งล่าสุด")
        print("  จะมีบรรทัด 'Ollama    : ...' บอกสถานะไว้อยู่แล้วว่าเชื่อมต่อได้ไหม")
        print("- ลองพิมพ์คำถามในหน้าแชท 1 ครั้ง แล้วดูว่าในหน้าต่าง cmd ขึ้นข้อความ error อะไร")
        print("  ขึ้นมาบ้างไหม (ถ้ามี ช่วยคัดลอกข้อความนั้นมาให้ดูด้วยจะช่วยระบุสาเหตุที่แน่ชัดได้เร็วขึ้น)")
else:
    print("ไม่สามารถเทียบมิติอัตโนมัติได้ (ดูสาเหตุด้านบน) แต่ข้อมูลนี้ยังมีประโยชน์:")
    print(f"- index ปัจจุบันมีมิติ {idx.d} และมี {idx.ntotal} chunks")
    print("- โมเดลที่ main.py กำหนดไว้ตอนนี้คือ intfloat/multilingual-e5-base ซึ่งควรมีมิติ 768")
    print(f"- ถ้า {idx.d} != 768 ให้ทำตามขั้นตอนล้าง+อัปโหลดใหม่ด้านบนได้เลย (ดูใน main.py")
    print("  คอมเมนต์แถว EMBEDDING_MODEL สำหรับขั้นตอนละเอียด)")
