import os, json, re, traceback, hashlib, threading, secrets, time, unicodedata
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, Request, HTTPException, Depends, Form
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# werkzeug.utils.secure_filename() ตัดอักขระที่ไม่ใช่ ASCII ทิ้งทั้งหมด รวมถึงภาษาไทย
# เช่น secure_filename('คู่มือกิจกรรมนักศึกษา.pdf') -> 'pdf' (นามสกุลไฟล์หายไปเพราะ
# ชื่อไฟล์ทั้งหมดที่เหลืออยู่คือคำว่า pdf เอง) ทำให้การอัปโหลดไฟล์ชื่อภาษาไทยล้มเหลวเสมอ
# ระบบนี้ใช้ชื่อไฟล์ภาษาไทยเป็นหลัก จึงต้องเขียนฟังก์ชันกันชื่อไฟล์เองแทน โดยยังคง
# อักษรไทย/ยูนิโค้ดไว้ และกันเฉพาะสิ่งที่อันตรายจริง (path traversal, อักขระต้องห้ามในชื่อไฟล์)
def safe_filename(filename: str) -> str:
    filename = os.path.basename(filename or "")            # กัน path traversal เช่น ../../etc/passwd
    filename = unicodedata.normalize("NFC", filename)       # รวมสระ/วรรณยุกต์ไทยให้เป็นรูปแบบเดียว
    filename = filename.replace("\x00", "")
    filename = re.sub(r'[\\/:*?"<>|\r\n\t]', "_", filename) # อักขระต้องห้ามในชื่อไฟล์ (Windows/Unix)
    filename = filename.strip(" .")                        # กันชื่อไฟล์ขึ้น/ลงท้ายด้วยจุดหรือช่องว่าง
    return filename or "unnamed_file"

# ------------------------------------------------------------------ #
# CONFIG
# ------------------------------------------------------------------ #
BASE_DIR   = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
VS_DIR     = BASE_DIR / "vector_store"
FAISS_PATH = str(VS_DIR / "faiss_index")
USERS_FILE = BASE_DIR / "users.json"
ADMIN_CONFIG_FILE = BASE_DIR / "admin_config.json"  # เก็บ email + password hash ของแอดมินคนเดียว

UPLOAD_DIR.mkdir(exist_ok=True)
VS_DIR.mkdir(exist_ok=True)
(BASE_DIR / "static_assets").mkdir(exist_ok=True)  # กัน StaticFiles mount error ถ้าโฟลเดอร์นี้ยังไม่มี

EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
OLLAMA_MODEL    = "gemma3:4b"
OLLAMA_HOST     = "http://localhost:11434"
CHUNK_SIZE      = 500
CHUNK_OVERLAP   = 80
TOP_K           = 8
ALLOWED_EXT     = {".pdf", ".txt", ".docx", ".md"}

SYSTEM_PROMPT = """คุณคือเจ้าหน้าที่ฝ่ายกิจการนักศึกษาที่ตอบคำถามนักศึกษาโดยใช้ข้อมูลอ้างอิงที่ให้มาเท่านั้น
- ตอบเหมือนเจ้าหน้าที่มืออาชีพที่รู้เรื่องนี้อยู่แล้วโดยตรง ห้ามพูดถึงที่มาของข้อมูลเด็ดขาด
  เช่น ห้ามพูดว่า "จากเอกสาร...", "ตามคู่มือระบุว่า...", "จากไฟล์...", "ตามข้อมูลอ้างอิง..."
  หรือกล่าวถึงชื่อไฟล์/ชื่อเอกสารใดๆ ทั้งสิ้น ให้ตอบเนื้อหาตรงๆ เหมือนรู้อยู่แล้วเอง
- ตอบให้ตรงกับสิ่งที่ถูกถามจริงๆ ถ้าถามเรื่องขั้นตอน/วิธีการ ให้อธิบายขั้นตอนหรือวิธีการ
  ไม่ใช่แค่ยกนิยามทั่วไปมาแปะ ถ้าถามเรื่องกฎ/ระเบียบ ให้ตอบกฎ/ระเบียบที่เกี่ยวข้องกับ
  คำถามนั้นโดยตรง ไม่ตอบนอกประเด็นหรือใส่ข้อมูลที่ไม่เกี่ยวข้อง
- ถ้าข้อมูลอ้างอิงไม่มีคำตอบที่ตรงกับคำถาม ให้ตอบตามตรงว่าไม่พบข้อมูลนี้ในระบบ และแนะนำให้
  ติดต่อฝ่ายกิจการนักศึกษาโดยตรง อย่าแต่งคำตอบขึ้นเอง
- ตอบเป็นภาษาเดียวกับคำถามของผู้ใช้เท่านั้น (ผู้ใช้ส่วนใหญ่ถามเป็นภาษาไทย)
- ห้ามสลับหรือปนภาษาอื่นในคำตอบโดยเด็ดขาด ไม่ว่ากรณีใดก็ตาม (เช่น ห้ามมีตัวอักษรจีน
  หรือภาษาอังกฤษปนอยู่กลางคำตอบภาษาไทย ยกเว้นคำศัพท์เฉพาะที่ไม่มีคำแปลไทยจริงๆ)
  ถ้าพบว่ากำลังจะพิมพ์ภาษาอื่นนอกจากภาษาของคำถาม ให้เปลี่ยนกลับมาพิมพ์เป็นภาษาเดียวกับ
  คำถามทันที
- ตอบให้กระชับ ชัดเจน เป็นทางการ และตรงประเด็น
-เมื่อผู้ใช้ถามเป็นภาษาไทยให้ตอบเป็นภาษไทย
-เรียบเรียงข้อความรูปแบบการตอบคำถามให้เข้าใจง่าย
"""

# ------------------------------------------------------------------ #
# VECTOR STORE
# ------------------------------------------------------------------ #
import faiss, numpy as np
from sentence_transformers import SentenceTransformer

class VectorStore:
    def __init__(self):
        print(f"[VectorStore] โหลด embedding model: {EMBEDDING_MODEL}")
        self.embedder  = SentenceTransformer(EMBEDDING_MODEL)
        self.dimension = self.embedder.get_sentence_embedding_dimension()
        self.index: faiss.Index | None = None
        self.metadata: list[dict] = []
        self._lock = threading.Lock()
        self._load_or_create()

    def _load_or_create(self):
        idx_f  = FAISS_PATH + ".index"
        meta_f = FAISS_PATH + ".meta.npy"
        if os.path.exists(idx_f) and os.path.exists(meta_f):
            print("[VectorStore] พบ index เดิม กำลังโหลด...")
            self.index    = faiss.read_index(idx_f)
            self.metadata = np.load(meta_f, allow_pickle=True).tolist()
            print(f"[VectorStore] โหลดสำเร็จ {len(self.metadata)} chunks")
        else:
            print("[VectorStore] ไม่พบ index เดิม สร้างใหม่")
            self.index    = faiss.IndexFlatIP(self.dimension)
            self.metadata = []

    def _embed(self, texts):
        v = self.embedder.encode(texts, convert_to_numpy=True,
                                  normalize_embeddings=True, show_progress_bar=False)
        return v.astype("float32")

    def _save(self):
        faiss.write_index(self.index, FAISS_PATH + ".index")
        np.save(FAISS_PATH + ".meta.npy", np.array(self.metadata, dtype=object))

    def add_chunks(self, chunks: list[dict]) -> int:
        if not chunks: return 0
        vectors = self._embed([c["text"] for c in chunks])
        with self._lock:
            self.index.add(vectors)
            self.metadata.extend(chunks)
            self._save()
        return len(chunks)

    def search(self, query: str, top_k: int = TOP_K) -> list[dict]:
        if self.index.ntotal == 0: return []
        qv = self._embed([query])
        scores, indices = self.index.search(qv, min(top_k, self.index.ntotal))
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1: continue
            item = dict(self.metadata[idx])
            item["score"] = float(score)
            results.append(item)
        return results

    def stats(self) -> dict:
        sources = sorted(set(m["source"] for m in self.metadata))
        return {"total_chunks": len(self.metadata),
                "total_documents": len(sources), "sources": sources}

    def available_years(self) -> set[str]:
        """คืนชุดรหัสรุ่น (2 หลัก) ที่มีเอกสารติด year นี้อยู่จริงใน vector store
        ไม่รวมเอกสารกลางที่ year ว่าง (เพราะเอกสารกลางไม่ใช่ 'รุ่น' ใดรุ่นหนึ่งโดยเฉพาะ)"""
        return {m["year"] for m in self.metadata if m.get("year")}

    def clear(self):
        with self._lock:
            self.index    = faiss.IndexFlatIP(self.dimension)
            self.metadata = []
            self._save()

    # --- methods ที่ app.py เรียกใช้แต่ยังไม่มีใน vector_store.py เดิม ---
    def delete_by_source(self, source: str) -> int:
        """ลบ chunk ทั้งหมดของไฟล์นี้ออกจาก index แล้ว rebuild"""
        with self._lock:
            keep = [m for m in self.metadata if m["source"] != source]
            removed = len(self.metadata) - len(keep)
            if removed == 0:
                return 0
            self.index    = faiss.IndexFlatIP(self.dimension)
            self.metadata = []
            if keep:
                vectors = self._embed([m["text"] for m in keep])
                self.index.add(vectors)
                self.metadata = keep
            self._save()
        return removed

    def list_documents_detailed(self) -> list[dict]:
        counts: dict[str, int] = {}
        years:  dict[str, str] = {}
        for m in self.metadata:
            counts[m["source"]] = counts.get(m["source"], 0) + 1
            if m.get("year"):
                years[m["source"]] = m["year"]
        return [{"source": s, "chunk_count": c, "year": years.get(s, "")}
                for s, c in sorted(counts.items())]

    def set_year_for_source(self, source: str, year: str) -> int:
        """แก้ปีของไฟล์ที่อัปโหลดไว้แล้ว (ใช้กับไฟล์เก่าที่อัปโหลดก่อนมีฟีเจอร์แยกปี
        โดยไม่ต้องอัปโหลดไฟล์ใหม่ซ้ำ) คืนค่าจำนวน chunk ที่ถูกแก้"""
        with self._lock:
            updated = 0
            for m in self.metadata:
                if m["source"] == source:
                    m["year"] = year
                    updated += 1
            if updated:
                self._save()
        return updated

    def get_chunks_by_source(self, source: str) -> list[dict]:
        return [{"index": i, "text": m["text"]}
                for i, m in enumerate(self.metadata) if m["source"] == source]

vector_store = VectorStore()

# ------------------------------------------------------------------ #
# DOCUMENT LOADER
# ------------------------------------------------------------------ #
from pypdf import PdfReader
import docx as _docx
# LangChain >= 0.1 ย้าย RecursiveCharacterTextSplitter ไปแพ็กเกจแยก langchain_text_splitters
# (ของเดิม import จาก langchain.text_splitter ใช้ไม่ได้แล้วกับ LangChain เวอร์ชันใหม่)
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter

def _read_pdf(path): return "\n".join(p.extract_text() or "" for p in PdfReader(path).pages)
def _read_docx(path): return "\n".join(p.text for p in _docx.Document(path).paragraphs)
def _read_txt(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f: return f.read()

def load_text(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":  text = _read_pdf(path)
    elif ext == ".docx": text = _read_docx(path)
    elif ext in (".txt", ".md"): text = _read_txt(path)
    else: raise ValueError(f"ไม่รองรับไฟล์ประเภทนี้: {ext}")
    # PDF ภาษาไทย (โดยเฉพาะที่ทำจากการสแกน/OCR) มักดึงข้อความออกมาโดยสระ/วรรณยุกต์
    # ไม่รวมกับพยัญชนะเป็นรูปเดียว (unicode ที่ยังไม่ normalize) ทำให้ embedding ของ chunk
    # ต่างจาก embedding ของคำถามที่ผู้ใช้พิมพ์ปกติ (ซึ่งอยู่ในรูป NFC) อย่างมีนัยสำคัญ
    # ส่งผลให้ค้นหาไม่เจอเนื้อหาที่มีอยู่จริง จึงต้อง normalize เป็น NFC ก่อนตัด chunk เสมอ
    # (ใช้หลักการเดียวกับ safe_filename() ด้านบนที่ทำกับชื่อไฟล์อยู่แล้ว)
    return unicodedata.normalize("NFC", text)

def split_chunks(text: str, source: str, year: str = "") -> list[dict]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", ".", " ", ""])
    # year = ปีการศึกษา พ.ศ. 4 หลัก (เช่น "2566") ที่แอดมินกรอกตอนอัปโหลด
    # เก็บเป็นฟิลด์ metadata ของ chunk โดยตรง แทนการเดาจากชื่อไฟล์ตอนค้นหา
    # ถ้าเว้นว่างไว้ = เอกสารกลาง ให้ทุกรุ่นเห็นเหมือนกัน
    return [{"text": c, "source": source, "year": year} for c in splitter.split_text(text) if c.strip()]

def process_file(path: str, year: str = "") -> list[dict]:
    source = os.path.basename(path)
    text   = load_text(path)
    if not text.strip():
        raise ValueError(f"ไม่พบข้อความในไฟล์: {source}")
    return split_chunks(text, source, year)

# ------------------------------------------------------------------ #
# LLM CLIENT (Ollama)
# ------------------------------------------------------------------ #
import ollama as _ollama

def _build_messages(question: str, chunks: list[dict], history: list[dict] = None):
    # หมายเหตุ: เดิม ctx ใส่ label "[แหล่งที่มา: ชื่อไฟล์]" นำหน้าทุก chunk เพื่อ debug
    # แต่ทำให้ LLM เห็นชื่อไฟล์แล้วเผลอพูดถึงชื่อไฟล์/เอกสารในคำตอบ (เช่น "จากเอกสาร
    # คู่มือกิจกรรมนักศึกษา 66.pdf ...") ซึ่งไม่เป็นธรรมชาติสำหรับผู้ใช้ปลายทาง จึงตัด
    # label ออกจากสิ่งที่ส่งให้ LLM เห็น (ชื่อไฟล์จริงยังคงส่งกลับใน field "sources"
    # ของ response แยกต่างหากสำหรับ debug/dev console ตามเดิม ไม่กระทบส่วนนั้น)
    ctx = "\n\n---\n\n".join(c["text"] for c in chunks) \
          if chunks else "(ไม่พบข้อมูลที่เกี่ยวข้องในระบบ)"
    user_msg = f"ข้อมูลอ้างอิงภายใน (ห้ามเอ่ยถึงคำว่า 'ข้อมูลอ้างอิง' หรือที่มาของข้อมูลนี้ในคำตอบ):\n{ctx}\n\nคำถามจากนักศึกษา: {question}\n\nตอบคำถามข้างต้นโดยใช้ข้อมูลอ้างอิงนี้ ตอบตรงประเด็นเหมือนเจ้าหน้าที่ตอบเอง"
    msgs = [{"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_msg}]
    if history:
        msgs = [msgs[0]] + list(history) + [msgs[1]]
    return msgs

def ask_llm(question, chunks, history=None):
    r = _ollama.chat(model=OLLAMA_MODEL, messages=_build_messages(question, chunks, history))
    return r["message"]["content"]

def ask_llm_stream(question, chunks, history=None):
    for part in _ollama.chat(model=OLLAMA_MODEL,
                              messages=_build_messages(question, chunks, history),
                              stream=True):
        c = part["message"]["content"]
        if c: yield c

def check_ollama():
    try:
        names = [m["model"] for m in _ollama.list().get("models", [])]
        if any(OLLAMA_MODEL in n for n in names):
            return True, f"พร้อมใช้งาน (พบโมเดล: {names})"
        return False, f"Ollama รันอยู่ แต่ไม่พบโมเดล '{OLLAMA_MODEL}'. รัน: ollama pull {OLLAMA_MODEL}"
    except Exception as e:
        return False, f"เชื่อมต่อ Ollama ไม่ได้: {e}"

# ------------------------------------------------------------------ #
# AUTH
# ------------------------------------------------------------------ #
_auth_lock = threading.Lock()

def _hash(pw): return hashlib.sha256(pw.encode()).hexdigest()

def _load_users():
    if not USERS_FILE.exists(): return {}
    try:
        return json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except: return {}

def _save_users(u):
    USERS_FILE.write_text(json.dumps(u, ensure_ascii=False, indent=2), encoding="utf-8")

def register_user(username, password):
    if not username or not password: return False, "กรุณากรอกข้อมูลให้ครบถ้วน"
    with _auth_lock:
        u = _load_users()
        if username in u: return False, "มีบัญชีนี้อยู่แล้ว กรุณาเข้าสู่ระบบ"
        u[username] = _hash(password); _save_users(u)
    return True, "สมัครสมาชิกสำเร็จ"

def login_user(username, password):
    if not username or not password: return False, "กรุณากรอกข้อมูลให้ครบถ้วน"
    with _auth_lock:
        u = _load_users()
        if username not in u:
            return False, "ไม่พบรหัสนี้ในระบบ กรุณาติดต่อผู้ดูแลระบบ"
        if u[username] != _hash(password): return False, "รหัสผ่านไม่ถูกต้อง"
    return True, "เข้าสู่ระบบสำเร็จ"


# ------------------------------------------------------------------ #
# ADMIN ACCOUNT — อนุญาตให้มีผู้ดูแลระบบได้ "เพียงบัญชีเดียวเท่านั้น" ตามที่กำหนดไว้
# ไม่ผูกกับ users.json (ของผู้ใช้ทั่วไป/นักศึกษา) และปิดการลงทะเบียนเพิ่มจากหน้าเว็บถาวร
# (ดู /admin/register ด้านล่าง)
#
# ค่าเริ่มต้น: อีเมล admin@gmail.com / รหัสผ่าน 123456 — เก็บเป็น "password hash" ไว้ใน
# admin_config.json (ไฟล์ถูกสร้างอัตโนมัติตอนรันครั้งแรกถ้ายังไม่มี) ไม่ใช่ plain text ในซอร์สโค้ด
#
# ลืมรหัสผ่าน? รันคำสั่งนี้บนเครื่อง/เซิร์ฟเวอร์ที่รันระบบอยู่ (ต้องมีสิทธิ์เข้าถึงไฟล์เซิร์ฟเวอร์
# เท่านั้น จึงจะรีเซ็ตได้ — เป็นไปตามหลักการที่ว่ามีผู้ดูแลระบบได้เพียงคนเดียว):
#     python reset_admin_password.py you-new-password
# ดูรายละเอียดเพิ่มเติมในไฟล์ reset_admin_password.py
# ------------------------------------------------------------------ #
DEFAULT_ADMIN_EMAIL    = "admin@gmail.com"
DEFAULT_ADMIN_PASSWORD = "123456"

def _default_admin_config():
    return {"email": DEFAULT_ADMIN_EMAIL, "password_hash": _hash(DEFAULT_ADMIN_PASSWORD)}

def _save_admin_config(cfg):
    ADMIN_CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

def _load_admin_config():
    if not ADMIN_CONFIG_FILE.exists():
        cfg = _default_admin_config()
        _save_admin_config(cfg)
        return cfg
    try:
        cfg = json.loads(ADMIN_CONFIG_FILE.read_text(encoding="utf-8"))
        if "email" not in cfg or "password_hash" not in cfg:
            raise ValueError("invalid admin_config.json")
        return cfg
    except Exception:
        traceback.print_exc()
        # ไฟล์ config เสีย/อ่านไม่ได้ -> ใช้ค่าเริ่มต้นแทนแทนที่จะทำให้เข้าระบบไม่ได้เลย
        return _default_admin_config()

# กันบรูทฟอร์ซรหัสผ่านแบบง่ายๆ: ล็อกอินผิดติดกันเกินกำหนดจาก IP เดียวกัน ต้องรอสักพัก
_admin_login_attempts = {}          # ip -> {"count": int, "locked_until": unix_ts}
_admin_login_attempts_lock = threading.Lock()
ADMIN_MAX_ATTEMPTS  = 5
ADMIN_LOCKOUT_SECONDS = 5 * 60       # ล็อก 5 นาทีถ้าใส่รหัสผิดเกิน 5 ครั้งติดกัน

def _admin_lockout_check(ip: str):
    with _admin_login_attempts_lock:
        rec = _admin_login_attempts.get(ip)
        if rec and rec["locked_until"] > time.time():
            wait_min = int((rec["locked_until"] - time.time()) // 60) + 1
            return False, f"ใส่รหัสผ่านผิดหลายครั้งเกินไป กรุณารออีกประมาณ {wait_min} นาทีแล้วลองใหม่"
    return True, ""

def _admin_lockout_register_result(ip: str, success: bool):
    with _admin_login_attempts_lock:
        if success:
            _admin_login_attempts.pop(ip, None)
            return
        rec = _admin_login_attempts.setdefault(ip, {"count": 0, "locked_until": 0})
        rec["count"] += 1
        if rec["count"] >= ADMIN_MAX_ATTEMPTS:
            rec["locked_until"] = time.time() + ADMIN_LOCKOUT_SECONDS
            rec["count"] = 0

def admin_login_user(username, password):
    if not username or not password: return False, "กรุณากรอกข้อมูลให้ครบถ้วน"
    cfg = _load_admin_config()
    email_ok = secrets.compare_digest(username.strip().lower(), cfg["email"].strip().lower())
    pass_ok  = secrets.compare_digest(_hash(password), cfg["password_hash"])
    if not (email_ok and pass_ok):
        return False, "อีเมลหรือรหัสผ่านไม่ถูกต้อง"
    return True, "เข้าสู่ระบบสำเร็จ"

def list_users():
    with _auth_lock: return sorted(_load_users().keys())

# ------------------------------------------------------------------ #
# ROSTER (รายชื่อนักศึกษา/บุคลากรจริงจากฝ่ายทะเบียน) — ฟีเจอร์ทางเลือก (opt-in)
# วางไฟล์ students_roster.json ไว้ข้างๆ main.py รูปแบบ: ["66122160111", "67122160101", ...]
# ถ้าไม่มีไฟล์นี้ ระบบทำงานเหมือนเดิมทุกอย่าง (ใครก็สมัครได้ด้วยรหัสที่ format ถูก)
# ถ้ามีไฟล์นี้ ระบบจะเช็ครหัสกับรายชื่อจริงก่อนอนุญาตให้สมัคร/เข้าใช้งาน
# ------------------------------------------------------------------ #
ROSTER_FILE = BASE_DIR / "students_roster.json"

def _load_roster() -> set[str] | None:
    if not ROSTER_FILE.exists():
        return None  # ยังไม่มีไฟล์รายชื่อ = ปิดการตรวจสอบนี้ไว้ก่อน (ทำงานแบบเดิม)
    try:
        return set(json.loads(ROSTER_FILE.read_text(encoding="utf-8")))
    except Exception:
        traceback.print_exc()
        return None  # ไฟล์เสีย/อ่านไม่ได้ → ปิดการตรวจสอบชั่วคราว ดีกว่าทำให้ทุกคน login ไม่ได้

def is_code_in_roster(code: str) -> bool:
    roster = _load_roster()
    if roster is None:
        return True  # ยังไม่ได้ตั้งค่ารายชื่อ → ไม่บล็อกใคร (พฤติกรรมเดิม)
    return code in roster

def extract_student_year(code: str) -> str | None:
    """คืนรหัสรุ่น 2 หลักถ้าเป็นรหัสนักศึกษา (ตัวเลข 11 หลัก), หรือ None ถ้าไม่ใช่
    (เช่น รหัสบุคลากร/อาจารย์ 5 หลัก ซึ่งไม่ผูกกับรุ่นใดรุ่นหนึ่ง)"""
    return code[:2] if len(code) == 11 and code.isdigit() else None

def delete_user(username):
    with _auth_lock:
        u = _load_users()
        if username not in u: return False, "ไม่พบบัญชีนี้"
        del u[username]; _save_users(u)
    return True, "ลบบัญชีสำเร็จ"

# ------------------------------------------------------------------ #
# CHAT MEMORY
# เก็บไว้ใน memory เหมือนเดิมสำหรับความเร็ว (อ่าน/เขียนระหว่างแชทไม่ต้องแตะดิสก์)
# แต่สำรองลงไฟล์ทุกครั้งที่มีข้อความใหม่ ("history/<session_id>.json") เพื่อกัน
# ประวัติหายตอน restart server — ตอนเรียก get_history() ถ้า memory ไม่มี (เช่น
# server เพิ่ง restart) จะลองโหลดจากไฟล์ก่อนคืนค่า list ว่าง
# ------------------------------------------------------------------ #
_sessions: dict[str, list] = {}
_mem_lock = threading.Lock()
MAX_HIST  = 20
HISTORY_DIR = BASE_DIR / "chat_history"
HISTORY_DIR.mkdir(exist_ok=True)

def _history_path(sid: str) -> Path:
    # กัน path traversal จาก session_id (เผื่อมีคนส่ง id แปลกๆ เช่น "../../etc")
    return HISTORY_DIR / f"{safe_filename(sid)}.json"

def _load_history_from_disk(sid: str) -> list:
    p = _history_path(sid)
    if not p.exists(): return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []  # ไฟล์เสีย/อ่านไม่ได้ ไม่ทำให้แชทพัง แค่เริ่มประวัติใหม่

def _save_history_to_disk(sid: str, h: list):
    try:
        _history_path(sid).write_text(json.dumps(h, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        traceback.print_exc()  # เขียนดิสก์ไม่สำเร็จ ไม่ทำให้ request ทั้งหมด error

def get_history(sid):
    with _mem_lock:
        if sid not in _sessions:
            _sessions[sid] = _load_history_from_disk(sid)  # server เพิ่ง restart → กู้จากไฟล์
        return list(_sessions[sid])

def append_exchange(sid, q, a):
    with _mem_lock:
        h = _sessions.setdefault(sid, [])
        h += [{"role":"user","content":q},{"role":"assistant","content":a}]
        if len(h) > MAX_HIST: del h[:len(h)-MAX_HIST]
        h_copy = list(h)
    _save_history_to_disk(sid, h_copy)  # เขียนดิสก์นอก lock กันบล็อก thread อื่นนาน

def reset_session(sid):
    with _mem_lock: _sessions.pop(sid, None)
    _history_path(sid).unlink(missing_ok=True)

# ------------------------------------------------------------------ #
# FastAPI APP
# ------------------------------------------------------------------ #
@asynccontextmanager
async def lifespan(app: FastAPI):
    ok, msg = check_ollama()
    print("=" * 60)
    print("RAG Chatbot — FastAPI")
    print(f"Embedding : {EMBEDDING_MODEL}")
    print(f"LLM       : {OLLAMA_MODEL} (Ollama)")
    print(f"Ollama    : {msg}")
    print(f"Frontend  : http://localhost:8000/")
    print("=" * 60)
    yield

app = FastAPI(title="RAG Chatbot", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

# Serve static files (CSS, JS, images)  — ต้องมาก่อน route อื่น
# เปลี่ยนจาก directory=str(BASE_DIR)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static_assets")), name="static")

# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #
def _allowed(filename): return os.path.splitext(filename)[1].lower() in ALLOWED_EXT
def ok(data): return JSONResponse(content=data)
def err(msg, code=400): return JSONResponse(content={"detail": msg, "error": msg}, status_code=code)

# จำกัดสิทธิ์เข้าถึง /dev/* และหน้า dev.html ให้เฉพาะเครื่อง localhost เท่านั้น
# (ผู้พัฒนาที่นั่งอยู่หน้า server) กันคนนอกเรียกมาดู/ลบข้อมูลดิบได้โดยตรง
# หมายเหตุ: ถ้า deploy หลัง reverse proxy (nginx) request.client.host อาจกลายเป็น
# IP ของ proxy เอง ต้องตั้งค่า proxy ให้ forward X-Forwarded-For และปรับเช็คตรงนี้เพิ่ม
_LOCALHOST_IPS = {"127.0.0.1", "::1", "localhost"}

def verify_localhost(request: Request):
    client_host = request.client.host if request.client else None
    if client_host not in _LOCALHOST_IPS:
        raise HTTPException(403, "เข้าถึงหน้านี้ได้เฉพาะจากเครื่อง server (localhost) เท่านั้น")

def _guess_year_from_filename(filename: str) -> str:
    """เดารหัสรุ่น 2 หลักจากชื่อไฟล์ เช่น 'คู่มือกิจกรรมนักศึกษา 66.pdf' -> '66'
    หาเลข 2 หลักที่ไม่ติดกับตัวเลขอื่นๆ (กันไปแมตช์เลขยาวๆ ที่ไม่เกี่ยวข้อง เช่น รหัสเอกสาร)
    ถ้าเจอหลายตำแหน่งเอาตำแหน่งท้ายสุดก่อนนามสกุลไฟล์ เพราะเป็นรูปแบบที่พบบ่อยที่สุด
    ถ้าไม่เจอเลย คืนค่าว่าง (ไฟล์นั้นจะกลายเป็นเอกสารกลางที่ทุกรุ่นเห็น)"""
    name = os.path.splitext(filename)[0]
    matches = re.findall(r'(?<!\d)(\d{2})(?!\d)', name)
    return matches[-1] if matches else ""

# ------------------------------------------------------------------ #
# Serve HTML pages
# ------------------------------------------------------------------ #
def _html(name: str):
    p = BASE_DIR / name
    if p.exists(): return FileResponse(str(p), media_type="text/html")
    raise HTTPException(404, f"ไม่พบไฟล์ {name}")

# ------------------------------------------------------------------ #
# Pydantic models
# ------------------------------------------------------------------ #
class ChatBody(BaseModel):
    message:    str = ""
    history:    list = []
    session_id: str = "guest"
    role:       str = "student"
    year:       str = ""

class ChatSimpleBody(BaseModel):
    question:   str = ""
    session_id: str = "guest"
    role:       str = "student"
    year:       str = ""

class LoginBody(BaseModel):
    username: str = ""
    password: str = ""

@app.get("/",               response_class=HTMLResponse)
async def root():            return _html("pang.html")
@app.get("/user.html")
async def page_user():       return _html("user.html")
@app.get("/chatbot.html")
async def page_chatbot():    return _html("chatbot.html")
@app.get("/loginadmin.html")
async def page_loginadmin(): return _html("loginadmin.html")
@app.get("/admin.html")
async def page_admin():      return _html("admin.html")
@app.get("/upload.html")
async def page_upload():     return _html("upload.html")
@app.get("/index.html")
async def page_index():      return _html("index.html")
@app.get("/dev.html", dependencies=[Depends(verify_localhost)])
async def page_dev():        return _html("dev.html")
@app.get("/pang.html")
async def page_pang():       return _html("pang.html")
@app.get("/style.css")
async def css(): return FileResponse(str(BASE_DIR / "style.css"), media_type="text/css")
@app.get("/java.js")
async def js():  return FileResponse(str(BASE_DIR / "java.js"),   media_type="application/javascript")
@app.get("/mascot.png")
async def mascot(): return FileResponse(str(BASE_DIR / "mascot.png"), media_type="image/png")


# ------------------------------------------------------------------ #
# Health
# ------------------------------------------------------------------ #
@app.get("/api/health")
async def health():
    ok_flag, msg = check_ollama()
    return {"status": "ok",
            "vector_store": vector_store.stats(),
            "ollama": {"connected": ok_flag, "message": msg, "model": OLLAMA_MODEL}}

# ------------------------------------------------------------------ #
# Upload  /api/upload  (ใช้โดย index.html)
# ------------------------------------------------------------------ #
@app.post("/api/upload")
async def api_upload(file: UploadFile = File(...)):
    if not file.filename: return err("ไม่ได้เลือกไฟล์")
    if not _allowed(file.filename):
        return err(f"ไม่รองรับไฟล์ประเภทนี้ รองรับ: {', '.join(ALLOWED_EXT)}")
    filename = safe_filename(file.filename)
    fpath    = str(UPLOAD_DIR / filename)
    content  = await file.read()
    with open(fpath, "wb") as f: f.write(content)
    try:
        chunks = process_file(fpath); n = vector_store.add_chunks(chunks)
        return ok({"message": f"อัปโหลด '{filename}' สำเร็จ",
                   "filename": filename, "chunks_added": n,
                   "vector_store": vector_store.stats()})
    except Exception as e:
        traceback.print_exc()
        if os.path.exists(fpath): os.remove(fpath)
        return err(f"ประมวลผลไฟล์ล้มเหลว: {e}", 500)

# ------------------------------------------------------------------ #
# Documents
# ------------------------------------------------------------------ #
@app.get("/api/documents")
async def api_docs(): return vector_store.stats()

@app.post("/api/documents/clear")
async def api_clear():
    vector_store.clear()
    return {"message": "ล้างเอกสารทั้งหมดใน vector store แล้ว"}

# ------------------------------------------------------------------ #
# Chat  /api/chat  (ใช้โดย index.html)
# ------------------------------------------------------------------ #
@app.post("/api/chat")
async def api_chat(body: ChatSimpleBody):
    q = body.question.strip()
    if not q: return err("กรุณาส่งข้อความคำถาม")
    try:
        history    = get_history(body.session_id)
        all_chunks = vector_store.search(q, TOP_K *5)

        if body.role == "teacher" or not body.year:
            chunks = all_chunks[:TOP_K]                          # อาจารย์ → เห็นทั้งหมด
        else:
            # นศ → เห็นเฉพาะไฟล์ของรุ่นตัวเอง (เทียบรหัสรุ่น 2 หลักตรงๆ เช่น "66" กับ "66")
            # + ไฟล์กลางที่ไม่ได้ระบุปี (ไม่ระบุ = ให้ทุกรุ่นเห็น) ตัดรุ่นอื่นออกไปเลย
            filtered = [c for c in all_chunks
                        if not c.get("year") or c.get("year") == body.year]
            chunks   = filtered[:TOP_K]

        answer = ask_llm(q, chunks, history=history)
        append_exchange(body.session_id, q, answer)
        return {"answer": answer}
    except Exception as e:
        traceback.print_exc()
        return err(str(e), 500)          # ← ส่ง error กลับ client

# ------------------------------------------------------------------ #
# Chat stream  /api/chat/stream
# กรองตามปีการศึกษา/role แบบเดียวกับ /chat (non-stream) ทุกประการ — เดิม endpoint
# นี้ไม่มีการกรองเลย ถ้านำมาใช้กับหน้านักศึกษาโดยตรงจะทำให้เห็นเอกสารรุ่นอื่นด้วย
# จึงต้องแก้ให้ตรงกันก่อนจะสลับ frontend มาใช้ endpoint นี้
# ------------------------------------------------------------------ #
@app.post("/api/chat/stream")
async def api_chat_stream(body: ChatBody):
    q = body.message.strip()
    if not q: return err("กรุณาส่งข้อความคำถาม")

    history    = get_history(body.session_id)
    all_chunks = vector_store.search(q, TOP_K * 5)
    if body.role == "teacher" or not body.year:
        chunks = all_chunks[:TOP_K]
    else:
        filtered = [c for c in all_chunks
                    if not c.get("year") or c.get("year") == body.year]
        chunks   = filtered[:TOP_K]

    def generate():
        yield f"data: {json.dumps({'type':'sources','sources':[{'source':c['source'],'score':round(c['score'],4)} for c in chunks]}, ensure_ascii=False)}\n\n"
        full_answer = ""
        try:
            for token in ask_llm_stream(q, chunks, history=history):
                full_answer += token
                yield f"data: {json.dumps({'type':'token','content':token}, ensure_ascii=False)}\n\n"
            append_exchange(body.session_id, q, full_answer)  # บันทึกความจำ+ประวัติเหมือน /chat
        except Exception as e:
            yield f"data: {json.dumps({'type':'error','message':str(e)})}\n\n"
        yield f"data: {json.dumps({'type':'done'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

# ------------------------------------------------------------------ #
# Chat simple  /chat  (ใช้โดย chatbot.html / java.js)
# ------------------------------------------------------------------ #
@app.post("/chat")
async def chat_simple(body: ChatSimpleBody):
    q = body.question.strip()
    if not q: return err("กรุณาส่งข้อความคำถาม")
    try:
        history    = get_history(body.session_id)
        all_chunks = vector_store.search(q, TOP_K * 5)

        # กรองตาม role/year — ใช้ค่า "year" จริงที่เก็บไว้ตอนอัปโหลด (ดู admin_upload)
        # เทียบรหัสรุ่น 2 หลักตรงๆ (เช่น รหัสนักศึกษา 66122xxxxxx -> year="66")
        if body.role == "teacher" or not body.year:
            chunks = all_chunks[:TOP_K]                          # อาจารย์ → เห็นทั้งหมด
        else:
            filtered = [c for c in all_chunks
                        if not c.get("year") or c.get("year") == body.year]
            chunks   = filtered[:TOP_K]

        answer = ask_llm(q, chunks, history=history)
        append_exchange(body.session_id, q, answer)
        # ใส่ sources มาด้วยเผื่อทดสอบว่า filter ปี/role ทำงานถูกไหม (ดูใน DevTools > Network
        # > Response ของ request /chat) — frontend เดิมอ่านแค่ data.answer จึงไม่กระทบ UI เดิม
        return {"answer": answer,
                "sources": [{"source": c["source"], "year": c.get("year", "")} for c in chunks]}
    except Exception as e:
        traceback.print_exc(); return err(str(e), 500)

@app.post("/reset-memory/{session_id}")
async def reset_memory(session_id: str):
    reset_session(session_id)
    return {"message": "ล้างความจำแล้ว"}
# เพิ่มใหม่ทั้งหมด
@app.post("/login")
async def user_login(body: LoginBody):
    username = body.username.strip()
    password = body.password.strip()

    # ถ้าเป็นรหัสนักศึกษา (11 หลัก) ต้องมีเอกสารของ "รุ่น" นั้นอยู่ในระบบจริงก่อน ถึงจะเข้าได้
    # (เช็คทุกครั้งที่ login ไม่ใช่แค่ตอนสมัครครั้งแรก เผื่อกรณีเอกสารรุ่นนั้นถูกลบออกไปทีหลัง)
    # รหัสบุคลากร/อาจารย์ (5 หลัก) ไม่ต้องเช็ค เพราะไม่ได้ผูกกับรุ่นใดรุ่นหนึ่ง เห็นเอกสารทุกรุ่นอยู่แล้ว
    student_year = extract_student_year(username)
    if student_year is not None and student_year not in vector_store.available_years():
        return JSONResponse(
            {"detail": f"ยังไม่มีเอกสารคู่มือสำหรับรุ่น '{student_year}' ในระบบ "
                       f"กรุณาตรวจสอบรหัสอีกครั้ง หรือติดต่อผู้ดูแลระบบ"},
            status_code=403)

    with _auth_lock:
        u = _load_users()
        if username not in u:
            # ถ้ามีไฟล์รายชื่อจริงแล้ว (students_roster.json) ต้องเช็คก่อนสมัครอัตโนมัติ
            # ถ้ายังไม่มีไฟล์นี้ (roster == permissive) พฤติกรรมจะเหมือนเดิมทุกอย่าง
            if not is_code_in_roster(username):
                return JSONResponse(
                    {"detail": "ไม่พบรหัสนี้ในระบบทะเบียน กรุณาตรวจสอบรหัส หรือติดต่อฝ่ายทะเบียน"},
                    status_code=403)
            u[username] = _hash(password)   # สมัครอัตโนมัติในครั้งแรกที่เข้าใช้
            _save_users(u)
            return {"message": "ลงทะเบียนและเข้าสู่ระบบสำเร็จ"}
        if u[username] != _hash(password):
            return JSONResponse({"detail": "รหัสไม่ถูกต้อง"}, status_code=401)
    return {"message": "เข้าสู่ระบบสำเร็จ"}

# ------------------------------------------------------------------ #
# Admin  /admin/*  (ใช้โดย loginadmin.html, admin.html, upload.html)
# ------------------------------------------------------------------ #
# เก็บ session ของแอดมินที่ login สำเร็จไว้ในหน่วยความจำ (หายเมื่อ restart server)
# token -> {"username": ..., "expires": unix_timestamp}
_admin_sessions = {}
_admin_sessions_lock = threading.Lock()
ADMIN_SESSION_TTL = 8 * 60 * 60  # session หมดอายุใน 8 ชั่วโมง

def _create_admin_session(username: str) -> str:
    token = secrets.token_urlsafe(32)
    with _admin_sessions_lock:
        _admin_sessions[token] = {"username": username, "expires": time.time() + ADMIN_SESSION_TTL}
    return token

def verify_admin_session(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "กรุณาเข้าสู่ระบบแอดมินก่อน")
    token = auth.removeprefix("Bearer ").strip()
    with _admin_sessions_lock:
        session = _admin_sessions.get(token)
        if not session:
            raise HTTPException(401, "เซสชันไม่ถูกต้อง กรุณาเข้าสู่ระบบใหม่")
        if session["expires"] < time.time():
            del _admin_sessions[token]
            raise HTTPException(401, "เซสชันหมดอายุ กรุณาเข้าสู่ระบบใหม่")
    return session["username"]

@app.post("/admin/login")
async def admin_login(body: LoginBody, request: Request):
    ip = request.client.host if request.client else "unknown"
    allowed, lock_msg = _admin_lockout_check(ip)
    if not allowed:
        return JSONResponse({"detail": lock_msg}, status_code=429)

    username = body.username.strip()
    ok_flag, msg = admin_login_user(username, body.password.strip())
    _admin_lockout_register_result(ip, ok_flag)
    if ok_flag:
        token = _create_admin_session(username)
        return {"message": msg, "token": token}
    return JSONResponse({"detail": msg}, status_code=401)

@app.post("/admin/logout")
async def admin_logout(request: Request):
    auth = request.headers.get("Authorization", "")
    token = auth.removeprefix("Bearer ").strip() if auth.startswith("Bearer ") else ""
    with _admin_sessions_lock:
        _admin_sessions.pop(token, None)
    return {"message": "ออกจากระบบแล้ว"}

@app.post("/admin/register")
async def admin_register(body: LoginBody):
    """ปิดใช้งานถาวร — ระบบอนุญาตให้มีผู้ดูแลระบบได้เพียงบัญชีเดียวเท่านั้น (ดู admin_config.json /
    DEFAULT_ADMIN_EMAIL ด้านบน) ไม่เปิดให้ลงทะเบียนเพิ่มจากหน้าเว็บอีกต่อไป
    หากลืมรหัสผ่าน ให้รัน reset_admin_password.py บนเซิร์ฟเวอร์แทน"""
    return JSONResponse(
        {"detail": "ระบบอนุญาตให้มีผู้ดูแลระบบได้เพียงบัญชีเดียวเท่านั้น ไม่สามารถลงทะเบียนเพิ่มได้ "
                    "หากลืมรหัสผ่าน กรุณาติดต่อผู้ดูแลระบบเซิร์ฟเวอร์เพื่อรีเซ็ตรหัสผ่าน"},
        status_code=403)

@app.post("/admin/upload", dependencies=[Depends(verify_admin_session)])
async def admin_upload(file: UploadFile = File(...), year: str = Form("")):
    if not file.filename: return JSONResponse({"detail":"ไม่พบไฟล์"}, status_code=400)
    if not _allowed(file.filename):
        return JSONResponse({"detail":"ไม่รองรับไฟล์ประเภทนี้"}, status_code=400)
    year = year.strip()
    # เว้นว่างได้ (= เอกสารกลาง ให้ทุกรุ่นเห็น) แต่ถ้ากรอกมาต้องเป็นรหัสรุ่น 2 หลักเท่านั้น
    # (ตรงกับตัวเลข 2 หลักแรกของรหัสนักศึกษา เช่น 66122xxxxxx -> "66")
    if year and not (year.isdigit() and len(year) == 2):
        return JSONResponse({"detail": "กรุณากรอกปีการศึกษาเป็นรหัสรุ่น 2 หลัก เช่น 66 หรือเว้นว่างไว้"},
                             status_code=400)
    # ถ้าแอดมินไม่ได้กรอกปีเอง ลองเดาจากชื่อไฟล์ก่อน (เช่น "...นักศึกษา 66.pdf" -> "66")
    auto_guessed = False
    if not year:
        guessed = _guess_year_from_filename(file.filename)
        if guessed:
            year = guessed
            auto_guessed = True
    filename = safe_filename(file.filename)
    fpath    = str(UPLOAD_DIR / filename)
    content  = await file.read()
    with open(fpath, "wb") as f: f.write(content)
    try:
        chunks = process_file(fpath, year); n = vector_store.add_chunks(chunks)
        msg = f"อัปโหลด '{filename}' และอัปเดต AI เรียบร้อย ({n} chunks)"
        if auto_guessed:
            msg += f" — เดาปีจากชื่อไฟล์เป็นรุ่น '{year}' อัตโนมัติ"
        return {"message": msg, "chunks_added": n, "filename": filename,
                "year": year, "year_auto_guessed": auto_guessed}
    except Exception as e:
        traceback.print_exc()
        if os.path.exists(fpath): os.remove(fpath)
        return JSONResponse({"detail": f"ประมวลผลไฟล์ล้มเหลว: {e}"}, status_code=500)

@app.get("/admin/files", dependencies=[Depends(verify_admin_session)])
async def admin_list_files():
    """รายการไฟล์คู่มือทั้งหมดพร้อมปีการศึกษา — ใช้เติมตารางในหน้า upload.html ตอนโหลดหน้า
    (ดึงจาก vector store จริง จึงเห็นไฟล์เก่าที่เคยอัปโหลดไว้ครบ ไม่ใช่แค่ที่อัปโหลดในเซสชันนี้)"""
    return {"files": vector_store.list_documents_detailed()}

@app.get("/admin/files/search", dependencies=[Depends(verify_admin_session)])
async def admin_search_files(q: str = ""):
    """ค้นหาไฟล์คู่มือจากชื่อไฟล์ (ไม่สนตัวพิมพ์เล็ก/ใหญ่) ใช้แทนปุ่ม 'ค้นหา' ที่เดิมเป็น mockup"""
    keyword = q.strip().lower()
    all_files = vector_store.list_documents_detailed()
    if not keyword:
        return {"files": all_files}
    matched = [f for f in all_files if keyword in f["source"].lower()]
    return {"files": matched}

@app.post("/admin/files/auto-tag", dependencies=[Depends(verify_admin_session)])
async def admin_auto_tag_years():
    """ไล่ดูไฟล์ทั้งหมดที่ยังไม่มีปีติดอยู่ (ไฟล์เก่าที่อัปโหลดก่อนมีฟีเจอร์นี้) แล้วเดาปีจาก
    ชื่อไฟล์ให้อัตโนมัติทีเดียวทั้งหมด ไม่ต้องกรอกทีละไฟล์"""
    tagged, skipped = [], []
    for doc in vector_store.list_documents_detailed():
        if doc["year"]:
            continue  # มีปีอยู่แล้ว ไม่ต้องแตะ
        guessed = _guess_year_from_filename(doc["source"])
        if guessed:
            vector_store.set_year_for_source(doc["source"], guessed)
            tagged.append({"source": doc["source"], "year": guessed})
        else:
            skipped.append(doc["source"])
    return {"message": f"ติดปีอัตโนมัติสำเร็จ {len(tagged)} ไฟล์"
                        + (f" (เดาไม่ได้ {len(skipped)} ไฟล์)" if skipped else ""),
            "tagged": tagged, "skipped": skipped}

class SetYearBody(BaseModel):
    source: str = ""
    year:   str = ""

@app.post("/admin/files/year", dependencies=[Depends(verify_admin_session)])
async def admin_set_file_year(body: SetYearBody):
    """แก้ปีของไฟล์ที่อัปโหลดไว้แล้ว โดยไม่ต้องอัปโหลดไฟล์ใหม่ซ้ำ — ใช้กับไฟล์เก่าที่เคย
    อัปโหลดไว้ก่อนมีฟีเจอร์แยกปี (ตอนนี้ยังเป็น "ทุกรุ่น" อยู่)"""
    source = body.source.strip()
    year   = body.year.strip()
    if not source:
        return JSONResponse({"detail": "ไม่พบชื่อไฟล์"}, status_code=400)
    if year and not (year.isdigit() and len(year) == 2):
        return JSONResponse({"detail": "กรุณากรอกปีการศึกษาเป็นรหัสรุ่น 2 หลัก เช่น 66 หรือเว้นว่างไว้"},
                             status_code=400)
    updated = vector_store.set_year_for_source(source, year)
    if updated == 0:
        return JSONResponse({"detail": f"ไม่พบไฟล์ '{source}' ใน vector store"}, status_code=404)
    return {"message": f"อัปเดตปีของ '{source}' เป็น '{year or 'ทุกรุ่น'}' แล้ว ({updated} chunks)",
            "source": source, "year": year}

@app.delete("/admin/files/{filename}", dependencies=[Depends(verify_admin_session)])
async def admin_delete_file(filename: str):
    """ลบไฟล์คู่มือถาวร (ทั้งไฟล์บนดิสก์และ chunk ที่เกี่ยวข้องทั้งหมดใน vector store)
    ใช้โดยปุ่ม "ลบ" ในหน้า upload.html — เดิมมีแต่ฝั่ง /dev/uploads/{filename} ที่จำกัด
    เฉพาะเครื่อง localhost เท่านั้น (สำหรับผู้พัฒนา) จึงเพิ่มตัวนี้ให้แอดมินที่ login ผ่าน
    /admin/login ลบไฟล์เองได้จากหน้าเว็บโดยตรง โดยใช้ตรรกะเดียวกับ dev_delete_upload"""
    fpath = UPLOAD_DIR / safe_filename(filename)
    file_removed = fpath.exists() and fpath.is_file()
    if file_removed: fpath.unlink()
    removed_chunks = vector_store.delete_by_source(filename)
    if not file_removed and removed_chunks == 0:
        return JSONResponse({"detail": f"ไม่พบไฟล์ '{filename}' ในระบบ"}, status_code=404)
    return {"message": f"ลบ '{filename}' เรียบร้อยแล้ว ({removed_chunks} chunks ถูกลบออกจาก AI ด้วย)"}

# ------------------------------------------------------------------ #
# Dev console  /dev/*  (ใช้โดย dev.html — เครื่องมือฝั่งผู้พัฒนา)
# จำกัดให้เรียกได้เฉพาะจากเครื่อง localhost เท่านั้น (verify_localhost นิยามไว้ด้านบน
# แล้ว ใกล้ๆ helper อื่นๆ เพื่อให้ page_dev() ที่อยู่ก่อนหน้านี้เรียกใช้ได้)
# ------------------------------------------------------------------ #
@app.get("/dev/uploads", dependencies=[Depends(verify_localhost)])
async def dev_list_uploads():
    files = [{"filename": p.name, "size_bytes": p.stat().st_size}
              for p in sorted(UPLOAD_DIR.iterdir()) if p.is_file()]
    return {"files": files}

@app.delete("/dev/uploads/{filename}", dependencies=[Depends(verify_localhost)])
async def dev_delete_upload(filename: str):
    fpath = UPLOAD_DIR / safe_filename(filename)
    file_removed = fpath.exists() and fpath.is_file()
    if file_removed: fpath.unlink()
    removed_chunks = vector_store.delete_by_source(filename)
    if not file_removed and removed_chunks == 0:
        raise HTTPException(404, f"ไม่พบไฟล์หรือ chunk ของ '{filename}'")
    return {"message": f"ลบ '{filename}' แล้ว "
                        f"(ไฟล์: {'ลบแล้ว' if file_removed else 'ไม่มีไฟล์ในดิสก์'}, "
                        f"chunks ที่ลบ: {removed_chunks})"}

@app.get("/dev/users", dependencies=[Depends(verify_localhost)])
async def dev_list_users():
    return {"users": list_users()}

@app.delete("/dev/users/{username}", dependencies=[Depends(verify_localhost)])
async def dev_delete_user(username: str):
    ok_flag, msg = delete_user(username)
    if ok_flag: return {"message": msg}
    return JSONResponse({"detail": msg}, status_code=404)

@app.get("/dev/documents", dependencies=[Depends(verify_localhost)])
async def dev_list_documents():
    return {"documents": vector_store.list_documents_detailed()}

@app.get("/dev/test-retrieval", dependencies=[Depends(verify_localhost)])
async def dev_test_retrieval(q: str, role: str = "student", year: str = ""):
    """เอาไว้ทดสอบว่า filter ตามปี/role ทำงานถูกไหม โดยไม่ต้อง login จริงและไม่ต้องรอ
    LLM ตอบ (ดูแค่ขั้นตอนดึงเอกสารที่จะถูกส่งไปให้ AI อ่าน) เช่น:
    /dev/test-retrieval?q=การลาพักการเรียน&role=student&year=66
    จะเห็นว่ามีเอกสารรุ่นอื่นหลุดเข้ามาปนไหม (source/year ของทุก chunk ที่ถูกดึงมา)"""
    all_chunks = vector_store.search(q, TOP_K * 5)
    if role == "teacher" or not year:
        chunks = all_chunks[:TOP_K]
    else:
        filtered = [c for c in all_chunks if not c.get("year") or c.get("year") == year]
        chunks   = filtered[:TOP_K]
    return {
        "query": q, "role": role, "year": year,
        "retrieved": [{"source": c["source"], "year": c.get("year", ""), "score": round(c["score"], 4)}
                      for c in chunks],
        "warning": "พบเอกสารรุ่นอื่นปนอยู่!" if any(
            role != "teacher" and year and c.get("year") and c["year"] != year for c in chunks
        ) else None
    }

@app.get("/dev/documents/{source}/chunks", dependencies=[Depends(verify_localhost)])
async def dev_get_chunks(source: str):
    chunks = vector_store.get_chunks_by_source(source)
    if not chunks:
        raise HTTPException(404, f"ไม่พบ chunk ของ '{source}'")
    return {"chunks": chunks}

# ------------------------------------------------------------------ #
# ENTRYPOINT — ทำให้รันได้ตรงๆ ด้วย `python main.py` โดยไม่ต้องจำคำสั่ง uvicorn
# (เดิมไฟล์นี้ไม่มีส่วนนี้เลย ต้องรันด้วย `uvicorn main:app --reload` เท่านั้น
# ซึ่งง่ายต่อการพิมพ์ผิดตอนสอบ จึงเพิ่ม fallback ให้รันตรงๆ ได้เลย)
#
# รันพร้อมกัน 2 เซิร์ฟเวอร์บนพอร์ต 8000 เดียวกัน (คนละ socket) เพื่อให้เข้าได้ทั้ง:
#   1) host="0.0.0.0" -> ทุกที่อยู่ IPv4 ในเครื่อง รวมถึง IP วง LAN ที่เครื่องอื่น
#      ในเครือข่ายเดียวกัน (เช่นมือถือ/โน้ตบุ๊กอีกเครื่อง) ใช้เข้าถึงได้
#   2) host="::1"      -> IPv6 loopback ของเครื่อง server เอง เพราะ Windows
#      สมัยใหม่เวลาพิมพ์คำว่า "localhost" ในเบราว์เซอร์ มักแปลไป IPv6 (::1)
#      เป็นอันดับแรกก่อน IPv4 (127.0.0.1) เสมอ — ถ้าไม่เปิดฟังตัวนี้ไว้ด้วย
#      พิมพ์ "localhost:8000" บนเครื่อง server เองจะขึ้น "connection refused"
#      ทั้งที่ server รันอยู่จริง (ต้องใช้ 127.0.0.1 แทนเท่านั้น)
# ------------------------------------------------------------------ #
if __name__ == "__main__":
    import uvicorn
    import asyncio

    async def _run_both_hosts():
        config_v4 = uvicorn.Config("main:app", host="0.0.0.0", port=8000, reload=False)
        config_v6 = uvicorn.Config("main:app", host="::1",     port=8000, reload=False)
        server_v4 = uvicorn.Server(config_v4)
        server_v6 = uvicorn.Server(config_v6)
        # return_exceptions=True กันไม่ให้ฝั่งใดฝั่งหนึ่งพัง (เช่นเครื่องนี้ปิด IPv6 ไว้
        # หรือ bind ::1 ไม่ได้ด้วยเหตุผลอื่น) ดึงอีกฝั่งที่ทำงานได้ปกติให้ล้มตามไปด้วย
        results = await asyncio.gather(server_v4.serve(), server_v6.serve(), return_exceptions=True)
        if isinstance(results[0], Exception):
            print(f"[WARN] เปิดฟัง IPv4 (0.0.0.0:8000) ไม่สำเร็จ: {results[0]}")
        if isinstance(results[1], Exception):
            print(f"[WARN] เปิดฟัง IPv6 (::1:8000) ไม่สำเร็จ — ใช้ 10.7.21.0:8000 แทนได้: {results[1]}")

    asyncio.run(_run_both_hosts())