import os, json, re, traceback, hashlib, threading, secrets, time, unicodedata, subprocess, shutil, sqlite3, io, asyncio  # โมดูลมาตรฐานที่ใช้ทั่วทั้งไฟล์
from contextlib import asynccontextmanager  # ใช้ประกาศ lifespan ของ FastAPI (โค้ดที่รันตอนเปิด/ปิดเซิร์ฟเวอร์)
from pathlib import Path  # จัดการ path ไฟล์แบบ object แทน string

from fastapi import FastAPI, File, UploadFile, Request, HTTPException, Depends, Form  # เครื่องมือหลักของ FastAPI
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse, HTMLResponse  # รูปแบบ response ต่างๆ ที่ endpoint คืนได้
from fastapi.staticfiles import StaticFiles  # ใช้เสิร์ฟไฟล์ static (css/js/รูป) ตรงๆ
from fastapi.middleware.cors import CORSMiddleware  # ควบคุมว่า origin ไหนเรียก API ได้บ้าง
from pydantic import BaseModel  # กำหนด schema ของข้อมูลที่ client ส่งเข้ามา (validate อัตโนมัติ)

import bcrypt  # ใช้แฮชรหัสผ่านแบบมีความปลอดภัยสูง (มี Salt ในตัว)

# ------------------------------------------------------------------ #
# CONFIG & DATABASE SETUP (SQLite)
# ------------------------------------------------------------------ #
BASE_DIR   = Path(__file__).parent  # โฟลเดอร์ที่ไฟล์นี้อยู่ ใช้เป็นจุดอ้างอิง path อื่นทั้งหมด
UPLOAD_DIR = BASE_DIR / "uploads"  # โฟลเดอร์เก็บไฟล์คู่มือดิบที่แอดมินอัปโหลด
VS_DIR     = BASE_DIR / "vector_store"  # โฟลเดอร์เก็บไฟล์ FAISS index + metadata
FAISS_PATH = str(VS_DIR / "faiss_index")  # ชื่อไฟล์ตั้งต้นของ FAISS (จะถูกต่อท้ายด้วย .index / .meta.npy)
DB_FILE    = BASE_DIR / "lpru_chatbot.db"  # ไฟล์ฐานข้อมูล SQLite หลักของระบบ
SUGGESTED_Q_FILE  = BASE_DIR / "suggested_questions.json"  # ไฟล์ JSON เก็บคำถามแนะนำ (ไม่ได้อยู่ใน SQLite)

UPLOAD_DIR.mkdir(exist_ok=True)  # สร้างโฟลเดอร์ uploads ถ้ายังไม่มี
VS_DIR.mkdir(exist_ok=True)  # สร้างโฟลเดอร์ vector_store ถ้ายังไม่มี
(BASE_DIR / "static_assets").mkdir(exist_ok=True)  # สร้างโฟลเดอร์ static_assets ถ้ายังไม่มี

# ------------------------------------------------------------------ #
# บัญชีแอดมินเริ่มต้น — อ่านจาก environment variable แทนการ hardcode ในซอร์สโค้ด
# (เดิม admin@gmail.com/123456 ฝังตรงในไฟล์ ใครอ่านซอร์สได้ก็รู้รหัสผ่านทันที)
# ค่าเริ่มต้นยังคงเป็น 123456 ตามที่ระบบเคยใช้ แต่ตอนนี้ตั้งผ่าน ADMIN_PASSWORD ได้
# (เปลี่ยนได้โดยไม่ต้องแก้ซอร์สโค้ด) — ควรตั้ง ADMIN_PASSWORD เป็นค่าอื่นเอง หรือใช้ฟีเจอร์
# "เปลี่ยนรหัสผ่าน" ในหน้า upload.html ทันทีหลังติดตั้งระบบจริง
# ------------------------------------------------------------------ #
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@gmail.com").strip().lower()  # อีเมลแอดมิน อ่านจาก env ถ้าไม่ตั้งใช้ค่า default
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "123456")  # รหัสผ่านแอดมินเริ่มต้น อ่านจาก env เช่นกัน

def init_db():  # สร้างตารางฐานข้อมูลทั้งหมด + บัญชีแอดมินเริ่มต้น (เรียกครั้งเดียวตอนสตาร์ทไฟล์)
    conn = sqlite3.connect(str(DB_FILE))  # เปิดการเชื่อมต่อฐานข้อมูล
    cursor = conn.cursor()  # เคอร์เซอร์ไว้รันคำสั่ง SQL
    # เพิ่มคอลัมน์ is_admin (0 = ผู้ใช้ทั่วไป, 1 = แอดมินระบบ)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
    """)  # ตารางผู้ใช้: username, รหัสผ่านที่แฮชแล้ว, และ flag ว่าเป็นแอดมินไหม
    cursor.execute("CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, user_type TEXT NOT NULL, identifier TEXT NOT NULL, role TEXT, year TEXT, expires_at REAL NOT NULL)")  # ตาราง session/token สำหรับ login
    cursor.execute("CREATE TABLE IF NOT EXISTS conversations (student_id TEXT NOT NULL, conv_id TEXT NOT NULL, title TEXT NOT NULL, created_at REAL NOT NULL, updated_at REAL NOT NULL, PRIMARY KEY (student_id, conv_id))")  # ตารางหัวข้อแชทของนักศึกษาแต่ละคน
    cursor.execute("CREATE TABLE IF NOT EXISTS chat_messages (student_id TEXT NOT NULL, conv_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, timestamp REAL NOT NULL)")  # ตารางข้อความแต่ละข้อความในแชท

    # สร้างบัญชีแอดมินเริ่มต้นอัตโนมัติถ้ายังไม่มีในระบบ (ใช้ ADMIN_EMAIL/ADMIN_PASSWORD ด้านบน
    # แทนค่าคงที่ในซอร์สโค้ด)
    cursor.execute("SELECT username FROM users WHERE username = ?", (ADMIN_EMAIL,))  # เช็คว่ามีบัญชีแอดมินนี้อยู่แล้วหรือยัง
    if not cursor.fetchone():  # ถ้ายังไม่มี
        default_hash = bcrypt.hashpw(ADMIN_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")  # แฮชรหัสผ่านเริ่มต้นด้วย bcrypt
        cursor.execute("INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)", (ADMIN_EMAIL, default_hash, 1))  # สร้างบัญชีแอดมิน

    conn.commit()  # บันทึกการเปลี่ยนแปลงลงไฟล์ .db
    conn.close()  # ปิดการเชื่อมต่อ

init_db()  # รันสร้างฐานข้อมูลทันที

EMBEDDING_MODEL = "intfloat/multilingual-e5-base"  # โมเดลแปลงข้อความรองรับภาษาไทย
OLLAMA_MODEL    = "gemma3:4b"                      # โมเดล LLM หลักสำหรับตอบคำถาม
OLLAMA_HOST     = "http://localhost:11434"  # ที่อยู่ของ Ollama server ที่รันอยู่ในเครื่องเดียวกัน
CHUNK_SIZE      = 800                              # ขนาดตัวอักษรต่อ chunk
CHUNK_OVERLAP   = 150                              # ระยะซ้อนทับกันระหว่าง chunk
TOP_K           = 8                                # จำนวน chunk สูงสุดที่ดึงมาใช้อ้างอิง
ALLOWED_EXT     = {".pdf", ".txt", ".docx", ".md"}  # นามสกุลไฟล์ที่อัปโหลดได้
OLLAMA_NUM_CTX  = 4096  # ขนาด context window ที่ส่งให้โมเดล LLM

SYSTEM_PROMPT = """คุณคือเจ้าหน้าที่ฝ่ายกิจการนักศึกษาที่ตอบคำถามนักศึกษาโดยใช้ข้อมูลอ้างอิงที่ให้มาเท่านั้น
- ตอบเหมือนเจ้าหน้าที่มืออาชีพที่รู้เรื่องนี้อยู่แล้วโดยตรง
- ตอบให้ตรงกับสิ่งที่ถูกถามจริงๆ ถ้าถามเรื่องขั้นตอน/วิธีการ ให้อธิบายขั้นตอนหรือวิธีการ
- ถ้าข้อมูลอ้างอิงไม่มีคำตอบ ให้ตอบตามตรงว่าไม่พบข้อมูลนี้ในระบบ และแนะนำให้ติดต่อฝ่ายกิจการนักศึกษาโดยตรง อย่าแต่งคำตอบขึ้นเอง
- ห้ามคำนวณ บวก ลบ รวม หรือประมาณตัวเลขใดๆ เอง ให้ใช้ตัวเลขที่ปรากฏตรงตัวในข้อมูลอ้างอิงเท่านั้น
- ตอบเป็นภาษาเดียวกับคำถามของผู้ใช้เท่านั้น และตอบให้กระชับ ชัดเจน เป็นทางการ ถ้าในอธิบายกิจกรรมนักศึกษาได้และนำคู่มือจากแหล่งนั้นมาประกอบ
- ห้ามขึ้นต้นคำตอบด้วยวลีอ้างถึงแหล่งข้อมูล เช่น "จากข้อมูลที่ให้มา" ให้ตอบเนื้อหาตรงๆ ทันที
"""  # ข้อความ system prompt กำหนดบุคลิก/กติกาการตอบของ LLM

def safe_filename(filename: str) -> str:  # ทำชื่อไฟล์ให้ปลอดภัยก่อนบันทึกลงดิสก์
    filename = os.path.basename(filename or "")  # ตัด path ทิ้ง เอาแค่ชื่อไฟล์
    filename = unicodedata.normalize("NFC", filename)  # ปรับ unicode ให้เป็นมาตรฐานเดียวกัน
    filename = filename.replace("\x00", "")  # ตัดอักขระ null (กัน path injection)
    filename = re.sub(r'[\\/:*?"<>|\r\n\t]', "_", filename)  # แทนอักขระต้องห้ามด้วย underscore
    return filename.strip(" .") or "unnamed_file"  # ตัดจุด/ช่องว่างหัวท้าย ถ้าว่างให้ใช้ชื่อ default

# ------------------------------------------------------------------ #
# VECTOR STORE (FAISS)
# ------------------------------------------------------------------ #
import faiss, numpy as np  # ไลบรารีค้นหาเวกเตอร์ (FAISS) และคำนวณเชิงตัวเลข
from sentence_transformers import SentenceTransformer  # ใช้แปลงข้อความเป็นเวกเตอร์

class VectorStore:  # คลาสจัดการฐานข้อมูลเวกเตอร์ทั้งหมดของระบบ
    def __init__(self):  # ตอนสร้าง instance ให้โหลดโมเดลและ index ทันที
        print(f"[VectorStore] โหลด embedding model: {EMBEDDING_MODEL}")  # log แจ้งว่ากำลังโหลดโมเดล
        self.embedder  = SentenceTransformer(EMBEDDING_MODEL)  # โหลดโมเดล embedding
        self.dimension = self.embedder.get_sentence_embedding_dimension()  # ขนาดมิติของเวกเตอร์ที่โมเดลนี้สร้าง
        self.index: faiss.Index | None = None  # ตัวแปรเก็บ FAISS index (ยังไม่สร้าง)
        self.metadata: list[dict] = []  # เก็บข้อมูลประกอบของแต่ละ chunk (text, source, year)
        self._lock = threading.Lock()  # ล็อกกันหลาย thread เขียน index พร้อมกัน
        self._load_or_create()  # โหลด index เดิมจากดิสก์ หรือสร้างใหม่ถ้ายังไม่มี

    def _load_or_create(self):  # โหลด FAISS index+metadata จากไฟล์ หรือสร้างเปล่าใหม่
        idx_f, meta_f = FAISS_PATH + ".index", FAISS_PATH + ".meta.npy"  # ชื่อไฟล์ index และ metadata
        if os.path.exists(idx_f) and os.path.exists(meta_f):  # ถ้ามีไฟล์เดิมอยู่แล้ว
            try:
                self.index = faiss.read_index(idx_f)  # โหลด index จากดิสก์
                self.metadata = np.load(meta_f, allow_pickle=True).tolist()  # โหลด metadata จากดิสก์
                print(f"[VectorStore] โหลดสำเร็จ {len(self.metadata)} chunks")  # log จำนวน chunk ที่โหลดได้
            except Exception as e:
                self.index = faiss.IndexFlatIP(self.dimension)  # ถ้าโหลดพัง ให้สร้าง index เปล่าแทน
                self.metadata = []  # เคลียร์ metadata ให้ว่างคู่กัน
        else:
            self.index = faiss.IndexFlatIP(self.dimension)  # ไม่เคยมีไฟล์มาก่อน สร้าง index เปล่า
            self.metadata = []  # metadata เริ่มต้นว่าง

    def _embed(self, texts, is_query: bool = False):  # แปลงข้อความหลายชิ้นเป็นเวกเตอร์
        prefix = "query: " if is_query else "passage: "  # โมเดล e5 ต้องการ prefix แยกคำถาม/เนื้อหา
        v = self.embedder.encode([prefix + t for t in texts], convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False)  # เข้ารหัสเป็นเวกเตอร์ normalize แล้ว
        return v.astype("float32")  # แปลงชนิดข้อมูลให้ตรงกับที่ FAISS ต้องการ

    def _save(self):  # บันทึก index + metadata ลงดิสก์
        faiss.write_index(self.index, FAISS_PATH + ".index")  # เขียนไฟล์ index
        np.save(FAISS_PATH + ".meta.npy", np.array(self.metadata, dtype=object))  # เขียนไฟล์ metadata

    def search(self, query: str, top_k: int = TOP_K) -> list[dict]:  # ค้นหา chunk ที่ใกล้เคียงคำถามที่สุด
        with self._lock:  # กันชนกับ thread อื่นที่กำลังแก้ index
            if self.index.ntotal == 0: return []  # ยังไม่มีข้อมูลใน index เลย คืนค่าว่าง
            qv = self._embed([query], is_query=True)  # แปลงคำถามเป็นเวกเตอร์
            scores, indices = self.index.search(qv, min(top_k, self.index.ntotal))  # ค้นหาเวกเตอร์ที่ใกล้เคียงที่สุด top_k อัน
            results = []  # เก็บผลลัพธ์
            for score, idx in zip(scores[0], indices[0]):  # วนดูแต่ละผลลัพธ์
                if idx == -1: continue  # -1 หมายถึงไม่พบ ข้ามไป
                item = dict(self.metadata[idx])  # คัดลอก metadata ของ chunk นั้น
                item["score"] = float(score)  # แนบคะแนนความคล้ายเข้าไปด้วย
                results.append(item)  # เพิ่มเข้าลิสต์ผลลัพธ์
            return results  # คืนรายการ chunk ที่พบ

    def stats(self) -> dict:  # สรุปสถิติภาพรวมของ vector store
        sources = sorted(set(m["source"] for m in self.metadata))  # รายชื่อไฟล์เอกสารทั้งหมดที่ไม่ซ้ำ
        return {"total_chunks": len(self.metadata), "total_documents": len(sources), "sources": sources}  # จำนวน chunk/เอกสารทั้งหมด

    def available_years(self) -> set[str]:  # รายชื่อรุ่น/ปีการศึกษาที่มีเอกสารรองรับอยู่
        return {m["year"] for m in self.metadata if m.get("year")}  # ดึง year ที่ไม่ว่างจาก metadata ทั้งหมด

    def delete_by_source(self, source: str) -> int:  # ลบ chunk ทั้งหมดที่มาจากไฟล์เอกสารที่ระบุ
        with self._lock:  # ล็อกกันชนกับการค้นหา/แก้ไขพร้อมกัน
            keep = [dict(m) for m in self.metadata if m["source"] != source]  # เก็บเฉพาะ chunk ที่ไม่ใช่ของไฟล์นี้
            removed = len(self.metadata) - len(keep)  # นับจำนวน chunk ที่จะถูกลบ
            if removed == 0: return 0  # ไม่พบ chunk ของไฟล์นี้เลย ไม่ต้องทำอะไรต่อ
        new_index = faiss.IndexFlatIP(self.dimension)  # สร้าง index ใหม่เปล่าๆ
        if keep:  # ถ้ายังมี chunk อื่นเหลืออยู่
            vectors = self._embed([m["text"] for m in keep], is_query=False)  # embed ใหม่ทั้งหมดที่เหลือ
            new_index.add(vectors)  # เติมเวกเตอร์เข้า index ใหม่
        with self._lock:  # ล็อกอีกครั้งตอนสลับ index จริง
            self.index, self.metadata = new_index, keep  # แทนที่ index/metadata เดิมด้วยชุดใหม่ที่ไม่มีไฟล์นี้แล้ว
            self._save()  # บันทึกลงดิสก์
        return removed  # คืนจำนวน chunk ที่ลบไป

    def replace_source(self, source: str, chunks: list[dict]) -> int:  # แทนที่ chunk เดิมของไฟล์นี้ด้วยชุดใหม่ (ใช้ตอนอัปโหลดซ้ำ)
        if not chunks: raise ValueError("ไม่พบ chunk")  # กันกรณีไม่มี chunk ให้เพิ่มเลย
        new_vectors = self._embed([c["text"] for c in chunks], is_query=False)  # embed chunk ชุดใหม่ล่วงหน้า
        with self._lock:  # ล็อกตลอดขั้นตอนสลับข้อมูล
            keep = [dict(m) for m in self.metadata if m["source"] != source]  # เก็บ chunk ของไฟล์อื่นไว้เหมือนเดิม
            new_index = faiss.IndexFlatIP(self.dimension)  # สร้าง index ใหม่
            if keep:  # ถ้ามี chunk ของไฟล์อื่นอยู่
                new_index.add(self._embed([m["text"] for m in keep], is_query=False))  # เติมของเดิมกลับเข้าไปก่อน
            new_index.add(new_vectors)  # เติม chunk ใหม่ของไฟล์นี้ต่อท้าย
            self.index, self.metadata = new_index, keep + [dict(c) for c in chunks]  # อัปเดต index/metadata ให้ตรงกัน
            self._save()  # บันทึกลงดิสก์
        return len(chunks)  # คืนจำนวน chunk ใหม่ที่เพิ่มเข้าไป

    def list_documents_detailed(self) -> list[dict]:  # สรุปรายชื่อเอกสารทั้งหมดพร้อมจำนวน chunk และปี
        counts, years = {}, {}  # ตัวนับจำนวน chunk และปีของแต่ละไฟล์
        for m in self.metadata:  # วนดู metadata ทุก chunk
            counts[m["source"]] = counts.get(m["source"], 0) + 1  # นับจำนวน chunk ต่อไฟล์
            if m.get("year"): years[m["source"]] = m["year"]  # จำปีของไฟล์นั้นไว้
        return [{"source": s, "chunk_count": c, "year": years.get(s, "")} for s, c in sorted(counts.items())]  # ประกอบเป็นลิสต์สรุป

    def set_year_for_source(self, source: str, year: str) -> int:  # แก้ปีของเอกสารที่มีอยู่แล้วโดยไม่ต้อง embed ใหม่
        with self._lock:  # ล็อกกันชน
            updated = 0  # นับจำนวน chunk ที่แก้ไป
            for m in self.metadata:  # วนหา chunk ของไฟล์นี้
                if m["source"] == source: m["year"], updated = year, updated + 1  # ตั้งปีใหม่ให้ chunk นั้น
            if updated: self._save()  # ถ้ามีการแก้จริง ค่อยบันทึกลงดิสก์
        return updated  # คืนจำนวน chunk ที่ถูกแก้

    def get_chunks_by_source(self, source: str) -> list[dict]:  # ดึงเนื้อหา chunk ดิบทั้งหมดของไฟล์หนึ่ง (ใช้ใน dev console)
        return [{"index": i, "text": m["text"]} for i, m in enumerate(self.metadata) if m["source"] == source]  # กรองเฉพาะของไฟล์ที่ต้องการ

vector_store = VectorStore()  # สร้าง instance เดียวใช้ร่วมกันทั้งแอป (โหลดโมเดล+index ตอนสตาร์ท)

# ------------------------------------------------------------------ #
# DOCUMENT PROCESSING & LOADERS
# ------------------------------------------------------------------ #
from pypdf import PdfReader  # ใช้อ่านไฟล์ PDF (สำรองกรณี pdftotext ใช้ไม่ได้)
import docx as _docx  # ใช้อ่านไฟล์ .docx
try: import openpyxl  # ใช้อ่านไฟล์ .xlsx ตอนนำเข้าคำถามแนะนำ
except ImportError: openpyxl = None  # ถ้าไม่ได้ติดตั้งไว้ ให้ตั้งเป็น None (endpoint ที่ใช้จะเช็คก่อน)

try: from langchain_text_splitters import RecursiveCharacterTextSplitter  # ตัวตัดข้อความเป็น chunk (แพ็กเกจใหม่)
except ImportError: from langchain.text_splitter import RecursiveCharacterTextSplitter  # เผื่อยังใช้แพ็กเกจเก่าอยู่

_PDFTOTEXT_BIN = shutil.which("pdftotext")  # หาตำแหน่งโปรแกรม pdftotext ในเครื่อง (ถ้ามีจะอ่าน PDF ได้แม่นกว่า)

def _read_pdf(path: str) -> str:  # อ่านข้อความจากไฟล์ PDF
    if _PDFTOTEXT_BIN:  # ถ้าเครื่องมี pdftotext ติดตั้งอยู่
        try:
            res = subprocess.run([_PDFTOTEXT_BIN, "-layout", "-enc", "UTF-8", path, "-"], capture_output=True, timeout=180, check=True)  # เรียกโปรแกรมแปลง PDF เป็นข้อความ
            text = res.stdout.decode("utf-8", errors="ignore")  # ถอดผลลัพธ์เป็น string
            if text.strip(): return text  # ถ้าได้ข้อความจริง ใช้ผลนี้เลย
        except Exception: pass  # ถ้าพัง ให้ไปใช้วิธีสำรองด้านล่างแทน
    return "\n".join(p.extract_text() or "" for p in PdfReader(path).pages)  # วิธีสำรอง: อ่านทีละหน้าด้วย pypdf

def _read_docx(path): return "\n".join(p.text for p in _docx.Document(path).paragraphs)  # อ่านข้อความทุกย่อหน้าในไฟล์ .docx
def _read_txt(path):  # อ่านไฟล์ข้อความธรรมดา/markdown
    with open(path, "r", encoding="utf-8", errors="ignore") as f: return f.read()  # เปิดอ่านทั้งไฟล์เป็น utf-8

_THAI_DIGIT_MAP = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")  # ตารางแปลงเลขไทยเป็นเลขอารบิก
def _normalize_thai_digits(text: str): return text.translate(_THAI_DIGIT_MAP)  # แปลงเลขไทยทั้งหมดในข้อความให้เป็นเลขอารบิก

_THAI_COMBINING_MARKS = "ัิีึืุู็่้๊๋์ํ๎"  # รายการวรรณยุกต์/สระลอยภาษาไทยที่ซ้ำกันได้บ่อยจากการแปลงไฟล์ผิดพลาด
_THAI_DUP_MARK_RE = re.compile("([" + _THAI_COMBINING_MARKS + r"])\1+")  # regex จับตัวอักษรกลุ่มนี้ที่ซ้ำติดกัน
def _fix_duplicated_thai_marks(text: str): return _THAI_DUP_MARK_RE.sub(r"\1", text)  # ยุบวรรณยุกต์ที่ซ้ำให้เหลือตัวเดียว

def load_text(path: str) -> str:  # อ่านไฟล์ตามนามสกุล แล้วทำความสะอาดข้อความก่อนนำไปใช้
    ext = os.path.splitext(path)[1].lower()  # ดูนามสกุลไฟล์ (ตัวพิมพ์เล็ก)
    if ext == ".pdf": text = _read_pdf(path)  # เลือกวิธีอ่านตามชนิดไฟล์: PDF
    elif ext == ".docx": text = _read_docx(path)  # Word
    elif ext in (".txt", ".md"): text = _read_txt(path)  # ข้อความ/markdown
    else: raise ValueError(f"ไม่รองรับไฟล์: {ext}")  # นามสกุลอื่นไม่รองรับ โยน error
    return _fix_duplicated_thai_marks(_normalize_thai_digits(unicodedata.normalize("NFC", text)))  # ปรับ unicode + เลขไทย + วรรณยุกต์ซ้ำให้เรียบร้อย

def process_file(path: str, year: str = "") -> list[dict]:  # แปลงไฟล์หนึ่งไฟล์ให้เป็นลิสต์ของ chunk พร้อม metadata
    source = os.path.basename(path)  # ใช้ชื่อไฟล์เป็น source อ้างอิง
    text = load_text(path)  # อ่าน+ทำความสะอาดข้อความในไฟล์
    if not text.strip(): raise ValueError("ไม่พบข้อความในไฟล์")  # ไฟล์ว่างเปล่า ไม่สามารถประมวลผลต่อได้
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP, separators=["\n\n", "\n", "。", ".", " ", ""])  # ตัวตัดข้อความเป็น chunk ตามขนาดที่กำหนด
    return [{"text": c, "source": source, "year": year} for c in splitter.split_text(text) if c.strip()]  # ตัด chunk แล้วประกอบ metadata แนบไปด้วย

# ------------------------------------------------------------------ #
# OLLAMA LLM INTEGRATION
# ------------------------------------------------------------------ #
import ollama as _ollama  # ไลบรารีไคลเอนต์สำหรับเรียก Ollama
_ollama_client = _ollama.Client(host=OLLAMA_HOST)  # สร้างไคลเอนต์เชื่อมต่อ Ollama server

def _build_messages(question: str, chunks: list[dict], history: list[dict] = None):  # ประกอบ prompt/ประวัติแชทให้เป็นรูปแบบที่ Ollama ต้องการ
    ctx = "\n\n---\n\n".join(c["text"] for c in chunks) if chunks else "(ไม่พบข้อมูลอ้างอิง)"  # รวมเนื้อหา chunk ที่ค้นเจอเป็น context เดียว
    user_msg = f"ข้อมูลอ้างอิงภายใน:\n{ctx}\n\nคำถาม: {question}\n\nตอบคำถามจากข้อมูลอ้างอิงเท่านั้น"  # ประกอบข้อความผู้ใช้ที่แนบ context เข้าไปด้วย
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_msg}]  # เริ่มต้นด้วย system prompt + คำถามปัจจุบัน
    if history: msgs = [msgs[0]] + list(history) + [msgs[1]]  # ถ้ามีประวัติแชทเก่า ให้แทรกไว้ตรงกลางก่อนคำถามล่าสุด
    return msgs  # คืนลิสต์ข้อความพร้อมส่งให้โมเดล

def ask_llm(question, chunks, history=None, model: str = None):  # เรียก LLM แบบรอคำตอบเต็มทีเดียว (ไม่สตรีม)
    # เพิ่มพารามิเตอร์ model (ไม่บังคับ) — ถ้าไม่ระบุมา ใช้ OLLAMA_MODEL ค่าเริ่มต้นของระบบเหมือนเดิม
    # ใช้กับฟีเจอร์ "เลือกโมเดล AI" ในหน้าแชทที่อาจารย์/บุคลากรเปลี่ยนโมเดลของแชทจริงได้ (ดู
    # /api/chat/stream ด้านล่าง) โดยไม่กระทบค่าเริ่มต้นของระบบหรือนักศึกษาคนอื่น
    r = _ollama_client.chat(model=model or OLLAMA_MODEL, messages=_build_messages(question, chunks, history), options={"num_ctx": OLLAMA_NUM_CTX}, keep_alive=0)  # เรียกโมเดลแบบ synchronous
    return _strip_answer_preamble(r["message"]["content"])  # ตัดวลีขึ้นต้นที่ไม่ต้องการออกก่อนคืนค่า

_ANSWER_PREAMBLE_RE = re.compile(r'^\s*(?:อ้างอิงจาก|จาก|ตาม)\s*(?:ข้อมูล|เอกสาร|คู่มือ)\s*(?:ที่ให้มา|ที่ได้รับ)?\s*[,ๆ]?\s*')  # regex จับวลีขึ้นต้นแบบ "จากข้อมูลที่ให้มา..."
def _strip_answer_preamble(text: str) -> str: return _ANSWER_PREAMBLE_RE.sub("", text, count=1).lstrip()  # ตัดวลีนั้นออกจากต้นคำตอบ (ครั้งเดียว)

def ask_llm_stream(question, chunks, history=None, model: str = None):  # เรียก LLM แบบสตรีมคำตอบทีละส่วน (generator)
    # เพิ่มพารามิเตอร์ model (ไม่บังคับ) เช่นเดียวกับ ask_llm ด้านบน — ไม่ระบุ = ใช้ OLLAMA_MODEL เดิม
    for part in _ollama.chat(model=model or OLLAMA_MODEL, messages=_build_messages(question, chunks, history), options={"num_ctx": OLLAMA_NUM_CTX}, stream=True, keep_alive=0):  # วนรับ token ที่โมเดลส่งมาทีละก้อน
        c = part["message"]["content"]  # เนื้อหาของ token ก้อนนี้
        if c: yield c  # ถ้ามีเนื้อหาจริง ส่งออกไปให้ผู้เรียกใช้ทันที

def check_ollama():  # เช็คว่าเชื่อมต่อ Ollama server ได้หรือไม่ (ใช้ทั้งตอนสตาร์ทและ /api/health)
    try:
        response = _ollama_client.list()  # ลองเรียกดูรายชื่อโมเดลที่มีในเครื่อง
        return True, "พร้อมใช้งาน (ข้ามการตรวจสอบชื่อโมเดล)"  # เชื่อมต่อสำเร็จ
    except Exception as e:
        return False, f"เชื่อมต่อ Ollama ไม่ได้: {e}"  # เชื่อมต่อไม่สำเร็จ พร้อมข้อความ error

# ------------------------------------------------------------------ #
# AUTHENTICATION & USERS (SQLite)
# ------------------------------------------------------------------ #
_auth_lock = threading.Lock()  # ล็อกกันหลาย request แก้ตาราง users พร้อมกัน

def _hash(pw: str) -> str: return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")  # แฮชรหัสผ่านด้วย bcrypt (มี salt ในตัว)
_OLD_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")  # รูปแบบ hash SHA-256 แบบเก่า (64 ตัวอักษร hex)

def _looks_like_old_sha256_hash(h: str) -> bool: return bool(_OLD_SHA256_RE.fullmatch(h or ""))  # เช็คว่า hash ที่เก็บไว้เป็นแบบเก่า (SHA-256) หรือไม่

def _verify_password(pw: str, stored_hash: str) -> bool:  # ตรวจรหัสผ่านที่ผู้ใช้กรอกกับ hash ที่เก็บไว้
    if not stored_hash: return False  # ไม่มี hash เก็บไว้เลย ถือว่าไม่ผ่าน
    if _looks_like_old_sha256_hash(stored_hash):  # ถ้าเป็น hash แบบเก่า
        return secrets.compare_digest(hashlib.sha256(pw.encode()).hexdigest(), stored_hash)  # เทียบแบบ SHA-256 (constant-time compare กัน timing attack)
    try: return bcrypt.checkpw(pw.encode("utf-8"), stored_hash.encode("utf-8"))  # ปกติเทียบแบบ bcrypt
    except Exception: return False  # ถ้า hash รูปแบบผิดพลาด ถือว่าไม่ผ่าน

def _load_users() -> dict:  # โหลดผู้ใช้ทั้งหมดเป็น dict {username: password_hash}
    conn = sqlite3.connect(str(DB_FILE))  # เปิดฐานข้อมูล
    cursor = conn.cursor()  # เคอร์เซอร์
    cursor.execute("SELECT username, password_hash FROM users")  # ดึงผู้ใช้ทุกคน
    rows = cursor.fetchall()  # อ่านผลลัพธ์ทั้งหมด
    conn.close()  # ปิดการเชื่อมต่อ
    return {row[0]: row[1] for row in rows}  # แปลงเป็น dict ให้ค้นหาเร็ว

def register_user(username, password):  # สมัครสมาชิกใหม่ (ใช้ตอนนักศึกษาล็อกอินครั้งแรก)
    if not username or not password: return False, "กรุณากรอกข้อมูลให้ครบถ้วน"  # เช็คข้อมูลว่าง
    with _auth_lock:  # ล็อกกันชนกับ request อื่น
        conn = sqlite3.connect(str(DB_FILE))  # เปิดฐานข้อมูล
        cursor = conn.cursor()  # เคอร์เซอร์
        cursor.execute("SELECT username FROM users WHERE username = ?", (username,))  # เช็คว่ามีบัญชีนี้อยู่แล้วหรือยัง
        if cursor.fetchone():  # ถ้ามีอยู่แล้ว
            conn.close()  # ปิดการเชื่อมต่อ
            return False, "มีบัญชีนี้อยู่แล้ว"  # แจ้งว่าซ้ำ
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, _hash(password)))  # สร้างบัญชีใหม่พร้อมแฮชรหัสผ่าน
        conn.commit()  # บันทึก
        conn.close()  # ปิดการเชื่อมต่อ
    return True, "สมัครสมาชิกสำเร็จ"  # สำเร็จ

def login_user(username, password):  # ตรวจสอบล็อกอินของผู้ใช้ที่มีบัญชีอยู่แล้ว
    if not username or not password: return False, "กรุณากรอกข้อมูลให้ครบถ้วน"  # เช็คข้อมูลว่าง
    with _auth_lock:  # ล็อกกันชน
        conn = sqlite3.connect(str(DB_FILE))  # เปิดฐานข้อมูล
        cursor = conn.cursor()  # เคอร์เซอร์
        cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))  # ดึง hash รหัสผ่านที่เก็บไว้
        row = cursor.fetchone()  # อ่านผลลัพธ์
        if not row:  # ไม่พบผู้ใช้
            conn.close()  # ปิดการเชื่อมต่อ
            return False, "ไม่พบรหัสนี้ในระบบ"  # แจ้ง error
        stored = row[0]  # hash ที่เก็บไว้จริง
        if not _verify_password(password, stored):  # ตรวจรหัสผ่านไม่ผ่าน
            conn.close()  # ปิดการเชื่อมต่อ
            return False, "รหัสผ่านไม่ถูกต้อง"  # แจ้ง error
        if _looks_like_old_sha256_hash(stored):  # ถ้ายังเป็น hash แบบเก่า
            cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", (_hash(password), username))  # อัปเกรดเป็น bcrypt ทันทีที่ล็อกอินสำเร็จ
            conn.commit()  # บันทึกการอัปเกรด hash
        conn.close()  # ปิดการเชื่อมต่อ
    return True, "เข้าสู่ระบบสำเร็จ"  # สำเร็จ

def list_users():  # ดึงรายชื่อผู้ใช้ทั้งหมด (ใช้ใน dev console)
    with _auth_lock:  # ล็อกกันชน
        conn = sqlite3.connect(str(DB_FILE))  # เปิดฐานข้อมูล
        cursor = conn.cursor()  # เคอร์เซอร์
        cursor.execute("SELECT username FROM users ORDER BY username")  # ดึงชื่อผู้ใช้เรียงตามตัวอักษร
        rows = cursor.fetchall()  # อ่านผลลัพธ์
        conn.close()  # ปิดการเชื่อมต่อ
        return [row[0] for row in rows]  # คืนเป็นลิสต์ของ username

def delete_user(username):  # ลบบัญชีผู้ใช้ (ใช้ใน dev console)
    with _auth_lock:  # ล็อกกันชน
        conn = sqlite3.connect(str(DB_FILE))  # เปิดฐานข้อมูล
        cursor = conn.cursor()  # เคอร์เซอร์
        cursor.execute("DELETE FROM users WHERE username = ?", (username,))  # ลบผู้ใช้ตาม username
        affected = cursor.rowcount  # จำนวนแถวที่ถูกลบจริง
        conn.commit()  # บันทึก
        conn.close()  # ปิดการเชื่อมต่อ
    if affected == 0: return False, "ไม่พบบัญชีนี้"  # ไม่พบผู้ใช้ที่จะลบ
    return True, "ลบบัญชีสำเร็จ"  # ลบสำเร็จ

# ------------------------------------------------------------------ #
# ROSTER & YEAR UTILS
# ------------------------------------------------------------------ #
ROSTER_FILE = BASE_DIR / "students_roster.json"  # ไฟล์รายชื่อรหัสนักศึกษาที่อนุญาตให้เข้าระบบ
def _load_roster():  # โหลดรายชื่อรหัสนักศึกษาที่อนุญาต
    if not ROSTER_FILE.exists(): return None  # ไม่มีไฟล์นี้ = ไม่จำกัดสิทธิ์ (คืน None)
    try: return set(json.loads(ROSTER_FILE.read_text(encoding="utf-8")))  # โหลดเป็น set เพื่อเช็คเร็ว
    except Exception: return None  # อ่านไฟล์ผิดพลาด ถือว่าไม่จำกัดสิทธิ์เช่นกัน

def is_code_in_roster(code: str):  # เช็คว่ารหัสนักศึกษานี้อยู่ในทะเบียนที่อนุญาตไหม
    r = _load_roster()  # โหลด roster
    return True if r is None else code in r  # ไม่มี roster = ผ่านทุกคน, มี roster = ต้องอยู่ในลิสต์

def extract_student_year(code: str): return code[:2] if len(code) == 11 and code.isdigit() else None  # ดึงรหัสรุ่น (2 ตัวแรก) จากรหัสนักศึกษา 11 หลัก

# ------------------------------------------------------------------ #
# SUGGESTED QUESTIONS (JSON)
# ------------------------------------------------------------------ #
_sq_lock = threading.Lock()  # ล็อกกันหลาย request แก้ไฟล์ JSON พร้อมกัน
def _load_sq():  # โหลดข้อมูลคำถามแนะนำจากไฟล์ JSON
    if not SUGGESTED_Q_FILE.exists(): return {"next_id": 1, "items": []}  # ยังไม่มีไฟล์ ให้ค่าเริ่มต้นว่าง
    try: return json.loads(SUGGESTED_Q_FILE.read_text(encoding="utf-8"))  # อ่านและ parse JSON
    except Exception: return {"next_id": 1, "items": []}  # ไฟล์เสีย ให้ค่าเริ่มต้นว่างแทน

def _save_sq(d): SUGGESTED_Q_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")  # เขียนข้อมูลกลับลงไฟล์ JSON

def list_suggested_questions():  # ดึงคำถามแนะนำทั้งหมด (ทุกรุ่น)
    with _sq_lock: return list(_load_sq()["items"])  # ล็อกอ่านแล้วคืนสำเนาลิสต์

def get_suggested_questions_for_year(year: str):  # ดึงคำถามแนะนำที่ตรงกับรุ่นที่ระบุ (รวมคำถามที่ใช้ได้ทุกรุ่นด้วย)
    year = (year or "").strip()  # ตัดช่องว่างของ year ที่รับมา
    items = list_suggested_questions()  # โหลดคำถามทั้งหมด
    return [i for i in items if not i.get("year")] + [i for i in items if year and i.get("year") == year]  # รวมคำถามที่ไม่ระบุรุ่น + คำถามที่ตรงรุ่นนี้

def add_suggested_question(year, q):  # เพิ่มคำถามแนะนำใหม่
    with _sq_lock:  # ล็อกกันชน
        d = _load_sq()  # โหลดข้อมูลปัจจุบัน
        item = {"id": d["next_id"], "year": year, "question": q}  # สร้าง record ใหม่พร้อม id ถัดไป
        d["items"].append(item)  # เพิ่มเข้าไปในลิสต์
        d["next_id"] += 1  # เพิ่มตัวนับ id ถัดไป
        _save_sq(d)  # บันทึกกลับลงไฟล์
        return item  # คืนค่า record ที่เพิ่งสร้าง

def delete_suggested_question(item_id):  # ลบคำถามแนะนำตาม id
    with _sq_lock:  # ล็อกกันชน
        d = _load_sq()  # โหลดข้อมูลปัจจุบัน
        before = len(d["items"])  # จำนวนก่อนลบ (ไว้เทียบ)
        d["items"] = [i for i in d["items"] if i["id"] != item_id]  # กรองตัวที่ต้องการลบออก
        if len(d["items"]) == before: return False  # จำนวนไม่เปลี่ยน แปลว่าไม่พบ id นี้
        _save_sq(d)  # บันทึกกลับลงไฟล์
        return True  # ลบสำเร็จ

def update_suggested_question(item_id, year, question):  # แก้ไขคำถามแนะนำที่มีอยู่แล้ว
    with _sq_lock:  # ล็อกกันชน
        d = _load_sq()  # โหลดข้อมูลปัจจุบัน
        for item in d["items"]:  # วนหา record ที่ id ตรงกัน
            if item["id"] == item_id:  # เจอแล้ว
                item["year"], item["question"] = year, question  # แก้ค่าปีและคำถามใหม่
                _save_sq(d)  # บันทึกกลับลงไฟล์
                return item  # คืนค่า record ที่แก้แล้ว
        return None  # ไม่พบ id ที่ต้องการแก้

# ------------------------------------------------------------------ #
# SESSION & CONVERSATION MANAGEMENT (SQLite)
# ------------------------------------------------------------------ #
STUDENT_SESSION_TTL = 12 * 3600  # อายุ session นักศึกษา: 12 ชั่วโมง
ADMIN_SESSION_TTL   = 8 * 3600  # อายุ session แอดมิน: 8 ชั่วโมง

# ประวัติแชท (conversations + chat_messages) เก็บไว้ได้ไม่เกิน CHAT_HISTORY_TTL วินาที
# นับจากครั้งล่าสุดที่แชทนั้นถูกใช้งาน (updated_at) — เกินแล้วลบทิ้งอัตโนมัติ เพื่อไม่ให้ฐานข้อมูลบวมเกินไป
# ปรับได้ผ่าน environment variable CHAT_HISTORY_TTL_HOURS (ค่าเริ่มต้น 8 ชม.)
CHAT_HISTORY_TTL = float(os.getenv("CHAT_HISTORY_TTL_HOURS", "8")) * 3600  # อายุสูงสุดของประวัติแชทก่อนถูกลบอัตโนมัติ (วินาที)
# ความถี่ที่ background task จะตรวจและเคลียร์แชทเก่า (ทุก 30 นาที ไม่จำเป็นต้องถี่เท่ากับ TTL เอง)
CHAT_CLEANUP_INTERVAL = 30 * 60  # ความถี่ที่ background task จะตรวจเช็ค (วินาที)

def _create_session_db(user_type, identifier, role="", year="", ttl=STUDENT_SESSION_TTL):  # สร้าง session token ใหม่ (ใช้ร่วมกันทั้งนักศึกษา/แอดมิน)
    token = secrets.token_urlsafe(32)  # สุ่ม token ที่คาดเดาไม่ได้
    expires_at = time.time() + ttl  # เวลาหมดอายุ = ตอนนี้ + ttl
    conn = sqlite3.connect(str(DB_FILE))  # เปิดฐานข้อมูล
    cursor = conn.cursor()  # เคอร์เซอร์
    cursor.execute("INSERT INTO sessions (token, user_type, identifier, role, year, expires_at) VALUES (?, ?, ?, ?, ?, ?)", (token, user_type, identifier, role, year, expires_at))  # บันทึก session ลงตาราง
    conn.commit()  # บันทึก
    conn.close()  # ปิดการเชื่อมต่อ
    return token  # คืน token ให้ client เก็บไว้ใช้

def _get_session_db(token, user_type):  # ตรวจสอบ token ว่ายังใช้ได้ไหม แล้วคืนข้อมูลเจ้าของ session
    conn = sqlite3.connect(str(DB_FILE))  # เปิดฐานข้อมูล
    cursor = conn.cursor()  # เคอร์เซอร์
    cursor.execute("SELECT identifier, role, year, expires_at FROM sessions WHERE token = ? AND user_type = ?", (token, user_type))  # ค้นหา session ตาม token+ประเภท
    row = cursor.fetchone()  # อ่านผลลัพธ์
    if not row or row[3] < time.time():  # ไม่พบ หรือหมดอายุแล้ว
        if row: cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))  # ถ้าหมดอายุ ให้ลบทิ้งไปเลย (เคลียร์ session เก่า)
        conn.commit()  # บันทึก
        conn.close()  # ปิดการเชื่อมต่อ
        return None  # แจ้งว่า session นี้ใช้ไม่ได้
    conn.close()  # ปิดการเชื่อมต่อ
    return {"identifier": row[0], "role": row[1], "year": row[2]}  # คืนข้อมูลเจ้าของ session

def _create_student_session(sid, role, year): return _create_session_db("student", sid, role, year, STUDENT_SESSION_TTL)  # สร้าง session สำหรับนักศึกษาโดยเฉพาะ
def _get_student_session(request: Request):  # FastAPI dependency: ดึง session นักศึกษาจาก header ของ request
    auth = request.headers.get("Authorization", "")  # อ่าน header Authorization
    if not auth.startswith("Bearer "): raise HTTPException(401, "กรุณาเข้าสู่ระบบก่อน")  # ไม่มี Bearer token เลย
    sess = _get_session_db(auth.removeprefix("Bearer ").strip(), "student")  # ตรวจสอบ token กับฐานข้อมูล
    if not sess: raise HTTPException(401, "เซสชันหมดอายุ กรุณาเข้าสู่ระบบใหม่")  # token ไม่ถูกต้อง/หมดอายุ
    return {"student_id": sess["identifier"], "role": sess["role"], "year": sess["year"]}  # คืนข้อมูล session ให้ endpoint ใช้ต่อ

def verify_own_student_session(student_id: str, request: Request):  # dependency: ต้องเป็นเจ้าของ student_id นี้เท่านั้นถึงเข้าถึงได้
    sess = _get_student_session(request)  # ตรวจ session ก่อน
    if sess["student_id"] != student_id: raise HTTPException(403, "ไม่มีสิทธิ์เข้าถึงข้อมูลผู้อื่น")  # เจ้าของ session ไม่ตรงกับ path parameter
    return sess  # ผ่าน คืนข้อมูล session

def _create_admin_session(username): return _create_session_db("admin", username, ttl=ADMIN_SESSION_TTL)  # สร้าง session สำหรับแอดมินโดยเฉพาะ
def verify_admin_session(request: Request):  # dependency: ตรวจสอบว่าเป็นแอดมินที่ล็อกอินถูกต้อง
    auth = request.headers.get("Authorization", "")  # อ่าน header Authorization
    if not auth.startswith("Bearer "): raise HTTPException(401, "กรุณาเข้าสู่ระบบแอดมิน")  # ไม่มี Bearer token
    sess = _get_session_db(auth.removeprefix("Bearer ").strip(), "admin")  # ตรวจสอบ token กับฐานข้อมูล
    if not sess: raise HTTPException(401, "เซสชันแอดมินหมดอายุ")  # token ไม่ถูกต้อง/หมดอายุ
    return sess["identifier"]  # คืน username ของแอดมิน

# --- ประวัติแชทด้วย SQLite ---
def composite_session_id(student_id, conv_id): return f"{student_id}::{conv_id}"  # รวม student_id+conv_id เป็น session_id เดียวใช้ฝั่ง frontend
def split_composite_session_id(sid):  # แยก session_id ที่รวมกันกลับเป็น student_id/conv_id
    return sid.split("::", 1) if "::" in sid else (None, None)  # ถ้าไม่มี "::" แปลว่าไม่ใช่รูปแบบนี้ คืน None คู่หนึ่ง

def get_history(sid, include_timestamp: bool = False):  # ดึงประวัติข้อความของแชทหนึ่ง เรียงตามเวลา
    # แก้บั๊ก "เวลาไม่ตรง": เดิมฟังก์ชันนี้ดึงแค่ role/content ทิ้งคอลัมน์ timestamp ที่บันทึกไว้จริง
    # ใน DB ไปเฉยๆ ทำให้ตอนโหลดประวัติแชทเก่ากลับมาแสดง (ดู /conversations/.../messages ด้านล่าง
    # + switchConversation ใน java.js) ไม่มีเวลาให้โชว์เลย พารามิเตอร์ include_timestamp (ไม่บังคับ)
    # เพิ่มเข้ามาให้เลือกได้ว่าจะเอา timestamp จริงมาด้วยไหม — ปิดไว้เป็นค่าเริ่มต้น (False) เพื่อ
    # ไม่ให้กระทบจุดที่เรียกใช้ history ไปยัดใส่ _build_messages() ส่งเข้า Ollama โดยตรง (เพิ่มคีย์
    # timestamp เข้าไปในนั้นอาจทำให้ library ของ Ollama งงกับ role message ที่ไม่รู้จักได้)
    s_id, c_id = split_composite_session_id(sid)  # แยกเป็น student_id/conv_id
    if not s_id: s_id, c_id = sid, "default"  # ถ้าแยกไม่ได้ ใช้ sid ทั้งก้อนเป็น student_id และ conv "default"
    conn = sqlite3.connect(str(DB_FILE))  # เปิดฐานข้อมูล
    cursor = conn.cursor()  # เคอร์เซอร์
    cursor.execute("SELECT role, content, timestamp FROM chat_messages WHERE student_id = ? AND conv_id = ? ORDER BY timestamp ASC", (s_id, c_id))  # ดึงข้อความของแชทนี้ เรียงเก่า→ใหม่ (เอา timestamp มาด้วยเสมอ เผื่อต้องใช้)
    rows = cursor.fetchall()  # อ่านผลลัพธ์
    conn.close()  # ปิดการเชื่อมต่อ
    if include_timestamp:
        return [{"role": r[0], "content": r[1], "timestamp": r[2]} for r in rows]  # รวม timestamp จริง (Unix epoch วินาที) ไว้ให้ frontend เอาไปแสดงผล
    return [{"role": r[0], "content": r[1]} for r in rows]  # ค่าเริ่มต้น: role/content ล้วนๆ เหมือนเดิมทุกประการ (ปลอดภัยกับ _build_messages)

def append_exchange(sid, q, a):  # บันทึกคู่คำถาม-คำตอบล่าสุดลงในแชท
    s_id, c_id = split_composite_session_id(sid)  # แยกเป็น student_id/conv_id
    if not s_id: s_id, c_id = sid, "default"  # กรณีไม่มี conv_id ให้ใช้ "default"
    now = time.time()  # เวลาปัจจุบัน
    conn = sqlite3.connect(str(DB_FILE))  # เปิดฐานข้อมูล
    cursor = conn.cursor()  # เคอร์เซอร์
    cursor.executemany("INSERT INTO chat_messages (student_id, conv_id, role, content, timestamp) VALUES (?, ?, ?, ?, ?)", [
        (s_id, c_id, "user", q, now),  # บันทึกข้อความฝั่งผู้ใช้
        (s_id, c_id, "assistant", a, now + 0.001)  # บันทึกคำตอบฝั่งบอท (เวลาขยับนิดหน่อยให้เรียงถูกลำดับ)
    ])
    conn.commit()  # บันทึก
    conn.close()  # ปิดการเชื่อมต่อ
    if c_id != "default": touch_conversation(s_id, c_id, first_message=q)  # อัปเดตเวลา/ชื่อแชท ถ้าไม่ใช่แชท default (แก้บั๊ก: เดิมลืมส่ง first_message=q ทำให้ตั้งชื่อแชทจากคำถามแรกไม่เคยทำงานจริง ชื่อค้างเป็น "แชทใหม่" ตลอด)

def list_conversations(student_id):  # ดึงรายการหัวข้อแชททั้งหมดของนักศึกษาคนหนึ่ง
    conn = sqlite3.connect(str(DB_FILE))  # เปิดฐานข้อมูล
    cursor = conn.cursor()  # เคอร์เซอร์
    cursor.execute("SELECT conv_id, title, created_at, updated_at FROM conversations WHERE student_id = ? ORDER BY updated_at DESC", (student_id,))  # ดึงแชท เรียงใช้งานล่าสุดก่อน
    rows = cursor.fetchall()  # อ่านผลลัพธ์
    conn.close()  # ปิดการเชื่อมต่อ
    return [{"id": r[0], "title": r[1], "created_at": r[2], "updated_at": r[3]} for r in rows]  # แปลงเป็นลิสต์ dict

def create_conversation(student_id):  # สร้างแชทใหม่ให้นักศึกษาคนหนึ่ง
    now = time.time()  # เวลาปัจจุบัน
    conv_id = "c_" + secrets.token_hex(6)  # สุ่ม id แชทใหม่
    conn = sqlite3.connect(str(DB_FILE))  # เปิดฐานข้อมูล
    cursor = conn.cursor()  # เคอร์เซอร์
    cursor.execute("INSERT INTO conversations (student_id, conv_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)", (student_id, conv_id, "แชทใหม่", now, now))  # สร้างแถวแชทใหม่ ชื่อเริ่มต้น "แชทใหม่"
    conn.commit()  # บันทึก
    conn.close()  # ปิดการเชื่อมต่อ
    return {"id": conv_id, "title": "แชทใหม่", "created_at": now, "updated_at": now}  # คืนข้อมูลแชทที่สร้าง

def touch_conversation(student_id, conversation_id, first_message=None):  # อัปเดตเวลาล่าสุด (และตั้งชื่อแชทอัตโนมัติ) ทุกครั้งที่มีข้อความใหม่
    now = time.time()  # เวลาปัจจุบัน
    conn = sqlite3.connect(str(DB_FILE))  # เปิดฐานข้อมูล
    cursor = conn.cursor()  # เคอร์เซอร์
    cursor.execute("SELECT title FROM conversations WHERE student_id = ? AND conv_id = ?", (student_id, conversation_id))  # ดึงชื่อแชทปัจจุบัน
    row = cursor.fetchone()  # อ่านผลลัพธ์
    if not row:  # ไม่พบแชทนี้ (อาจถูกลบไปแล้ว)
        conn.close()  # ปิดการเชื่อมต่อ
        return None  # ไม่ทำอะไรต่อ
    title = row[0]  # ชื่อแชทเดิม
    if first_message and title == "แชทใหม่":  # ถ้ายังเป็นชื่อ default และมีข้อความแรกส่งมา
        title = (first_message.strip()[:40] + "…") if len(first_message.strip()) > 40 else first_message.strip()  # ตั้งชื่อแชทจากข้อความแรก (ตัดไม่เกิน 40 ตัวอักษร)
    cursor.execute("UPDATE conversations SET updated_at = ?, title = ? WHERE student_id = ? AND conv_id = ?", (now, title, student_id, conversation_id))  # อัปเดตเวลาล่าสุด+ชื่อแชท
    conn.commit()  # บันทึก
    conn.close()  # ปิดการเชื่อมต่อ

def delete_conversation(student_id, conversation_id):  # ลบแชทหนึ่งแชท (ผู้ใช้กดลบเอง)
    conn = sqlite3.connect(str(DB_FILE))  # เปิดฐานข้อมูล
    cursor = conn.cursor()  # เคอร์เซอร์
    cursor.execute("DELETE FROM conversations WHERE student_id = ? AND conv_id = ?", (student_id, conversation_id))  # ลบหัวข้อแชท
    affected = cursor.rowcount  # จำนวนแถวที่ลบจริง (เช็คว่ามีแชทนี้อยู่จริงไหม)
    cursor.execute("DELETE FROM chat_messages WHERE student_id = ? AND conv_id = ?", (student_id, conversation_id))  # ลบข้อความทั้งหมดในแชทนี้ด้วย
    conn.commit()  # บันทึก
    conn.close()  # ปิดการเชื่อมต่อ
    return affected > 0  # คืนว่าลบสำเร็จจริงไหม (เคยมีแชทนี้อยู่)

def cleanup_old_conversations():
    """
    ลบแชท (conversations + chat_messages) ที่ไม่มีการใช้งาน (updated_at) เกิน CHAT_HISTORY_TTL
    เพื่อไม่ให้ตาราง chat_messages บวมขึ้นเรื่อยๆ แบบไม่มีที่สิ้นสุด
    คืนค่าจำนวนแชทที่ถูกลบไป (ไว้ log ดู)
    """  # ฟังก์ชันเคลียร์แชทเก่าอัตโนมัติ (ส่วนที่เพิ่มใหม่)
    cutoff = time.time() - CHAT_HISTORY_TTL  # คำนวณเวลาตัดขอบ: เก่ากว่านี้ถือว่าหมดอายุ
    conn = sqlite3.connect(str(DB_FILE))  # เปิดฐานข้อมูล
    cursor = conn.cursor()  # เคอร์เซอร์
    cursor.execute("SELECT student_id, conv_id FROM conversations WHERE updated_at < ?", (cutoff,))  # หาแชทที่ไม่มีการใช้งานเกิน TTL แล้ว
    old_convs = cursor.fetchall()  # รายการแชทที่ต้องลบ
    if old_convs:  # ถ้ามีแชทที่เข้าเงื่อนไข
        cursor.executemany("DELETE FROM chat_messages WHERE student_id = ? AND conv_id = ?", old_convs)  # ลบข้อความของแชทเหล่านั้นทั้งหมด
        cursor.executemany("DELETE FROM conversations WHERE student_id = ? AND conv_id = ?", old_convs)  # ลบหัวข้อแชทเหล่านั้นด้วย
        conn.commit()  # บันทึกการลบ
    conn.close()  # ปิดการเชื่อมต่อ
    return len(old_convs)  # คืนจำนวนแชทที่ถูกลบไป

async def _chat_cleanup_loop():
    """Background task: วนตรวจทุก CHAT_CLEANUP_INTERVAL วินาที แล้วเคลียร์แชทที่เกิน CHAT_HISTORY_TTL ทิ้ง"""  # task พื้นหลังที่รันอัตโนมัติตลอดอายุเซิร์ฟเวอร์
    while True:  # วนซ้ำตลอดไปจนกว่าจะถูกยกเลิก
        try:
            await asyncio.sleep(CHAT_CLEANUP_INTERVAL)  # รอตามรอบเวลาที่กำหนดก่อนเช็คแต่ละครั้ง
            deleted = await asyncio.to_thread(cleanup_old_conversations)  # รันฟังก์ชันเคลียร์แชทเก่า (ใน thread แยก กัน block event loop)
            if deleted:  # ถ้ามีการลบจริง
                print(f"[CLEANUP] ลบแชทที่ไม่ได้ใช้งานเกิน {CHAT_HISTORY_TTL / 3600:.1f} ชม. ไปแล้ว {deleted} แชท")  # log แจ้งผล
        except asyncio.CancelledError:  # ถูกสั่งยกเลิก (ตอนปิดเซิร์ฟเวอร์)
            break  # ออกจาก loop ทันที
        except Exception as e:  # เกิด error อื่นระหว่างเคลียร์
            print(f"[CLEANUP] เกิดข้อผิดพลาดระหว่างเคลียร์แชทเก่า: {e}")  # log error แต่ไม่ทำให้ loop หยุดทำงาน

# ------------------------------------------------------------------ #
# RETRIEVAL LOGIC
# ------------------------------------------------------------------ #
MIN_RELEVANCE_SCORE = 0.35  # คะแนนความเกี่ยวข้องขั้นต่ำที่ยอมรับ
KEYWORD_WEIGHT = 0.5  # น้ำหนักของคะแนนคำซ้ำ (keyword) เมื่อรวมกับ semantic score
_NGRAM_N = 3  # ขนาด n-gram ที่ใช้เทียบคำซ้ำ

def _char_ngrams(text: str, n: int = _NGRAM_N) -> set:  # แตกข้อความเป็นชุดตัวอักษรต่อเนื่อง n ตัว (n-gram)
    text = text.replace(" ", "").replace("\n", "").replace("\r", "").replace("\f", "")  # ตัดช่องว่าง/ขึ้นบรรทัดออกก่อน
    return {text[i:i+n] for i in range(max(0, len(text) - n + 1))}  # สร้าง set ของทุก n-gram ที่เป็นไปได้

def _keyword_overlap_score(query: str, chunk_text: str) -> float:  # คำนวณคะแนนความคล้ายแบบคำซ้ำระหว่างคำถามกับ chunk
    q_clean = re.sub(r"\s+", "", query.strip())  # คำถามที่ตัดช่องว่างออกหมด
    c_clean = re.sub(r"\s+", "", chunk_text.strip())  # เนื้อหา chunk ที่ตัดช่องว่างออกหมด
    if q_clean and q_clean in c_clean: return 1.0  # ถ้าคำถามทั้งประโยคอยู่ใน chunk เป๊ะๆ ให้คะแนนเต็ม
    q_grams, c_grams = _char_ngrams(query), _char_ngrams(chunk_text)  # แตกทั้งคู่เป็น n-gram
    if not q_grams: return 0.0  # คำถามสั้นเกินไปจนไม่มี n-gram เลย
    return len(q_grams & c_grams) / len(q_grams)  # สัดส่วน n-gram ของคำถามที่พบใน chunk

_YEAR_MENTION_RE = re.compile(r'ปี(?:การศึกษา)?\s*(?:พ\.?ศ\.?)?\s*0?(\d{2,4})')  # regex จับข้อความที่พูดถึง "ปี...66" หรือคล้ายกัน
def _extract_year_from_question(q: str):  # ดึงรุ่น/ปีที่ถูกพูดถึงในคำถามโดยตรง (ถ้ามี)
    m = _YEAR_MENTION_RE.search(q)  # ค้นหาด้วย regex
    if not m: return None  # ไม่พบการพูดถึงปีเลย
    digits = m.group(1)  # ตัวเลขที่จับได้
    return digits[-2:] if len(digits) in (2, 4) else None  # เอาแค่ 2 หลักท้าย (รองรับทั้ง พ.ศ. เต็มและแบบย่อ)

def retrieve_chunks(q: str, role: str, year: str) -> list[dict]:  # ฟังก์ชันหลักของ RAG: ค้นหา chunk ที่เกี่ยวข้องที่สุดกับคำถาม
    q = _fix_duplicated_thai_marks(_normalize_thai_digits(unicodedata.normalize("NFC", q)))  # ทำความสะอาดคำถามแบบเดียวกับตอนประมวลผลเอกสาร
    effective_year = _extract_year_from_question(q) or year  # ใช้ปีที่พูดถึงในคำถามก่อน ถ้าไม่มีค่อยใช้ปีของผู้ใช้เอง

    all_chunks = vector_store.search(q, 10**9)  # ค้นหาทุก chunk ที่มี (ใส่ top_k สูงมากเพื่อดึงมาให้ครบก่อนกรอง)
    relevant = [c for c in all_chunks if c.get("score", 0) >= MIN_RELEVANCE_SCORE]  # กรองเอาเฉพาะที่คะแนนผ่านเกณฑ์ขั้นต่ำ

    if role == "teacher":  # ถ้าเป็นบุคลากร/อาจารย์ ให้เห็นได้ทุกรุ่น
        candidates = relevant  # ใช้ทุก chunk ที่ผ่านเกณฑ์
        if effective_year:  # ถ้ามีการระบุปีที่สนใจ
            for c in candidates:  # วนให้คะแนนพิเศษ
                if c.get("year") == effective_year: c["score"] = c.get("score", 0.0) + 0.15  # เพิ่มคะแนนให้ chunk ที่ตรงปีที่สนใจ
    else:  # ถ้าเป็นนักศึกษา ต้องกรองตามรุ่นของตัวเองเท่านั้น
        candidates = [c for c in relevant if not c.get("year") or (effective_year and c.get("year") == effective_year)]  # เอาเฉพาะ chunk ที่ไม่ระบุรุ่น หรือรุ่นตรงกับผู้ใช้
        if not candidates and relevant:  # ถ้ากรองแล้วไม่เจอเลย แต่มี chunk อื่นอยู่
            candidates = [c for c in relevant if not c.get("year")]  # ลดเงื่อนไขเหลือแค่ chunk ที่ใช้ได้ทุกรุ่น

    for c in candidates:  # วนคำนวณคะแนนรวม
        c["hybrid_score"] = c.get("score", 0.0) + KEYWORD_WEIGHT * _keyword_overlap_score(q, c["text"])  # รวม semantic score กับ keyword score ตามน้ำหนักที่ตั้งไว้

    candidates.sort(key=lambda c: c["hybrid_score"], reverse=True)  # เรียงจากคะแนนรวมสูงสุดไปต่ำสุด
    return candidates[:TOP_K]  # คืนแค่ TOP_K อันดับแรก

# ------------------------------------------------------------------ #
# PYDANTIC MODELS (ข้อมูลสำหรับรับ Request Body)
# ------------------------------------------------------------------ #
class ChatBody(BaseModel):  # รูปแบบ body ที่ /api/chat/stream รับเข้ามา
    message: str = ""; history: list = []; session_id: str = "guest"; role: str = "student"; year: str = ""  # คำถาม, ประวัติ, session, บทบาท, รุ่น
    model: str = ""  # โมเดล AI ที่ต้องการใช้ตอบ (ไม่บังคับ) — ใช้ได้เฉพาะบัญชีที่ role="teacher" เท่านั้น
    # (เช็คซ้ำฝั่ง backend ใน api_chat_stream ด้านล่างเสมอ ไม่เชื่อ role ที่ client ส่งมาในนี้)
    # ปล่อยว่าง = ใช้ OLLAMA_MODEL ค่าเริ่มต้นของระบบเหมือนเดิมทุกประการ

class LoginBody(BaseModel):  # รูปแบบ body สำหรับล็อกอิน (ใช้ทั้งนักศึกษาและแอดมิน)
    username: str = ""; password: str = ""  # ชื่อผู้ใช้/รหัสผ่าน

class ChangePasswordBody(BaseModel):  # รูปแบบ body สำหรับเปลี่ยนรหัสผ่านแอดมิน
    old_password: str = ""  # รหัสผ่านเดิม
    new_password: str = ""  # รหัสผ่านใหม่

class SuggestedQuestionBody(BaseModel):  # รูปแบบ body สำหรับเพิ่ม/แก้คำถามแนะนำ
    year: str = ""; question: str = ""  # รุ่นที่ใช้ได้ และตัวคำถาม

# ------------------------------------------------------------------ #
# FASTAPI APP & RATE LIMITING
# ------------------------------------------------------------------ #
@asynccontextmanager
async def lifespan(app: FastAPI):  # ฟังก์ชันที่ FastAPI เรียกตอนเปิด/ปิดเซิร์ฟเวอร์
    ok, msg = check_ollama()  # เช็คสถานะ Ollama ตอนสตาร์ท
    print("=" * 60)  # เส้นคั่น log
    print(f"RAG Chatbot (SQLite Connected) | Ollama: {msg}")  # แสดงสถานะเริ่มต้นของระบบ
    # เตือนถ้ายังใช้รหัสผ่านแอดมินเริ่มต้น (ค่า default) อยู่ — ควรตั้ง ADMIN_PASSWORD เป็นค่าอื่น
    # ก่อน deploy จริง ข้อความนี้แสดงในคอนโซลเซิร์ฟเวอร์เท่านั้น ไม่มี API ใดคืนค่านี้ออกไปทางเน็ตเวิร์ก
    if ADMIN_PASSWORD == "123456":  # ถ้ายังใช้รหัสผ่านตั้งต้น
        print(f"[SECURITY] บัญชีแอดมิน ({ADMIN_EMAIL}) ยังใช้รหัสผ่านเริ่มต้น 123456 อยู่ — "
              f"กรุณาเปลี่ยนรหัสผ่านทันทีหลังเข้าสู่ระบบ หรือตั้งค่า environment variable "
              f"ADMIN_PASSWORD ก่อน deploy จริง")  # เตือนใน console
    if len(ALLOWED_ORIGINS) == 1 and ALLOWED_ORIGINS[0] == "*":  # ถ้า CORS เปิดกว้างทุกโดเมน
        print(f"[SECURITY] CORS เปิดกว้างทุกโดเมน (ALLOWED_ORIGINS=*) — เหมาะสำหรับ dev เท่านั้น "
              f"ตั้งค่า environment variable ALLOWED_ORIGINS ก่อน deploy จริง")  # เตือนใน console
    print(f"[CLEANUP] เก็บประวัติแชทไว้ไม่เกิน {CHAT_HISTORY_TTL / 3600:.1f} ชม. หลังใช้งานล่าสุด "
          f"(ตรวจทุก {CHAT_CLEANUP_INTERVAL // 60} นาที)")  # แจ้งค่าตั้งต้นของระบบเคลียร์แชท
    print("=" * 60)  # เส้นคั่น log

    # ลบแชทเก่าที่ค้างอยู่ทันทีตอนสตาร์ทระบบ (เผื่อค้างมาจากตอนที่เซิร์ฟเวอร์ปิดอยู่)
    # แล้วค่อยปล่อยให้ background loop ดูแลต่อเป็นระยะๆ ระหว่างที่แอปทำงานอยู่
    await asyncio.to_thread(cleanup_old_conversations)  # เคลียร์แชทเก่ารอบแรกทันทีตอนสตาร์ท
    cleanup_task = asyncio.create_task(_chat_cleanup_loop())  # เริ่ม background task ให้วนเคลียร์ต่อเนื่อง

    yield  # จุดที่แอปเริ่มรับ request ได้ (โค้ดก่อนหน้านี้รันตอนสตาร์ท, หลังจากนี้รันตอนปิด)

    cleanup_task.cancel()  # สั่งยกเลิก background task ตอนปิดเซิร์ฟเวอร์
    try:
        await cleanup_task  # รอให้ task ยกเลิกเสร็จเรียบร้อย
    except asyncio.CancelledError:  # การยกเลิกจะโยน exception นี้ออกมาเป็นปกติ
        pass  # ไม่ต้องทำอะไรเพิ่ม ถือว่าปิดเรียบร้อย

app = FastAPI(title="RAG Chatbot", lifespan=lifespan)  # สร้างแอป FastAPI พร้อมผูก lifespan ที่กำหนดไว้

# ------------------------------------------------------------------ #
# CORS — จำกัด origin ที่อนุญาตผ่าน environment variable แทนการเปิดกว้างทุกโดเมนแบบเดิม
# ตั้งค่า ALLOWED_ORIGINS="https://example.com,https://admin.example.com" ตอน deploy จริง
# (คั่นด้วยจุลภาค) ถ้าไม่ตั้งค่าเลย จะ fallback เป็น localhost สำหรับ dev เท่านั้น ไม่ใช่ "*"
# ------------------------------------------------------------------ #
_default_origins = "http://localhost:8000,http://127.0.0.1:8000"  # ค่า default ตอน dev
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", _default_origins).split(",") if o.strip()]  # อ่านรายชื่อ origin ที่อนุญาตจาก env
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_methods=["*"], allow_headers=["*"])  # ติดตั้ง CORS middleware
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static_assets")), name="static")  # เปิดเสิร์ฟไฟล์ static ที่ /static

_chat_rate_state = {}  # เก็บสถานะการนับ request ต่อ IP (ในหน่วยความจำ)
_chat_rate_lock = threading.Lock()  # ล็อกกันหลาย request แก้ state พร้อมกัน
def _check_chat_rate_limit(ip: str):  # ตรวจ rate limit ของการแชทตาม IP (20 คำขอ/นาที)
    now = time.time()  # เวลาปัจจุบัน
    with _chat_rate_lock:  # ล็อกกันชน
        rec = _chat_rate_state.get(ip)  # ดูสถิติของ IP นี้
        if rec is None or (now - rec["window_start"]) >= 60:  # ยังไม่เคยมี หรือเลยหน้าต่างเวลา 60 วิแล้ว
            _chat_rate_state[ip] = {"window_start": now, "count": 1}  # เริ่มนับหน้าต่างใหม่
            return True, 0  # อนุญาตให้ผ่าน
        if rec["count"] >= 20:  # ถ้าเกิน 20 ครั้งในหน้าต่างนี้แล้ว
            return False, int(60 - (now - rec["window_start"])) + 1  # ปฏิเสธ พร้อมบอกว่าต้องรออีกกี่วินาที
        rec["count"] += 1  # ยังไม่เกิน เพิ่มตัวนับ
        return True, 0  # อนุญาตให้ผ่าน

# ------------------------------------------------------------------ #
# API ENDPOINTS
# ------------------------------------------------------------------ #
@app.get("/", response_class=HTMLResponse)
async def root():  # หน้าแรกของเว็บ
    return FileResponse(str(BASE_DIR / "pang.html"), media_type="text/html")  # ส่งไฟล์ pang.html กลับไป

@app.get("/user.html")
async def p_user():  # เสิร์ฟหน้าล็อกอินนักศึกษา
    return FileResponse(str(BASE_DIR / "user.html"), media_type="text/html")  # ส่งไฟล์ user.html

@app.get("/chatbot.html")
async def p_chat():  # เสิร์ฟหน้าแชทบอท
    return FileResponse(str(BASE_DIR / "chatbot.html"), media_type="text/html")  # ส่งไฟล์ chatbot.html

@app.get("/loginadmin.html")
async def p_ladm():  # เสิร์ฟหน้าล็อกอินแอดมิน
    return FileResponse(str(BASE_DIR / "loginadmin.html"), media_type="text/html")  # ส่งไฟล์ loginadmin.html

@app.get("/admin.html")
async def p_adm():  # เสิร์ฟหน้าแดชบอร์ดแอดมิน
    return FileResponse(str(BASE_DIR / "admin.html"), media_type="text/html")  # ส่งไฟล์ admin.html

@app.get("/upload.html")
async def p_upl():  # เสิร์ฟหน้าอัปโหลด/จัดการคู่มือ
    return FileResponse(str(BASE_DIR / "upload.html"), media_type="text/html")  # ส่งไฟล์ upload.html

@app.get("/dev.html")
async def p_dev():  # เสิร์ฟหน้า developer console
    return FileResponse(str(BASE_DIR / "dev.html"), media_type="text/html")  # ส่งไฟล์ dev.html (ใช้ style.css/java.js กลางร่วมกับหน้าอื่นแล้ว)

@app.get("/pang.html")
async def p_pang():  # เสิร์ฟหน้าแรกอีกเส้นทางหนึ่ง (ตรงกับ path ตัวเอง)
    return FileResponse(str(BASE_DIR / "pang.html"), media_type="text/html")  # ส่งไฟล์ pang.html

@app.get("/style.css")
async def css():  # เสิร์ฟไฟล์ CSS หลัก
    return FileResponse(str(BASE_DIR / "style.css"), media_type="text/css")  # ส่งไฟล์ style.css

@app.get("/java.js")
async def js():  # เสิร์ฟไฟล์ JavaScript หลักฝั่ง frontend
    return FileResponse(str(BASE_DIR / "java.js"), media_type="application/javascript")  # ส่งไฟล์ java.js

@app.get("/mascot.png")
async def img():  # เสิร์ฟรูปมาสคอต
    return FileResponse(str(BASE_DIR / "mascot.png"), media_type="image/png")  # ส่งไฟล์รูป mascot.png

@app.get("/logout-icon.png")
async def ico():  # เสิร์ฟไอคอนปุ่มออกจากระบบ
    return FileResponse(str(BASE_DIR / "logout-icon.png"), media_type="image/png")  # ส่งไฟล์รูปไอคอน

@app.get("/api/health")
async def health():  # endpoint ตรวจสถานะระบบ (public ไม่ต้องล็อกอิน)
    ok_flag, msg = check_ollama()  # เช็คสถานะ Ollama
    return {"status": "ok", "vector_store": vector_store.stats(), "ollama": {"connected": ok_flag, "message": msg}}  # คืนสถานะรวมของระบบ

@app.post("/login")
async def user_login(body: LoginBody):  # endpoint ล็อกอินของนักศึกษา/บุคลากร
    uname, pwd = body.username.strip(), body.password.strip()  # ตัดช่องว่างของ username/password
    s_year = extract_student_year(uname)  # เช็คว่า username เป็นรหัสนักศึกษาไหม (ดึงรุ่นออกมา)
    if s_year is not None and s_year not in vector_store.available_years():  # เป็นนักศึกษา แต่รุ่นนี้ยังไม่มีเอกสารรองรับ
        return JSONResponse({"detail": f"ยังไม่มีเอกสารคู่มือสำหรับรุ่น '{s_year}' ในระบบ"}, status_code=403)  # ปฏิเสธการล็อกอิน

    role, year = ("student" if s_year is not None else "teacher"), (s_year or "")  # กำหนดบทบาทตามรูปแบบ username
    users = _load_users()  # โหลดผู้ใช้ทั้งหมดที่เคยสมัคร
    if uname not in users:  # ยังไม่เคยสมัครมาก่อน
        if not is_code_in_roster(uname): return JSONResponse({"detail": "ไม่พบรหัสในระบบทะเบียน"}, status_code=403)  # ไม่อยู่ในทะเบียนที่อนุญาต ปฏิเสธ
        register_user(uname, pwd)  # สมัครสมาชิกให้อัตโนมัติ (รหัสผ่าน = รหัสนักศึกษาที่กรอกครั้งแรก)
    else:  # เคยมีบัญชีอยู่แล้ว
        ok_flag, msg = login_user(uname, pwd)  # ตรวจสอบรหัสผ่านตามปกติ
        if not ok_flag: return JSONResponse({"detail": msg}, status_code=401)  # รหัสผ่านผิด ปฏิเสธ

    token = _create_student_session(uname, role, year)  # สร้าง session ใหม่ให้ผู้ใช้
    return {"message": "เข้าสู่ระบบสำเร็จ", "token": token, "role": role, "year": year}  # คืน token+ข้อมูลผู้ใช้

@app.post("/logout")
async def user_logout(request: Request):  # endpoint ออกจากระบบ (ใช้ได้ทั้งนักศึกษา/แอดมิน)
    auth = request.headers.get("Authorization", "")  # อ่าน header Authorization
    if auth.startswith("Bearer "):  # ถ้ามี token แนบมา
        conn = sqlite3.connect(str(DB_FILE))  # เปิดฐานข้อมูล
        cursor = conn.cursor()  # เคอร์เซอร์
        cursor.execute("DELETE FROM sessions WHERE token = ?", (auth.removeprefix("Bearer ").strip(),))  # ลบ session token นี้ทิ้ง
        conn.commit()  # บันทึก
        conn.close()  # ปิดการเชื่อมต่อ
    return {"message": "ออกจากระบบแล้ว"}  # แจ้งผลสำเร็จเสมอ (แม้ไม่มี token ก็ไม่ error)

@app.post("/api/chat/stream")
async def api_chat_stream(body: ChatBody, request: Request, session: dict = Depends(_get_student_session)):  # endpoint หลักของการแชท (ต้องล็อกอินก่อน)
    ip = request.client.host if request.client else "unknown"  # ดึง IP ของผู้เรียก (ไว้เช็ค rate limit)
    allowed, wait_sec = _check_chat_rate_limit(ip)  # ตรวจ rate limit
    if not allowed: return JSONResponse({"detail": f"ส่งข้อความถี่เกินไป กรุณารอ {wait_sec} วินาที"}, status_code=429)  # เกิน rate limit ปฏิเสธ

    q = body.message.strip()  # คำถามที่ตัดช่องว่างแล้ว
    if not q: return JSONResponse({"detail": "ข้อความว่างเปล่า"}, status_code=400)  # คำถามว่าง ปฏิเสธ

    role, year = session["role"], session["year"]  # บทบาท/รุ่นของผู้ถามจาก session
    s_id, c_id = split_composite_session_id(body.session_id)  # แยก session_id ที่ frontend ส่งมา
    if not s_id: s_id = session["student_id"]  # ถ้าแยกไม่ได้ ใช้ student_id จาก session แทน

    # เลือกโมเดล AI ของแชทนี้ — ฟีเจอร์ใหม่: อาจารย์/บุคลากร (role="teacher" ที่ยืนยันจาก session
    # จริงบน backend เท่านั้น ไม่เชื่อ body.role ที่ client ส่งมา) เปลี่ยนโมเดลที่ใช้ตอบคำถามในแชท
    # จริงของตัวเองได้ผ่าน UI ในหน้าแชท (ดู chatbot.html/java.js ส่วนที่ 2) นักศึกษาทุกคนและ
    # อาจารย์/บุคลากรที่ไม่ได้เลือกโมเดล ยังใช้ OLLAMA_MODEL ค่าเริ่มต้นของระบบเหมือนเดิมทุกประการ
    selected_model = OLLAMA_MODEL  # ค่าเริ่มต้น
    requested_model = body.model.strip()  # โมเดลที่ client ขอมา (ถ้ามี)
    if role == "teacher" and requested_model:  # อนุญาตเฉพาะบทบาทอาจารย์/บุคลากรเท่านั้น
        try:
            available = _list_ollama_models()  # เช็กว่ามีโมเดลนี้ติดตั้งจริงบนเครื่อง Ollama ไหม
            if available and requested_model not in available:
                return JSONResponse({"detail": f"ไม่พบโมเดล '{requested_model}' บนเครื่อง Ollama"}, status_code=400)  # กันชื่อโมเดลมั่ว/ไม่ได้ติดตั้ง
        except Exception:
            pass  # ต่อ Ollama ไม่ได้ตอน list ก็ปล่อยให้เรียกแชทด้านล่างรายงาน error เองแทน
        selected_model = requested_model  # ผ่านการตรวจสอบแล้ว ใช้โมเดลที่เลือก

    history = get_history(body.session_id)  # ดึงประวัติแชทเดิมของ session นี้
    chunks = retrieve_chunks(q, role, year)  # ค้นหา chunk ที่เกี่ยวข้องกับคำถาม (ขั้นตอน RAG)

    def generate():  # generator สำหรับสตรีมข้อมูลกลับแบบ SSE
        # ฟีเจอร์ใหม่: แจ้งชื่อโมเดลจริงที่ backend เลือกใช้ตอบคำถามนี้กลับไปให้ frontend ก่อนเป็น
        # อันดับแรก (event type "meta") เพื่อให้อาจารย์/บุคลากรยืนยันได้จริงว่าคำตอบมาจากโมเดล
        # ที่เลือกไว้หรือไม่ ไม่ใช่แค่เชื่อว่า client ส่ง model ไปแล้วต้องเป็นแบบนั้นจริง — ดู
        # java.js ส่วนที่ 2 (payload.type === "meta") ที่แสดงป้ายนี้ใต้คำตอบ
        yield f"data: {json.dumps({'type':'meta','model':selected_model}, ensure_ascii=False)}\n\n"

        seen = []  # เก็บชื่อไฟล์แหล่งอ้างอิงที่ไม่ซ้ำ
        for c in chunks:  # วนดู chunk ที่ค้นเจอ
            if c["source"] not in seen: seen.append(c["source"])  # เก็บชื่อไฟล์ที่ยังไม่เคยเจอ
        yield f"data: {json.dumps({'type':'sources','sources':[{'source':s} for s in seen]}, ensure_ascii=False)}\n\n"  # ส่งรายชื่อแหล่งอ้างอิงก่อนเป็นอันดับแรก

        full_ans = ""  # เก็บคำตอบเต็มไว้บันทึกทีหลัง
        try:
            for token in ask_llm_stream(q, chunks, history=history, model=selected_model):  # วนรับคำตอบจาก LLM ทีละ token (ใช้โมเดลที่เลือกไว้ด้านบน)
                full_ans += token  # สะสมคำตอบเต็ม
                yield f"data: {json.dumps({'type':'token','content':token}, ensure_ascii=False)}\n\n"  # ส่ง token นี้ไปให้ frontend ทันที
            append_exchange(body.session_id, q, full_ans)  # บันทึกคำถาม-คำตอบคู่นี้ลงฐานข้อมูล
        except Exception as e:  # ถ้าเกิด error ระหว่างเรียก LLM
            yield f"data: {json.dumps({'type':'error','message':str(e)})}\n\n"  # แจ้ง error กลับไปที่ frontend
        yield f"data: {json.dumps({'type':'done'})}\n\n"  # ส่งสัญญาณจบสตรีม

    return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})  # คืน response แบบ SSE streaming

# ดึงรายชื่อโมเดล AI ที่เลือกได้ในหน้าแชท — ฟีเจอร์ใหม่ คู่กับพารามิเตอร์ model ใน ChatBody/
# api_chat_stream ด้านบน ใช้ session token ปกติของนักศึกษา/อาจารย์ (ไม่ใช่ admin_token) แต่จำกัด
# เฉพาะบัญชีที่ role="teacher" เท่านั้นถึงจะเรียกได้ (นักศึกษาเรียกแล้วได้ 403 เสมอ) — เรียกใช้
# _list_ollama_models() ตัวเดียวกับที่ /dev/models ใช้ (นิยามอยู่ด้านล่างในไฟล์นี้)
@app.get("/api/models")
async def api_list_models(session: dict = Depends(_get_student_session)):  # endpoint คืนรายชื่อโมเดล AI ที่เลือกทดสอบ/ใช้งานได้ (เฉพาะอาจารย์/บุคลากร)
    if session["role"] != "teacher":  # นักศึกษาไม่มีสิทธิ์เห็นรายชื่อโมเดล/เปลี่ยนโมเดล
        raise HTTPException(403, "เฉพาะอาจารย์/บุคลากรเท่านั้นที่เลือกโมเดลได้")  # ปฏิเสธ
    try:
        return {"models": _list_ollama_models(), "active_default": OLLAMA_MODEL}  # คืนรายชื่อโมเดล พร้อมบอกว่าตัวไหนคือค่าเริ่มต้นของระบบ
    except Exception as e:
        return JSONResponse({"detail": f"เชื่อมต่อ Ollama ไม่ได้: {e}"}, status_code=502)  # Ollama ไม่ตอบสนอง

@app.get("/conversations/{student_id}", dependencies=[Depends(verify_own_student_session)])
async def api_list_conv(student_id: str): return {"conversations": list_conversations(student_id)}  # ดึงรายการแชททั้งหมดของนักศึกษาคนนี้ (ต้องเป็นเจ้าของ)

@app.post("/conversations/{student_id}", dependencies=[Depends(verify_own_student_session)])
async def api_create_conv(student_id: str): return {"conversation": create_conversation(student_id)}  # สร้างแชทใหม่ (ต้องเป็นเจ้าของ)

@app.get("/conversations/{student_id}/{conv_id}/messages", dependencies=[Depends(verify_own_student_session)])
async def api_get_messages(student_id: str, conv_id: str): return {"messages": get_history(composite_session_id(student_id, conv_id), include_timestamp=True)}  # ดึงข้อความในแชทหนึ่งๆ พร้อมเวลาจริงที่บันทึกไว้ (ต้องเป็นเจ้าของ) — แก้บั๊ก "เวลาไม่ตรง" ที่ frontend เคยไม่มี timestamp ให้ใช้เลย

@app.delete("/conversations/{student_id}/{conv_id}", dependencies=[Depends(verify_own_student_session)])
async def api_del_conv(student_id: str, conv_id: str):  # ลบแชทหนึ่งแชท (ผู้ใช้กดลบเอง, ต้องเป็นเจ้าของ)
    if not delete_conversation(student_id, conv_id): return JSONResponse({"detail": "ไม่พบแชท"}, status_code=404)  # ไม่พบแชทนี้ คืน 404
    return {"message": "ลบแชทแล้ว"}  # ลบสำเร็จ

@app.get("/api/suggested-questions")
async def api_sq(year: str = ""):  # endpoint public ดึงคำถามแนะนำตามรุ่น (ไม่ต้องล็อกอิน)
    items = get_suggested_questions_for_year(year)  # ดึงคำถามที่ตรงกับรุ่นนี้
    return {"questions": [{"id": i["id"], "question": i["question"]} for i in items]}  # คืนเฉพาะ id+question (ไม่โชว์ year)

# --- แอดมิน Endpoint ---
@app.post("/admin/login")
async def admin_login(body: LoginBody):  # endpoint ล็อกอินของแอดมิน
    uname, pwd = body.username.strip().lower(), body.password.strip()  # normalize username เป็นตัวพิมพ์เล็ก
    if not uname or not pwd:  # ข้อมูลไม่ครบ
        return JSONResponse({"detail": "กรุณากรอกข้อมูลให้ครบถ้วน"}, status_code=400)  # ปฏิเสธ

    conn = sqlite3.connect(str(DB_FILE))  # เปิดฐานข้อมูล
    cursor = conn.cursor()  # เคอร์เซอร์
    cursor.execute("SELECT password_hash FROM users WHERE username = ? AND is_admin = 1", (uname,))  # หา hash รหัสผ่านของบัญชีนี้ (ต้องเป็นแอดมินเท่านั้น)
    row = cursor.fetchone()  # อ่านผลลัพธ์
    conn.close()  # ปิดการเชื่อมต่อ

    if not row or not _verify_password(pwd, row[0]):  # ไม่พบบัญชี หรือรหัสผ่านผิด
        return JSONResponse({"detail": "อีเมลหรือรหัสผ่านไม่ถูกต้อง"}, status_code=401)  # ปฏิเสธ (ไม่บอกว่าผิดจุดไหนเพื่อความปลอดภัย)

    token = _create_admin_session(uname)  # สร้าง session แอดมิน
    return {"message": "เข้าสู่ระบบสำเร็จ", "token": token}  # คืน token

@app.post("/admin/change-password", dependencies=[Depends(verify_admin_session)])
async def admin_change_password(body: ChangePasswordBody, request: Request):  # endpoint เปลี่ยนรหัสผ่านแอดมิน (ต้องล็อกอินอยู่แล้ว)
    admin_username = verify_admin_session(request)  # ดึง username แอดมินจาก session ปัจจุบัน
    old_pw = body.old_password.strip()  # รหัสผ่านเดิมที่กรอกมา
    new_pw = body.new_password.strip()  # รหัสผ่านใหม่ที่ต้องการตั้ง

    if len(new_pw) < 6:  # รหัสผ่านใหม่สั้นเกินไป
        return JSONResponse({"detail": "รหัสผ่านใหม่ต้องมีความยาวอย่างน้อย 6 ตัวอักษร"}, status_code=400)  # ปฏิเสธ

    conn = sqlite3.connect(str(DB_FILE))  # เปิดฐานข้อมูล
    cursor = conn.cursor()  # เคอร์เซอร์
    cursor.execute("SELECT password_hash FROM users WHERE username = ?", (admin_username,))  # ดึง hash รหัสผ่านปัจจุบัน
    row = cursor.fetchone()  # อ่านผลลัพธ์

    if not row or not _verify_password(old_pw, row[0]):  # รหัสผ่านเดิมที่กรอกมาไม่ถูกต้อง
        conn.close()  # ปิดการเชื่อมต่อ
        return JSONResponse({"detail": "รหัสผ่านเดิมไม่ถูกต้อง"}, status_code=400)  # ปฏิเสธ

    new_hash = _hash(new_pw)  # แฮชรหัสผ่านใหม่
    cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", (new_hash, admin_username))  # อัปเดตรหัสผ่านในฐานข้อมูล
    conn.commit()  # บันทึก
    conn.close()  # ปิดการเชื่อมต่อ

    return {"message": "เปลี่ยนรหัสผ่านสำเร็จ"}  # แจ้งผลสำเร็จ

@app.post("/admin/upload", dependencies=[Depends(verify_admin_session)])
async def admin_upload(file: UploadFile = File(...), year: str = Form("")):  # endpoint อัปโหลดไฟล์คู่มือใหม่ (เฉพาะแอดมิน)
    if not file.filename: return JSONResponse({"detail": "ไม่พบไฟล์"}, status_code=400)  # ไม่มีไฟล์แนบมา
    filename = safe_filename(file.filename)  # ทำชื่อไฟล์ให้ปลอดภัย
    tmp = UPLOAD_DIR / f"temp_{filename}"  # ที่พักไฟล์ชั่วคราวระหว่างประมวลผล
    content = await file.read()  # อ่านเนื้อหาไฟล์ที่อัปโหลดมา
    try:
        with open(tmp, "wb") as f: f.write(content)  # เขียนไฟล์ชั่วคราวลงดิสก์ก่อน
        chunks = process_file(str(tmp), year.strip())  # ตัดไฟล์เป็น chunk พร้อม metadata ปี
        n = vector_store.replace_source(filename, chunks)  # เพิ่ม/แทนที่ chunk เดิมใน FAISS
        os.replace(tmp, UPLOAD_DIR / filename)  # ย้ายไฟล์จาก temp ไปเป็นไฟล์จริงหลังประมวลผลสำเร็จ
        return {"message": f"อัปโหลดสำเร็จ ({n} chunks)", "filename": filename, "year": year}  # แจ้งผลสำเร็จ
    except Exception as e:  # ถ้าเกิดข้อผิดพลาดระหว่างประมวลผล
        if tmp.exists(): tmp.unlink()  # ลบไฟล์ชั่วคราวทิ้ง (กันขยะค้าง)
        return JSONResponse({"detail": f"ผิดพลาด: {e}"}, status_code=500)  # แจ้ง error กลับไป

@app.get("/admin/files", dependencies=[Depends(verify_admin_session)])
async def admin_files(): return {"files": vector_store.list_documents_detailed()}  # ดึงรายชื่อไฟล์เอกสารทั้งหมดพร้อมจำนวน chunk/ปี

# ค้นหาไฟล์คู่มือด้วยชื่อไฟล์ — เชื่อมกับปุ่ม "ค้นหา" ใน #searchForm (upload.html/java.js)
# ที่มี UI อยู่แล้วแต่ยังไม่เคยมี endpoint นี้มาก่อน (ค้นหาแบบ case-insensitive, contains)
@app.get("/admin/files/search", dependencies=[Depends(verify_admin_session)])
async def admin_files_search(q: str = ""):  # endpoint ค้นหาไฟล์เอกสารด้วยคำค้น
    keyword = q.strip().lower()  # คำค้นแบบตัวพิมพ์เล็กทั้งหมด
    files = vector_store.list_documents_detailed()  # ดึงรายชื่อไฟล์ทั้งหมดก่อน
    if keyword:  # ถ้ามีคำค้น
        files = [f for f in files if keyword in f["source"].lower()]  # กรองเฉพาะชื่อไฟล์ที่มีคำค้นอยู่
    return {"files": files}  # คืนผลลัพธ์ที่กรองแล้ว

@app.delete("/admin/files/{filename}", dependencies=[Depends(verify_admin_session)])
async def admin_del_file(filename: str):  # endpoint ลบไฟล์เอกสาร (เฉพาะแอดมิน)
    fpath = UPLOAD_DIR / safe_filename(filename)  # path ของไฟล์จริงบนดิสก์
    if fpath.exists(): fpath.unlink()  # ลบไฟล์จริงถ้ามีอยู่
    rem = vector_store.delete_by_source(filename)  # ลบ chunk ที่เกี่ยวข้องออกจาก FAISS ด้วย
    return {"message": f"ลบเรียบร้อย ({rem} chunks)"}  # แจ้งผลสำเร็จพร้อมจำนวน chunk ที่ลบ

@app.get("/admin/suggested-questions", dependencies=[Depends(verify_admin_session)])
async def admin_get_sq(): return {"items": list_suggested_questions()}  # ดึงคำถามแนะนำทั้งหมด (ฝั่งแอดมินเห็นทุกรุ่น)

@app.post("/admin/suggested-questions", dependencies=[Depends(verify_admin_session)])
async def admin_add_sq(body: SuggestedQuestionBody):  # endpoint เพิ่มคำถามแนะนำใหม่
    item = add_suggested_question(body.year.strip(), body.question.strip())  # บันทึกคำถามใหม่
    return {"message": "เพิ่มสำเร็จ", "item": item}  # คืนผลลัพธ์ที่เพิ่งเพิ่ม

# แก้ไขคำถามแนะนำที่มีอยู่แล้ว — เชื่อมกับปุ่ม "แก้ไข" ในตารางคำถามแนะนำ (upload.html/java.js)
# ที่มี UI อยู่แล้วแต่ยังไม่เคยมี endpoint นี้มาก่อน (มีแค่เพิ่ม/ลบ)
@app.put("/admin/suggested-questions/{item_id}", dependencies=[Depends(verify_admin_session)])
async def admin_update_sq(item_id: int, body: SuggestedQuestionBody):  # endpoint แก้ไขคำถามแนะนำตาม id
    year = body.year.strip()  # รุ่นใหม่ที่ต้องการตั้ง
    question = body.question.strip()  # ข้อความคำถามใหม่
    if not question:  # ห้ามคำถามว่างเปล่า
        return JSONResponse({"detail": "กรุณากรอกคำถามแนะนำ"}, status_code=400)  # ปฏิเสธ
    if year and not re.fullmatch(r"\d{2}", year):  # ถ้าระบุปีมา ต้องเป็นเลข 2 หลักเท่านั้น
        return JSONResponse({"detail": "กรุณากรอกรหัสรุ่น 2 หลัก เช่น 66 หรือเว้นว่างไว้"}, status_code=400)  # ปฏิเสธ
    item = update_suggested_question(item_id, year, question)  # แก้ไขข้อมูลในไฟล์ JSON
    if item is None:  # ไม่พบ id นี้
        return JSONResponse({"detail": "ไม่พบข้อมูล"}, status_code=404)  # คืน 404
    return {"message": "แก้ไขสำเร็จ", "item": item}  # แจ้งผลสำเร็จ

@app.delete("/admin/suggested-questions/{item_id}", dependencies=[Depends(verify_admin_session)])
async def admin_del_sq(item_id: int):  # endpoint ลบคำถามแนะนำตาม id
    if not delete_suggested_question(item_id): return JSONResponse({"detail": "ไม่พบข้อมูล"}, status_code=404)  # ไม่พบ id นี้
    return {"message": "ลบสำเร็จ"}  # ลบสำเร็จ

# นำเข้าคำถามแนะนำจากไฟล์ Excel (.xlsx) แบบยกชุด — เชื่อมกับ #sqImportBtn/#sqImportFile ใน
# upload.html/java.js ที่มี UI อยู่แล้วแต่ยังไม่เคยมี endpoint นี้มาก่อน (openpyxl ถูก import
# ไว้ตั้งแต่ต้นไฟล์แล้วแต่ไม่เคยถูกใช้งานจริงจนกระทั่งตอนนี้)
# รูปแบบไฟล์ (ตรงกับ hint ใน upload.html): คอลัมน์ A = ปีการศึกษา (เว้นว่าง = ทุกรุ่น), คอลัมน์ B = คำถามแนะนำ
@app.post("/admin/suggested-questions/import", dependencies=[Depends(verify_admin_session)])
async def admin_import_sq(file: UploadFile = File(...)):  # endpoint นำเข้าคำถามแนะนำจากไฟล์ Excel
    if openpyxl is None:  # ถ้าเซิร์ฟเวอร์ไม่ได้ติดตั้ง openpyxl ไว้
        return JSONResponse({"detail": "เซิร์ฟเวอร์ไม่ได้ติดตั้งไลบรารี openpyxl กรุณาติดต่อผู้ดูแลระบบ"}, status_code=500)  # แจ้ง error

    content = await file.read()  # อ่านเนื้อหาไฟล์ Excel ที่อัปโหลดมา
    try:
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)  # เปิดไฟล์ Excel จาก memory
        ws = wb.active  # ใช้ sheet ที่ active อยู่
    except Exception as e:  # เปิดไฟล์ไม่สำเร็จ (ไฟล์เสีย/ไม่ใช่ Excel)
        return JSONResponse({"detail": f"อ่านไฟล์ Excel ไม่สำเร็จ: {e}"}, status_code=400)  # แจ้ง error

    added, errors = 0, []  # ตัวนับที่เพิ่มสำเร็จ และรายการ error ของแต่ละแถว
    for i, row in enumerate(ws.iter_rows(min_row=1, values_only=True), start=1):  # วนอ่านทุกแถวในชีต
        if not row or len(row) < 2:  # แถวว่างหรือมีคอลัมน์ไม่ครบ
            continue  # ข้ามไป
        year_cell, question_cell = row[0], row[1]  # คอลัมน์ A=ปี, B=คำถาม
        question = str(question_cell).strip() if question_cell is not None else ""  # แปลงคำถามเป็น string ตัดช่องว่าง
        if not question:  # ไม่มีคำถามในแถวนี้
            continue  # แถวว่าง/ไม่มีคำถาม ข้ามเงียบๆ (ไม่นับเป็น error เผื่อเป็นแถวหัวตาราง)

        year = str(year_cell).strip() if year_cell is not None else ""  # แปลงค่าปีเป็น string
        # เผื่อ Excel เก็บตัวเลขเป็น float (เช่น 66.0) ให้ตัด .0 ทิ้งก่อนตรวจรูปแบบ
        if year.endswith(".0"):  # กรณี Excel เก็บเป็นทศนิยม
            year = year[:-2]  # ตัด ".0" ทิ้ง
        if year and not re.fullmatch(r"\d{2}", year):  # รูปแบบปีไม่ถูกต้อง (ไม่ใช่เลข 2 หลัก)
            errors.append(f"แถว {i}: ปีการศึกษา '{year}' ไม่ถูกต้อง (ต้องเป็นตัวเลข 2 หลัก หรือเว้นว่าง) — ข้ามแถวนี้")  # บันทึก error ของแถวนี้
            continue  # ข้ามแถวนี้ไป ไม่นำเข้า

        add_suggested_question(year, question)  # บันทึกคำถามแนะนำแถวนี้เข้าระบบ
        added += 1  # นับจำนวนที่เพิ่มสำเร็จ

    return {"message": f"นำเข้าคำถามแนะนำสำเร็จ {added} รายการ", "added": added, "errors": errors}  # สรุปผลการนำเข้าทั้งหมด

# ------------------------------------------------------------------ #
# DEVELOPER CONSOLE ENDPOINTS (สำหรับ dev.html โดยเฉพาะ)
# แก้ไขความปลอดภัย: เดิม endpoint กลุ่มนี้ไม่มีการยืนยันตัวตนเลย (ต่างจาก /admin/* ทุกตัวที่มี
# Depends(verify_admin_session) ครบ) ใครก็เข้าถึง URL เซิร์ฟเวอร์ได้ก็ดูรายชื่อผู้ใช้ทั้งหมด/
# ลบผู้ใช้/ลบเอกสารได้ทันทีโดยไม่ต้องล็อกอิน — ตอนนี้ใช้ auth เดียวกับฝั่งแอดมินทุก endpoint
# (ต้องมี Authorization: Bearer <admin_token> เหมือนกับ /admin/* — ดู dev.html ที่แก้คู่กัน
# ให้เช็ค admin_token จาก sessionStorage ก่อนเรียก endpoint เหล่านี้)
# ------------------------------------------------------------------ #
@app.get("/dev/uploads", dependencies=[Depends(verify_admin_session)])
async def dev_list_uploads():  # endpoint ดูรายชื่อไฟล์ที่อัปโหลดไว้ทั้งหมด (dev console)
    files = []  # รายการไฟล์ที่จะคืน
    if UPLOAD_DIR.exists():  # ถ้าโฟลเดอร์ uploads มีอยู่
        for p in UPLOAD_DIR.iterdir():  # วนดูทุกไฟล์ในโฟลเดอร์
            if p.is_file() and not p.name.startswith("temp_"):  # เอาเฉพาะไฟล์จริง ไม่เอาไฟล์ temp ที่ค้าง
                files.append({"filename": p.name, "size_bytes": p.stat().st_size})  # เก็บชื่อ+ขนาดไฟล์
    return {"files": files}  # คืนรายการไฟล์ทั้งหมด

@app.delete("/dev/uploads/{filename}", dependencies=[Depends(verify_admin_session)])
async def dev_delete_upload(filename: str):  # endpoint ลบไฟล์อัปโหลดจาก dev console
    fpath = UPLOAD_DIR / safe_filename(filename)  # path ไฟล์จริงบนดิสก์
    if fpath.exists(): fpath.unlink()  # ลบไฟล์ถ้ามีอยู่จริง
    rem = vector_store.delete_by_source(filename)  # ลบ chunk ที่เกี่ยวข้องใน FAISS ด้วย
    return {"message": f"ลบไฟล์และ {rem} chunks เรียบร้อยแล้ว"}  # แจ้งผลสำเร็จ

@app.get("/dev/users", dependencies=[Depends(verify_admin_session)])
async def dev_list_users():  # endpoint ดูรายชื่อผู้ใช้ทั้งหมดในระบบ (dev console)
    return {"users": list_users()}  # คืนรายชื่อ username ทั้งหมด

@app.delete("/dev/users/{username}", dependencies=[Depends(verify_admin_session)])
async def dev_delete_user(username: str):  # endpoint ลบบัญชีผู้ใช้จาก dev console
    ok, msg = delete_user(username)  # ลบผู้ใช้ตาม username
    if not ok: return JSONResponse({"detail": msg}, status_code=404)  # ไม่พบผู้ใช้นี้
    return {"message": msg}  # ลบสำเร็จ

@app.get("/dev/documents", dependencies=[Depends(verify_admin_session)])
async def dev_list_documents():  # endpoint ดูรายชื่อเอกสารทั้งหมดใน FAISS (dev console)
    return {"documents": vector_store.list_documents_detailed()}  # คืนรายชื่อเอกสารพร้อมจำนวน chunk/ปี

@app.get("/dev/documents/{source:path}/chunks", dependencies=[Depends(verify_admin_session)])
async def dev_get_chunks(source: str):  # endpoint ดูเนื้อหา chunk ดิบของเอกสารหนึ่งไฟล์ (dev console)
    chunks = vector_store.get_chunks_by_source(source)  # ดึง chunk ทั้งหมดของไฟล์นี้
    if not chunks: return JSONResponse({"detail": "ไม่พบ chunk"}, status_code=404)  # ไม่พบ chunk ของไฟล์นี้เลย
    return {"chunks": chunks}  # คืนเนื้อหา chunk ทั้งหมด

# --- ทดสอบเปรียบเทียบโมเดล LLM (สำหรับผู้เชี่ยวชาญ/ผู้พัฒนาเท่านั้น) ---
# แยกขาดจาก /api/chat/stream ที่นักศึกษาใช้จริงโดยสิ้นเชิง ไม่แตะ OLLAMA_MODEL ค่าเริ่มต้น
# ไม่บันทึกประวัติแชท และต้องผ่าน verify_admin_session เหมือน /dev/* ทุกตัว จึงไม่กระทบผู้ใช้จริง
# หมายเหตุ: _list_ollama_models() ด้านล่างนี้ใช้ร่วมกับ /api/models และ api_chat_stream ด้านบน
# ด้วย (ฟีเจอร์เลือกโมเดลในหน้าแชทจริงสำหรับอาจารย์/บุคลากร) ไม่ได้ใช้เฉพาะ /dev/* แล้ว
def _list_ollama_models():  # ดึงรายชื่อโมเดลที่ติดตั้งไว้บนเครื่อง Ollama
    resp = _ollama_client.list()  # เรียก Ollama API ขอรายการโมเดล
    items = resp.get("models") if isinstance(resp, dict) else getattr(resp, "models", [])  # รองรับทั้งรูปแบบ dict และ object ของ ollama-python แต่ละเวอร์ชัน
    names = []  # รายชื่อโมเดลที่จะคืน
    for m in items or []:  # วนดูแต่ละโมเดลที่ได้
        name = (m.get("model") if isinstance(m, dict) else getattr(m, "model", None)) \
            or (m.get("name") if isinstance(m, dict) else getattr(m, "name", None))  # ดึงชื่อโมเดล (คีย์ต่างกันไปตามเวอร์ชัน)
        if name: names.append(name)  # เก็บเฉพาะชื่อที่ดึงได้จริง
    return names  # คืนรายชื่อโมเดลทั้งหมด

class DevChatTestBody(BaseModel):  # โครงสร้างข้อมูลคำขอทดสอบโมเดล
    message: str = ""; model: str = ""; role: str = "student"; year: str = ""  # คำถามทดสอบ, โมเดลที่เลือก, บทบาท/ชั้นปีสำหรับกรองข้อมูลอ้างอิง

@app.get("/dev/models", dependencies=[Depends(verify_admin_session)])
async def dev_list_models():  # endpoint คืนรายชื่อโมเดลที่เลือกทดสอบได้ (dev console)
    try:
        return {"models": _list_ollama_models(), "active_default": OLLAMA_MODEL}  # คืนรายชื่อโมเดล พร้อมบอกว่าตัวไหนคือค่าเริ่มต้นของระบบจริง
    except Exception as e:
        return JSONResponse({"detail": f"เชื่อมต่อ Ollama ไม่ได้: {e}"}, status_code=502)  # Ollama ไม่ตอบสนอง

@app.post("/dev/chat-test/stream", dependencies=[Depends(verify_admin_session)])
async def dev_chat_test_stream(body: DevChatTestBody):  # endpoint ทดสอบถามคำถามด้วยโมเดลที่เลือก (แยกจากแชทจริง)
    q = body.message.strip()  # ตัดช่องว่างหัวท้ายคำถาม
    if not q: return JSONResponse({"detail": "ข้อความว่างเปล่า"}, status_code=400)  # กันคำถามว่าง
    model = body.model.strip() or OLLAMA_MODEL  # ถ้าไม่ระบุโมเดล ใช้ค่าเริ่มต้นของระบบ
    try:
        available = _list_ollama_models()  # เช็กว่ามีโมเดลนี้ติดตั้งจริงไหม
        if available and model not in available:
            return JSONResponse({"detail": f"ไม่พบโมเดล '{model}' บนเครื่อง Ollama"}, status_code=400)  # กันชื่อโมเดลมั่ว/ไม่ได้ติดตั้ง
    except Exception:
        pass  # ต่อ Ollama ไม่ได้ตอน list ก็ปล่อยให้ chat ด้านล่างรายงาน error เองแทน

    chunks = retrieve_chunks(q, body.role.strip() or "student", body.year.strip())  # ดึงข้อมูลอ้างอิงเหมือนแชทจริงทุกประการ

    def generate():  # generator สำหรับสตรีมคำตอบทีละ token กลับไปยัง dev.html
        try:
            for part in _ollama.chat(model=model, messages=_build_messages(q, chunks),
                                      options={"num_ctx": OLLAMA_NUM_CTX}, stream=True, keep_alive=0):  # ยิงคำถามเข้าโมเดลที่เลือกทดสอบ
                c = part["message"]["content"]  # เนื้อหา token ที่โมเดลตอบกลับมา
                if c: yield f"data: {json.dumps({'type':'token','content':c}, ensure_ascii=False)}\n\n"  # ส่ง token ออกไปทีละชิ้นแบบ SSE
        except Exception as e:
            yield f"data: {json.dumps({'type':'error','message':str(e)})}\n\n"  # เกิดข้อผิดพลาดระหว่างเรียกโมเดล แจ้งกลับไปหน้าเว็บ
        yield f"data: {json.dumps({'type':'done'})}\n\n"  # แจ้งว่าสตรีมจบแล้ว

    return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})  # ส่งกลับเป็นสตรีม SSE เหมือนแชทจริง

if __name__ == "__main__":  # ถ้ารันไฟล์นี้ตรงๆ (ไม่ได้ import จากที่อื่น)
    import uvicorn  # โมดูล server สำหรับรัน FastAPI
    uvicorn.run(app, host="0.0.0.0", port=8000)  # สตาร์ทเซิร์ฟเวอร์ที่พอร์ต 8000 เปิดรับทุก interface