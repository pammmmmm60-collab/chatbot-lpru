@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
title Chatbot LPRU - Server

REM ไปที่โฟลเดอร์เดียวกับไฟล์ .bat นี้เสมอ (กันปัญหา path ผิดตอนดับเบิลคลิกจากที่อื่น)
cd /d "%~dp0"

echo ============================================================
echo   Chatbot LPRU - กำลังเริ่มต้นระบบ...
echo ============================================================
echo.

REM ---------- 1) หา Python ----------
where python >nul 2>nul
if %errorlevel%==0 (
    set "PYCMD=python"
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        set "PYCMD=py -3"
    ) else (
        echo [ผิดพลาด] ไม่พบ Python ในเครื่องนี้
        echo กรุณาติดตั้ง Python จาก https://www.python.org/downloads/ ก่อน
        echo ^(ตอนติดตั้ง อย่าลืมติ๊ก "Add python.exe to PATH"^)
        echo.
        pause
        exit /b 1
    )
)

REM ---------- 2) เปิดใช้ virtual environment ถ้ามี ----------
if exist "venv\Scripts\activate.bat" (
    echo [ข้อมูล] พบ virtual environment ^(venv^) กำลังเปิดใช้งาน...
    call "venv\Scripts\activate.bat"
) else if exist ".venv\Scripts\activate.bat" (
    echo [ข้อมูล] พบ virtual environment ^(.venv^) กำลังเปิดใช้งาน...
    call ".venv\Scripts\activate.bat"
)

REM ---------- 3) เช็คว่ามีไฟล์ main.py อยู่จริงในโฟลเดอร์นี้ ----------
if not exist "main.py" (
    echo [ผิดพลาด] ไม่พบไฟล์ main.py ในโฟลเดอร์เดียวกับไฟล์ .bat นี้
    echo กรุณาย้ายไฟล์ start_chatbot.bat นี้ไปไว้ในโฟลเดอร์เดียวกับ main.py
    echo.
    pause
    exit /b 1
)

REM ---------- 4) เช็คว่า Ollama กำลังรันอยู่หรือยัง ถ้ายัง ให้ลองสั่งรันเบื้องหลัง ----------
tasklist /fi "imagename eq ollama.exe" 2>nul | find /i "ollama.exe" >nul
if errorlevel 1 (
    where ollama >nul 2>nul
    if %errorlevel%==0 (
        echo [ข้อมูล] กำลังเปิด Ollama เบื้องหลัง...
        start "" /min ollama serve
        timeout /t 3 /nobreak >nul
    ) else (
        echo [คำเตือน] ไม่พบโปรแกรม Ollama ในเครื่องนี้
        echo ระบบแชทจะเชื่อมต่อ AI ไม่ได้จนกว่าจะติดตั้ง Ollama จาก https://ollama.com
        echo แล้วรันคำสั่ง: ollama pull gemma3:4b
    )
) else (
    echo [ข้อมูล] Ollama กำลังทำงานอยู่แล้ว
)

echo.

REM ---------- 4.5) เช็คว่ามีโปรแกรม pdftotext (Poppler) หรือไม่ ----------
REM main.py ใช้ pdftotext เป็นตัวหลักในการอ่านไฟล์ PDF (แม่นกว่า pypdf มากสำหรับฟอนต์ไทย —
REM ดูคอมเมนต์เหนือฟังก์ชัน _read_pdf ใน main.py) ถ้าเครื่องนี้ไม่มี Poppler ระบบจะยัง "รันได้
REM ปกติ" (ไม่ error/ไม่ล่ม เพราะมี fallback ไปใช้ pypdf อยู่แล้ว) แต่คุณภาพข้อความที่อ่านจาก
REM PDF บางไฟล์จะแย่ลงแบบเงียบๆ โดยไม่มีใครสังเกตเห็นจนกว่า AI จะเริ่มตอบผิด/ตอบไม่ตรงคำถาม
REM เตือนไว้ตรงนี้ให้เห็นชัดเจนตั้งแต่ตอนเปิดเซิร์ฟเวอร์ ดีกว่าปล่อยให้ไปเจอปัญหาทีหลัง
where pdftotext >nul 2>nul
if errorlevel 1 (
    echo [คำเตือน] ไม่พบโปรแกรม pdftotext ^(Poppler^) ในเครื่องนี้
    echo ระบบจะยังทำงานได้ปกติ แต่จะอ่านไฟล์ PDF บางไฟล์ผิดพลาดได้ ^(โดยเฉพาะฟอนต์ไทยบางแบบ^)
    echo แนะนำให้ติดตั้ง Poppler for Windows แล้วเพิ่มโฟลเดอร์ ...\poppler-xx\Library\bin
    echo เข้า PATH ของ Windows ^(ดูวิธีละเอียดในคอมเมนต์เหนือฟังก์ชัน _read_pdf ใน main.py^)
) else (
    echo [ข้อมูล] พบโปรแกรม pdftotext ^(Poppler^) แล้ว
)

echo.

REM ---------- 5) เปิด ngrok เพื่อสร้างลิงก์สาธารณะให้เข้าถึงระบบจากนอกเครื่องได้ ----------
REM หา ngrok.exe ในโฟลเดอร์นี้ก่อน ถ้าไม่มีค่อยหาใน PATH ของเครื่อง
set "NGROK_CMD="
if exist "ngrok.exe" set "NGROK_CMD=ngrok.exe"
if not defined NGROK_CMD (
    where ngrok >nul 2>nul
    if %errorlevel%==0 set "NGROK_CMD=ngrok"
)

if defined NGROK_CMD (
    echo [ข้อมูล] กำลังเปิด ngrok เพื่อสร้างลิงก์สาธารณะ ^(พอร์ต 8000^)...
    echo          ดูลิงก์สาธารณะได้ในหน้าต่าง "ngrok tunnel" ที่เปิดขึ้นมาใหม่
    echo          ^(ครั้งแรกต้องตั้งค่า authtoken ก่อน ถ้ายังไม่เคยทำ ให้รัน:
    echo           ngrok config add-authtoken ^<TOKEN_ของคุณจาก dashboard.ngrok.com^)
    start "ngrok tunnel" cmd /k %NGROK_CMD% http 8000
) else (
    echo [คำเตือน] ไม่พบ ngrok.exe ในโฟลเดอร์นี้ และไม่พบในเครื่อง จะข้ามการสร้างลิงก์สาธารณะ
)

echo.

REM ---------- 6) เปิดเบราว์เซอร์อัตโนมัติหลังรอเซิร์ฟเวอร์เริ่มทำงาน (รันเบื้องหลัง) ----------
REM ปรับตัวเลข 15 (วินาที) เพิ่ม/ลดได้ถ้าเซิร์ฟเวอร์เริ่มช้า/เร็วกว่านี้ในเครื่องคุณ
REM แก้ pang.html เป็นหน้าอื่นได้ถ้าต้องการให้เปิดหน้าอื่นแทน (เช่น user.html)
start "" cmd /c "timeout /t 15 /nobreak>nul && start http://127.0.0.1:8000/pang.html"

echo [ข้อมูล] กำลังเริ่มเซิร์ฟเวอร์... (ครั้งแรกอาจใช้เวลาสักครู่ กรุณารอ)
echo          เบราว์เซอร์จะเปิดให้อัตโนมัติใน ~15 วินาที
echo          หากเบราว์เซอร์เปิดแล้วแต่หน้าเว็บโหลดไม่ขึ้น ให้รอสักครู่แล้วกด Refresh
echo          *** ห้ามปิดหน้าต่างนี้ ห้ามปิดหน้าต่าง "ngrok tunnel" ขณะใช้งานระบบ ***
echo.

REM ---------- 7) รันเซิร์ฟเวอร์หลัก ----------
%PYCMD% main.py

echo.
echo ============================================================
echo   เซิร์ฟเวอร์หยุดทำงานแล้ว
echo ============================================================
pause