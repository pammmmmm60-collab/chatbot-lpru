# ==========================================================================
# package_for_handoff.ps1
# สคริปต์รวมไฟล์โปรเจกต์ LPRU Chatbot ทั้งหมดเป็นไฟล์ .zip ก้อนเดียว สำหรับส่งต่อให้
# ผู้ใช้อื่นนำไปติดตั้งบนเครื่องใหม่ — ตัดไฟล์ที่ไม่ควรส่งไปด้วยออกให้อัตโนมัติ (ข้อมูล
# บัญชี/ประวัติแชท/ดัชนีค้นหาของเครื่องนี้โดยเฉพาะ) ตามเช็กลิสต์ในคู่มือส่งต่อระบบ ไม่ต้อง
# มานั่งเลือกไฟล์ทีละไฟล์เอง กันพลาดส่งข้อมูลส่วนตัวของนักศึกษา/รหัสผ่านแอดมินไปด้วยโดยไม่ตั้งใจ
#
# วิธีใช้:
#   1) วางไฟล์นี้ไว้ในโฟลเดอร์เดียวกับ main.py (โฟลเดอร์โปรเจกต์หลัก)
#   2) เปิด PowerShell ในโฟลเดอร์นั้น (Shift + คลิกขวาในโฟลเดอร์ -> "Open PowerShell window here")
#   3) รันคำสั่ง:
#        powershell -ExecutionPolicy Bypass -File package_for_handoff.ps1
#   4) จะได้ไฟล์ lpru-chatbot-handoff-<วันที่-เวลา>.zip โผล่ขึ้นมาในโฟลเดอร์เดียวกัน
#      เอาไฟล์ .zip ไฟล์เดียวนี้ไปส่งต่อได้เลย ไม่ต้องแนบทีละไฟล์
# ==========================================================================

$ErrorActionPreference = "Stop"
$projectDir = $PSScriptRoot
$dateStamp  = Get-Date -Format "yyyyMMdd-HHmm"
$zipName    = "lpru-chatbot-handoff-$dateStamp.zip"
$stagingDir = Join-Path $env:TEMP "lpru-handoff-staging-$dateStamp"

Write-Host "กำลังรวมไฟล์จาก: $projectDir" -ForegroundColor Cyan

# โฟลเดอร์ที่ไม่ส่งไปด้วย — เป็นข้อมูล/ดัชนีเฉพาะของเครื่องนี้ เครื่องใหม่ต้องสร้างขึ้นเอง
# ใหม่ทั้งหมด (ดูขั้นตอนที่ 3 ในคู่มือส่งต่อระบบ: สร้างฐานข้อมูลค้นหาใหม่)
$excludeDirs = @("vector_store", "chat_history", "conversations", "__pycache__", ".git", ".venv", "venv")

# ไฟล์ที่ไม่ส่งไปด้วย — เป็นข้อมูลบัญชี/ผู้ใช้จริงของสถาบันเดิม ห้ามติดไปกับเครื่องคนอื่น
# เด็ดขาด (ดูคำเตือนในคู่มือส่งต่อระบบ ขั้นตอนที่ 1)
$excludeFiles = @("admin_config.json", "users.json", "students_roster.json")

if (Test-Path $stagingDir) { Remove-Item $stagingDir -Recurse -Force }
New-Item -ItemType Directory -Path $stagingDir | Out-Null

# ใช้ robocopy คัดลอกทั้งโปรเจกต์ไปที่โฟลเดอร์ staging ชั่วคราวก่อน โดยข้ามโฟลเดอร์ต้องห้าม
# (/XD) และไฟล์ .zip เก่าที่อาจมีอยู่แล้วจากการรันสคริปต์นี้ครั้งก่อน (/XF) — /E คัดลอกทุก
# โฟลเดอร์ย่อยรวมโฟลเดอร์ว่างด้วย ไม่ทำอะไรกับไฟล์ต้นฉบับเลย (คัดลอก ไม่ใช่ย้าย)
robocopy $projectDir $stagingDir /E /XD $excludeDirs /XF *.zip /NFL /NDL /NJH /NJS | Out-Null

# robocopy ข้ามได้แค่ระดับโฟลเดอร์/รูปแบบชื่อไฟล์ทั่วไป ไฟล์เจาะจงที่ต้องกันชัวร์ๆ (บัญชี
# ผู้ใช้) ลบออกจาก staging อีกทีตรงนี้
foreach ($f in $excludeFiles) {
    $target = Join-Path $stagingDir $f
    if (Test-Path $target) { Remove-Item $target -Force }
}

# บีบอัดเนื้อหาทั้งหมดใน staging เป็น .zip ก้อนเดียว (ไม่ครอบด้วยโฟลเดอร์ staging เอง
# เพื่อให้แตกไฟล์แล้วเจอ main.py อยู่ตรงนอกสุดทันที ไม่ต้องไล่เข้าโฟลเดอร์ซ้อน)
$zipPath = Join-Path $projectDir $zipName
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path (Join-Path $stagingDir "*") -DestinationPath $zipPath

Remove-Item $stagingDir -Recurse -Force

Write-Host ""
Write-Host "เสร็จแล้ว: $zipPath" -ForegroundColor Green
Write-Host ""
Write-Host "ไม่ได้รวมไปด้วย (ตั้งใจตัดออก):" -ForegroundColor Yellow
Write-Host "  โฟลเดอร์: $($excludeDirs -join ', ')"
Write-Host "  ไฟล์:     $($excludeFiles -join ', ')"
Write-Host ""
Write-Host "ก่อนส่งไฟล์ zip นี้ต่อ อย่าลืมเปลี่ยนรหัสผ่านแอดมินฝั่งเครื่องที่จะติดตั้งใหม่ด้วย" -ForegroundColor Yellow
Write-Host "(ดูขั้นตอนที่ 4 ในคู่มือส่งต่อระบบ)" -ForegroundColor Yellow