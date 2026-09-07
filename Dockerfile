# ---------------------------------------------------------------------------
# Dockerfile สำหรับแอป FastAPI (main.py) ของ LPRU Chatbot
# ---------------------------------------------------------------------------
FROM python:3.11-slim

# ตั้งค่า env พื้นฐานให้ Python ทำงานใน container ได้ดี
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/models/hf

# poppler-utils ให้ pdftotext (main.py ใช้เป็นตัวหลักอ่าน PDF ภาษาไทย)
# build-essential + libgomp1 จำเป็นสำหรับ faiss-cpu / sentence-transformers บางส่วน
RUN apt-get update && apt-get install -y --no-install-recommends \
        poppler-utils \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ติดตั้ง dependency ก่อน copy โค้ด เพื่อใช้ layer cache ได้เต็มที่
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# copy โค้ดและไฟล์ static ทั้งหมดของแอป
COPY . .

EXPOSE 8000

# รันแบบเดียวกับ start_chatbot.bat (python main.py -> uvicorn 0.0.0.0:8000)
CMD ["python", "main.py"]
