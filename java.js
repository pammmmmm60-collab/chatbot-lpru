// ==========================================
// 0. ค่ากลาง / ข้อความที่ใช้ร่วมกันทุกหน้า (ไม่ได้เจาะจงหน้าใดหน้าหนึ่ง)
// API = base URL ของ backend, txt/t() = ชุดข้อความแจ้งเตือนที่หน้าอื่น
// ด้านล่างเรียกใช้ร่วมกัน — ยกเว้นหน้า dev.html (ส่วนที่ 8) ที่ใช้
// DEV_API ของตัวเองแยกต่างหาก เพราะคุยกับ backend คนละที่อยู่
// ==========================================
const API = "";

const txt = {
    studentIdError: "กรุณากรอกรหัสนักศึกษาให้ครบ 11 หลัก และต้องเป็นตัวเลขเท่านั้น",
    connecting: "กำลังค้นหาข้อมูลในคู่มือ...",
    serverError: " ขออภัยครับ ไม่สามารถเชื่อมต่อกับเซิร์ฟเวอร์ได้ โปรดตรวจสอบว่าเปิด Backend รันอยู่หรือไม่",
    adminLoginSuccess: "เข้าสู่ระบบแอดมินสำเร็จ",
    adminLoginFail: "ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง",
    adminLoginServerError: "เชื่อมต่อเซิร์ฟเวอร์ไม่ได้",
    adminLoginEmpty: "กรุณากรอกข้อมูลให้ครบถ้วน",
    uploadSuccess: "อัปโหลดและอัปเดตเรียบร้อย",
    uploading: "กำลังอัปโหลด",
    uploadBtn: "อัปโหลด",
    uploadServerError: "อัปโหลดไม่สำเร็จ: เชื่อมต่อเซิร์ฟเวอร์ไม่ได้",
    uploadEmpty: "กรุณาเลือกไฟล์ก่อนกดอัปโหลด",
    searchMsg: "ระบบกำลังค้นหาคู่มือที่ชื่อว่า: ",
    loginTitle: "กรุณากรอกรหัสนักศึกษา",
    studentPlaceholder: "รหัสนักศึกษา / รหัสบุคลากร",
    loginBtn: "เข้าสู่ระบบ",
    codeFormatError: "กรุณากรอกเฉพาะตัวเลขเท่านั้นครับ",
    codeLengthError: "นักศึกษากรอกรหัส 11 หลัก, บุคลากรกรอกรหัส 5 หลัก",
    invalidCode: "รหัสไม่ถูกต้อง",
    loginServerError: "เชื่อมต่อ server ไม่ได้",
    roleStudent: "(นักศึกษา)",
    roleTeacher: "(อาจารย์/บุคลากร)",

    // คำถามแนะนำ (chatbot.html) — ฟีเจอร์ใหม่
    suggestedQuestionsTitle: "คำถามแนะนำ",

    // จัดการคำถามแนะนำประจำปี (upload.html ฝั่งแอดมิน) — ฟีเจอร์ใหม่
    sqAddSuccess: "เพิ่มคำถามแนะนำสำเร็จ",
    sqUpdateSuccess: "แก้ไขคำถามแนะนำสำเร็จ",
    sqDeleteSuccess: "ลบคำถามแนะนำสำเร็จ",
    sqEmptyQuestion: "กรุณากรอกคำถามแนะนำก่อนกดเพิ่ม",
    sqYearFormatError: "กรุณากรอกรหัสรุ่น 2 หลัก เช่น 66 หรือเว้นว่างไว้ถ้าเป็นคำถามกลาง (ทุกรุ่นเห็น)",
    sqServerError: "เชื่อมต่อเซิร์ฟเวอร์ไม่ได้",
};

function t(key) {
    return txt[key];
}

// ==========================================
// 1. หน้า Login — user.html
// (หมายเหตุ: เลขหมวดกระโดดจาก 2 ไป 4 ด้านล่าง เป็นแบบนี้มาตั้งแต่ไฟล์ต้นฉบับ
// เดิมแล้ว ไม่ได้แปลว่ามีส่วนที่ 3 หายไปหรือไม่ได้กำกับไว้ — ทุกหน้า/ทุกฟังก์ชัน
// ในไฟล์นี้มีคอมเมนต์กำกับครบว่าเป็นของหน้าไหนแล้วทั้งหมด)
// ==========================================
const loginForm = document.getElementById("loginForm");
if (loginForm) {
    loginForm.addEventListener("submit", async function(e) {
    e.preventDefault();
    const code = (document.getElementById("codeInput").value || "").trim();

    if (!/^\d+$/.test(code)) { alert(t("codeFormatError")); return; }
    if (code.length !== 11 && code.length !== 5) {
        alert(t("codeLengthError")); return;
    }

    try {
        const res = await fetch(`${API}/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: code, password: code })
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            alert(data.detail || t("invalidCode"));
            return;
        }

        // เก็บ session token + role/year ที่ backend ยืนยันแล้ว (ไม่ใช่ค่าที่คำนวณเองฝั่ง
        // client อีกต่อไป) ไว้ใน localStorage ผูกกับรหัสนี้ — หน้าแชทจะแนบ token นี้ไปกับ
        // ทุกคำขอที่แตะข้อมูลส่วนตัว (คุยกับ AI / ประวัติแชท) ผ่าน header Authorization
        // เดียวกับที่ฝั่งแอดมินใช้อยู่แล้ว (ดู sessionStorage("admin_token") ด้านล่างของไฟล์นี้)
        localStorage.setItem("lpru_session_" + code, JSON.stringify({
            token: data.token, role: data.role, year: data.year
        }));

        if (code.length === 11) {
            const year = code.substring(0, 2);
            window.location.href = `chatbot.html?role=student&year=${year}&id=${code}`;
        } else {
            window.location.href = `chatbot.html?role=teacher&id=${code}`;
        }
    } catch {
        alert(t("loginServerError"));
    }
});
}

// ==========================================
// 2. ส่วนของหน้าแชทบอท (Chatbot Page)
// ==========================================
const chatDisplay = document.querySelector(".chat-display");
const inputMessage = document.getElementById("inputMessage");
const sendButton = document.getElementById("Send");
const newChatButton = document.getElementById("NewChat");

if (chatDisplay && inputMessage && sendButton) {
    const urlParams = new URLSearchParams(window.location.search);
    // บั๊กเดิม: fallback เป็น "ไม่ระบุ" (string ไม่ว่าง) ทำให้ backend เช็ค `not body.year`
    // เป็น False แล้วไปกรองหาไฟล์ที่ year=="ไม่ระบุ" ซึ่งไม่มีอยู่จริง -> ได้ chunk ว่างเปล่า
    // ทุกครั้งที่เข้าหน้านี้โดยไม่มี ?year= ใน URL (เช่น เข้าตรงๆ ไม่ผ่านหน้า login)
    // แก้เป็น "" (string ว่าง) เพื่อให้ backend ตีความว่า "ไม่ระบุปี = ไม่กรอง" ตามที่ตั้งใจไว้จริง
    const studentYear = urlParams.get('year') || "";
    const studentId = urlParams.get('id') || ("guest_" + Math.floor(Math.random() * 10000));
    const userRole = urlParams.get('role') || "student";

    // Session token ที่ได้ตอน /login สำเร็จ (เก็บไว้ใน localStorage ผูกกับรหัสนี้ — ดูส่วนที่ 1
    // ด้านบน) *** สำคัญ: role/year ใน URL ด้านบนใช้แค่แสดงผล UI เท่านั้น (เช่น ป้าย "อาจารย์/
    // บุคลากร") ตัวที่ backend ใช้กรองข้อมูลจริงๆ คือ role/year ที่ผูกกับ token นี้ ซึ่งแก้จาก
    // URL ไม่ได้ — ถ้าไม่มี token เลย (เข้าหน้านี้ตรงๆ โดยไม่ผ่าน user.html) จะเด้งกลับไปหน้า
    // login ทันที เพราะ /api/chat/stream และ /conversations/* ทุกตัวต้องมี token ที่ถูกต้อง
    let sessionToken = null;
    if (!studentId.startsWith("guest_")) {
        try {
            const stored = JSON.parse(localStorage.getItem("lpru_session_" + studentId) || "null");
            sessionToken = stored && stored.token ? stored.token : null;
        } catch { sessionToken = null; }
    }
    if (!sessionToken) {
        alert("กรุณาเข้าสู่ระบบก่อนใช้งานแชทบอท");
        window.location.href = "user.html";
    }
    function authHeaders() {
        return sessionToken ? { "Authorization": "Bearer " + sessionToken } : {};
    }
    // ใช้ร่วมกันทุกจุดที่ยิง request ไปหา endpoint ที่ต้อง login (แชท/ประวัติแชท) — ถ้า token
    // หมดอายุ/ไม่ถูกต้อง (401/403) ให้เคลียร์ token เก่าทิ้งแล้วพากลับไป login ใหม่ทันที
    function handleAuthError(status) {
        if (status === 401 || status === 403) {
            localStorage.removeItem("lpru_session_" + studentId);
            alert("เซสชันหมดอายุ กรุณาเข้าสู่ระบบใหม่");
            window.location.href = "user.html";
            return true;
        }
        return false;
    }

    // แสดง role ข้าง title (เดิมมี <span id="roleName"> ในหน้า chatbot.html แต่ไม่เคยถูกเติมข้อความ)
    const roleNameEl = document.getElementById("roleName");
    if (roleNameEl) {
        roleNameEl.textContent = userRole === "teacher" ? t("roleTeacher") : t("roleStudent");
    }

    // ==========================================
    // เลือกโมเดล AI — ฟีเจอร์ใหม่ เฉพาะอาจารย์/บุคลากร (role=teacher) เท่านั้น เปลี่ยนโมเดลแล้ว
    // มีผลกับ "แชทจริง" ของเซสชันนี้ทันที (ไม่ใช่หน้าทดสอบแยกต่างหาก) ผูกกับ GET /api/models
    // และฟิลด์ model ใน POST /api/chat/stream ใน main.py — backend เช็ค role จาก session token
    // จริงเสมอ (ไม่เชื่อ userRole ที่มาจาก URL ตรงนี้) นักศึกษาที่แก้ URL เป็น role=teacher เอง
    // จะยังโดน /api/models ตอบ 403 อยู่ดี ส่วนนี้จึงยังคงซ่อนอยู่เหมือนเดิม
    // ==========================================
    const MODEL_KEY = "lpru_ai_model_" + studentId;  // จำโมเดลที่เลือกไว้ต่อผู้ใช้แต่ละคน (แนวทางเดียวกับ USER_NAME_KEY ด้านบน)
    const modelSelectBlock = document.getElementById("modelSelectBlock");
    const aiModelSelect    = document.getElementById("aiModelSelect");
    let selectedAiModel = localStorage.getItem(MODEL_KEY) || "";  // ค่าว่าง = ใช้โมเดลเริ่มต้นของระบบ (แนบไปกับทุกคำถามที่ส่งเข้า /api/chat/stream)

    async function loadAiModelOptions() {
        if (!aiModelSelect || userRole !== "teacher") return;  // เฉพาะอาจารย์/บุคลากรเท่านั้นถึงจะลองโหลด (ประหยัด request ของนักศึกษา)
        try {
            const res = await fetch(`${API}/api/models`, { headers: authHeaders() });
            if (!res.ok) return;  // ไม่ใช่อาจารย์/บุคลากรจริง (403), token หมดอายุ (401), หรือ Ollama ต่อไม่ได้ (502) — ซ่อนต่อไปเงียบๆ ไม่ alert รบกวน
            const data = await res.json();
            const models = data.models || [];
            const def = data.active_default || "";
            if (models.length === 0) return;  // ไม่มีโมเดลติดตั้งบนเครื่อง Ollama เลย ไม่ต้องโชว์ dropdown เปล่าๆ

            // ถ้าโมเดลที่เคยเลือกไว้ (จาก localStorage) ไม่มีอยู่ในเครื่องแล้ว ให้กลับไปใช้ค่าเริ่มต้นของระบบแทน
            if (selectedAiModel && !models.includes(selectedAiModel)) selectedAiModel = "";

            aiModelSelect.innerHTML = `<option value="">ค่าเริ่มต้นของระบบ${def ? " (" + escapeHtml(def) + ")" : ""}</option>` +
                models.map(m => `<option value="${escapeHtml(m)}" ${m === selectedAiModel ? "selected" : ""}>${escapeHtml(m)}</option>`).join("");

            modelSelectBlock.style.display = "block";  // มีโมเดลให้เลือกจริง ค่อยแสดง dropdown ขึ้นมา
        } catch (error) {
            // เชื่อมต่อ backend ไม่ได้ — ซ่อนไว้ก่อนเหมือนเดิม ไม่ต้อง alert รบกวนผู้ใช้
        }
    }

    if (aiModelSelect) {
        aiModelSelect.addEventListener("change", function() {
            selectedAiModel = aiModelSelect.value;
            localStorage.setItem(MODEL_KEY, selectedAiModel);
        });
    }
    loadAiModelOptions();

    // ชื่อที่แสดงของผู้ใช้ — แก้ไขได้โดยกดปุ่มข้าง "แชทใหม่"
    // (เอารูปโปรไฟล์ฝั่งผู้ใช้ออกแล้วตามที่ขอ เหลือแค่ชื่อที่ตั้งเองได้)
    const USER_NAME_KEY = "lpru_chat_user_name_" + studentId;
    function getUserName() {
        return localStorage.getItem(USER_NAME_KEY) || "ตั้งชื่อของคุณ";
    }
    const userAvatarBtn = document.getElementById("userAvatarBtn");
    if (userAvatarBtn) {
        userAvatarBtn.textContent = getUserName();
        userAvatarBtn.addEventListener("click", function() {
            const current = localStorage.getItem(USER_NAME_KEY) || "";
            const next = prompt("ตั้งชื่อที่จะแสดงของคุณ:", current);
            if (next !== null && next.trim() !== "") {
                localStorage.setItem(USER_NAME_KEY, next.trim());
                userAvatarBtn.textContent = next.trim();
            }
        });
    }

    // ปุ่ม "ออกจากระบบ" — อยู่ล่างสุดของแถบด้านข้าง (ดู chatbot.html) ลบ session token ทิ้ง
    // (ต้อง login ใหม่ถึงจะได้ token ใหม่มาคุยกับ AI/ดูประวัติแชทได้อีก) แล้วพากลับไปหน้ากรอก
    // รหัส (ไม่ลบชื่อที่ตั้งไว้หรือประวัติแชทใดๆ ทั้งสองอย่างยังอยู่ครบเมื่อกลับมาล็อกอินซ้ำ)
    const logoutBtn = document.getElementById("logoutBtn");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", async function() {
            try {
                await fetch(`${API}/logout`, { method: "POST", headers: authHeaders() });
            } catch (error) {
                console.error("logout request failed", error);
            } finally {
                localStorage.removeItem("lpru_session_" + studentId);
                window.location.href = "user.html";
            }
        });
    }

    // ข้อความทักทายตอนเปิดหน้าครั้งแรก (แสดงครั้งเดียว ไม่แสดงซ้ำถ้ามีข้อความอยู่แล้ว
    // เช่น ตอนเรียก appendMessage มาก่อนหน้านี้ในโค้ดส่วนอื่น) — เป็นแค่ placeholder ตอนเริ่มโหลด
    // หน้า ถ้าโหลดแถบประวัติแชท (ด้านล่าง) สำเร็จ จะถูกแทนที่ด้วยแชทเธรดจริงที่โหลดมาแทน
    if (chatDisplay.children.length === 0) {
        appendMessage("สวัสดีเจ้า มีอะหยังหื้อน้องกาสะลองจ่วยก่อเจ้า?", "bot", new Date());
    }

    // ==========================================
    // แถบประวัติแชท — ฟีเจอร์ใหม่ (ไม่กระทบกลไกความจำ/แชทเดิม)
    // เดิมกดปุ่ม "แชทใหม่" คือล้างประวัติทิ้งถาวรผ่าน /reset-memory ตอนนี้เปลี่ยนเป็น "สร้างแชท
    // เธรดใหม่" แทน (แชทเก่าไม่หาย ดูย้อนหลังได้จากแถบนี้) ผูกกับ /conversations/* ใน main.py
    // โดยใช้ studentId::conversationId เป็น session_id ตอนคุยกับ /chat แทน studentId เฉยๆ
    //
    // อัปเดต: ย้าย UI จากแถบเลื่อน (drawer) มาเป็นแถบด้านข้างถาวรที่พับ/กางได้ (#appSidebar ใน
    // chatbot.html) ตามที่ขอ ปุ่ม "+ เริ่มแชทใหม่" แยกในแถบประวัติถูกเอาออก เหลือปุ่ม "แชทใหม่"
    // บนแถบเมนูด้านบนเพียงจุดเดียวตามที่ขอ ("ยกเว้นแชทใหม่")
    // ==========================================
    const sidebarCollapseBtn  = document.getElementById("sidebarCollapseBtn");
    const sidebarExpandBtn    = document.getElementById("sidebarExpandBtn");
    const historyListEl       = document.getElementById("historyList");
    let activeConversationId = null;

    // แก้บั๊ก: เดิมสถานะ "กำลังตอบอยู่" (isGenerating/currentAbortController) เป็นตัวแปรเดียวใช้
    // ร่วมกันทั้งหน้า ไม่ได้ผูกกับแชทไหนแชทหนึ่ง — พอถามคำถามแล้วสลับไปดูแชทเก่าระหว่างที่ AI
    // ยังตอบไม่จบ หน้าจอ (chatDisplay) จะถูกล้างทิ้งไปแสดงแชทเก่าแทน ทำให้ดูเหมือนคำตอบ "หยุด"
    // ทั้งที่จริงๆ ยังรันอยู่เบื้องหลัง (คำตอบยังถูกบันทึกลงฐานข้อมูลถูกต้อง แค่ไม่มีที่แสดงผล)
    // ตอนนี้เปลี่ยนมาเก็บสถานะการตอบของ "แต่ละแชท" แยกกันใน Map นี้แทน (key = conversationId)
    // เพื่อให้สลับแชทไปมาระหว่างที่ AI กำลังตอบได้อย่างถูกต้อง — คำถาม/คำตอบของแชทเดิมยังทำงาน
    // ต่อเนื่องอยู่เบื้องหลังจริงๆ และถ้าสลับกลับมาดูแชทนั้นอีกครั้ง จะเห็นคำตอบไหลต่อ (หรือที่
    // ตอบจบไปแล้ว) ทันที ไม่ต้องรีเฟรชหน้าเว็บ ดู switchConversation/sendButton handler ด้านล่าง
    const activeGenerations = new Map();  // value: { status: "generating"|"done", fullAnswer, isFirstToken, loadingBox, rowEl, abortController }

    // session_id ที่ใช้คุยกับ /chat — ถ้ายังโหลดแถบประวัติไม่สำเร็จ (เช่น backend เก่า/ออฟไลน์)
    // จะ fallback ไปใช้ studentId เฉยๆ เหมือนพฤติกรรมเดิมก่อนมีฟีเจอร์นี้ทุกประการ
    function currentSessionId() {
        return activeConversationId ? `${studentId}::${activeConversationId}` : studentId;
    }

    // อัปเดตหน้าตาปุ่มส่ง/หยุด ให้ตรงกับสถานะของ "แชทที่กำลังเปิดดูอยู่ตอนนี้" เท่านั้น (ไม่ใช่
    // แชทล่าสุดที่กดส่ง) เรียกทุกครั้งที่สลับแชท หรือเริ่ม/จบการตอบของแชทที่กำลังเปิดอยู่
    function refreshSendButtonUI() {
        const gen = activeGenerations.get(activeConversationId);
        sendButton.innerHTML = (gen && gen.status === "generating")
            ? '<span style="display:inline-block; width:10px; height:10px; background:white; border-radius:2px;"></span>'  // ไอคอนหยุด (สี่เหลี่ยม)
            : `<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"></path></svg>`;  // ไอคอนส่ง (ลูกศร) ค่าเริ่มต้น
    }

    // พับ/กางแถบด้านข้าง — สลับคลาส "sidebar-collapsed" บน <body> (ดู style.css ส่วนที่ 14)
    // เปลี่ยนจากเดิมที่สลับบน #chatBodyLayout มาเป็น body แทน เพราะปุ่ม ☰ (#sidebarExpandBtn)
    // ถูกย้ายขึ้นไปอยู่ในแถบเมนูด้านบน (.navbar) ซึ่งอยู่นอก #chatBodyLayout แล้ว ต้องใช้ตัวที่
    // ครอบทั้งแถบเมนูและแถบด้านข้างพร้อมกันได้ถึงจะสั่งซ่อน/โชว์ปุ่มนี้ได้ถูกต้อง
    function collapseSidebar() { document.body.classList.add("sidebar-collapsed"); }
    function expandSidebar()   { document.body.classList.remove("sidebar-collapsed"); }

    // เริ่มต้นแบบพับเก็บไว้ก่อนบนจอเล็ก (มือถือ) กันแถบด้านข้างบังพื้นที่แชททั้งหมด
    // ส่วนจอปกติ (คอม/แท็บเล็ต) กางไว้ให้เห็นเลยเหมือนแชทบอทมาตรฐานทั่วไป
    if (window.innerWidth < 760) collapseSidebar();

    if (sidebarCollapseBtn) sidebarCollapseBtn.addEventListener("click", collapseSidebar);
    if (sidebarExpandBtn)   sidebarExpandBtn.addEventListener("click", expandSidebar);

    function renderHistoryList(list) {
        if (!historyListEl) return;
        if (!list || list.length === 0) {
            historyListEl.innerHTML = `<p class="history-empty">ยังไม่มีประวัติแชท</p>`;
            return;
        }
        historyListEl.innerHTML = "";
        list.forEach(conv => {
            const item = document.createElement("div");
            item.className = "history-item" + (conv.id === activeConversationId ? " active" : "");

            // แก้บั๊กสลับแชทระหว่างตอบ: ใส่ ⏳ นำหน้าชื่อแชทที่ยังมีคำตอบกำลังสตรีมอยู่เบื้องหลัง
            // (ดู activeGenerations ด้านบน) ให้ผู้ใช้รู้ว่าแชทนี้ยังไม่หยุด แค่ไม่ได้ดูอยู่เฉยๆ
            const stillGenerating = activeGenerations.get(conv.id)?.status === "generating";
            const titleEl = document.createElement("span");
            titleEl.className = "history-item-title";
            titleEl.textContent = (stillGenerating ? "⏳ " : "") + (conv.title || "แชทใหม่");
            item.appendChild(titleEl);

            const deleteBtn = document.createElement("button");
            deleteBtn.type = "button";
            deleteBtn.className = "history-item-delete";
            deleteBtn.textContent = "🗑";
            deleteBtn.title = "ลบแชทนี้";
            deleteBtn.addEventListener("click", async function(event) {
                event.stopPropagation();
                const confirmed = confirm(`ยืนยันลบแชท "${conv.title || 'แชทใหม่'}" หรือไม่? การลบไม่สามารถกู้คืนได้`);
                if (!confirmed) return;
                try {
                    const res = await fetch(`${API}/conversations/${encodeURIComponent(studentId)}/${encodeURIComponent(conv.id)}`, {
                        method: "DELETE", headers: authHeaders()
                    });
                    if (!res.ok) {
                        if (res.status === 401 || res.status === 403) handleAuthError(res.status);
                        throw new Error(`ลบแชทไม่สำเร็จ (${res.status})`);
                    }
                } catch (error) {
                    // ถ้าลบฝั่ง server ไม่สำเร็จ ห้ามแก้ UI ให้เหมือนลบสำเร็จ
                    console.error(error);
                    return;
                }
                if (conv.id === activeConversationId) {
                    // แชทที่กำลังเปิดดูอยู่ถูกลบไป ต้องหาแชทอื่นมาแทน หรือสร้างใหม่ถ้าไม่เหลือเลย
                    await switchToFirstOrNewConversation();
                } else {
                    await refreshHistoryList();
                }
            });
            item.appendChild(deleteBtn);

            item.addEventListener("click", function() {
                if (conv.id !== activeConversationId) {
                    switchConversation(conv.id, false);
                } else if (window.innerWidth < 760) {
                    // จอเล็ก: คลิกซ้ำแชทที่เปิดอยู่แล้ว ให้พับแถบเก็บกลับไปโชว์พื้นที่แชทแทน
                    collapseSidebar();
                }
            });

            historyListEl.appendChild(item);
        });
    }

    async function refreshHistoryList() {
        if (!historyListEl) return [];
        try {
            const res = await fetch(`${API}/conversations/${encodeURIComponent(studentId)}`, { headers: authHeaders() });
            if (!res.ok) { handleAuthError(res.status); return []; }
            const data = await res.json();
            const list = data.conversations || [];
            renderHistoryList(list);
            return list;
        } catch (error) {
            // เชื่อมต่อ backend ไม่ได้ — ปล่อยรายการเดิมไว้ก่อน ไม่ต้อง alert รบกวนผู้ใช้
            return [];
        }
    }

    async function switchConversation(conversationId, isInitialLoad) {
        activeConversationId = conversationId;
        chatDisplay.innerHTML = "";
        try {
            const res = await fetch(
                `${API}/conversations/${encodeURIComponent(studentId)}/${encodeURIComponent(conversationId)}/messages`,
                { headers: authHeaders() }
            );
            if (!res.ok) handleAuthError(res.status);
            const messages = res.ok ? ((await res.json()).messages || []) : [];
            if (messages.length === 0) {
                appendMessage("สวัสดีเจ้า มีอะหยังหื้อน้องกาสะลองจ่วยก่อเจ้า?", "bot", new Date());
            } else {
                // แก้บั๊ก "เวลาไม่ตรง": เดิม backend ไม่ส่ง timestamp ของข้อความเก่ากลับมาเลย ทำให้
                // ตอนโหลดประวัติแชทย้อนหลัง ข้อความจะไม่มีเวลาโชว์ (หรือถ้าเป็นบรรทัดข้อความ
                // ต้อนรับของแชทว่าง จะโชว์เวลา "ตอนนี้" ปลอมๆ ทุกครั้งที่เปิดแชทนั้น) ตอนนี้
                // main.py ส่ง timestamp จริง (Unix epoch วินาที) มาด้วยแล้ว (ดู get_history/
                // api_get_messages) จึงแปลงกลับเป็น Date จริงแล้วส่งให้ appendMessage ตรงนี้ได้
                messages.forEach(m => appendMessage(
                    m.content,
                    m.role === "user" ? "user" : "bot",
                    m.timestamp ? new Date(m.timestamp * 1000) : null
                ));
            }
        } catch (error) {
            appendMessage("สวัสดีเจ้า มีอะหยังหื้อน้องกาสะลองจ่วยก่อเจ้า?", "bot", new Date());
        }

        // แก้บั๊กสลับแชทระหว่างตอบ: ถ้าแชทที่กำลังจะสลับไปดูนี้ ยังมีคำตอบที่กำลังสตรีมอยู่จริง
        // (ผู้ใช้ถามค้างไว้แล้วสลับออกไปดูแชทอื่นก่อนหน้านี้) ให้ดึงกล่องข้อความที่สะสมคำตอบไว้
        // อยู่แล้ว (เก็บอยู่ใน activeGenerations เบื้องหลัง ไม่เคยหายไปไหน) กลับมาแปะต่อท้ายแชท
        // นี้อีกครั้ง แล้ว token ถัดๆ ไปที่ backend ส่งมาจะเข้ามาแสดงต่อในกล่องเดิมได้ทันที
        const ongoing = activeGenerations.get(conversationId);
        if (ongoing && ongoing.status === "generating") {
            if (ongoing.userRowEl) chatDisplay.appendChild(ongoing.userRowEl);  // คำถามที่ยังไม่ถูกบันทึกลง DB (เพราะยังตอบไม่จบ) แปะกลับมาด้วย ไม่ใช่แค่คำตอบลอยๆ
            if (ongoing.rowEl) chatDisplay.appendChild(ongoing.rowEl);
            chatDisplay.scrollTop = chatDisplay.scrollHeight;
        }

        await refreshHistoryList();
        refreshSendButtonUI();  // ให้ปุ่มส่ง/หยุดตรงกับสถานะของแชทที่เพิ่งสลับมาดู
        // จอเล็ก (มือถือ): หลังเลือกแชทจากแถบด้านข้างแล้วให้พับแถบเก็บอัตโนมัติ เพื่อโชว์พื้นที่
        // แชทเต็มจอ (จอปกติปล่อยแถบกางค้างไว้ตามพฤติกรรมแชทบอทมาตรฐาน)
        if (!isInitialLoad && window.innerWidth < 760) collapseSidebar();
    }

    // ใช้ตอนแชทที่เปิดอยู่ถูกลบไป — สลับไปแชทอื่นที่เหลือ หรือสร้างแชทใหม่ถ้าไม่เหลือเลย
    async function switchToFirstOrNewConversation() {
        try {
            const res = await fetch(`${API}/conversations/${encodeURIComponent(studentId)}`, { headers: authHeaders() });
            const data = res.ok ? await res.json() : { conversations: [] };
            const remaining = data.conversations || [];
            if (remaining.length > 0) {
                await switchConversation(remaining[0].id, true);
                return;
            }
        } catch (error) { /* ตกไปสร้างแชทใหม่ด้านล่าง */ }
        await startNewConversation();
    }

    // สร้างแชทเธรดใหม่แล้วสลับไปเปิดทันที — ใช้ทั้งปุ่ม "+ เริ่มแชทใหม่" ในแถบประวัติ
    // และปุ่ม "แชทใหม่" เดิมบนแถบเมนู (เปลี่ยนพฤติกรรมจากเดิมที่ล้างประวัติทิ้งถาวร)
    async function startNewConversation() {
        try {
            const res = await fetch(`${API}/conversations/${encodeURIComponent(studentId)}`, { method: "POST", headers: authHeaders() });
            if (res.ok) {
                const data = await res.json();
                await switchConversation(data.conversation.id, false);
                return;
            }
            if (res.status === 401 || res.status === 403) handleAuthError(res.status);
            console.error(`สร้างแชทใหม่ไม่สำเร็จ (${res.status})`);
        } catch (error) {
            // เชื่อมต่อ backend ไม่ได้ — fallback เป็นพฤติกรรมเดิมก่อนมีฟีเจอร์นี้ (ล้างจอเฉยๆ
            // ไม่ผูกกับเธรดใหม่ในแถบประวัติ กันไม่ให้ผู้ใช้กดปุ่มแล้วไม่มีอะไรเกิดขึ้นเลย)
            chatDisplay.innerHTML = "";
            appendMessage("สวัสดีเจ้า มีอะหยังหื้อน้องกาสะลองจ่วยก่อเจ้า?", "bot", new Date());
        }
    }

    // โหลดแถบประวัติแชทตอนเปิดหน้า — ถ้ายังไม่เคยมีแชทเลย จะสร้างเธรดแรกให้อัตโนมัติ
    async function initConversations() {
        const list = await refreshHistoryList();
        if (list.length > 0) {
            await switchConversation(list[0].id, true);
        } else {
            await startNewConversation();
        }
    }
    initConversations();

    // ==========================================
    // คำถามแนะนำประจำปี — ฟีเจอร์ใหม่ (ไม่กระทบการแชทปกติ)
    // ดึงคำถามแนะนำที่แอดมินตั้งไว้สำหรับรุ่นของผู้ใช้คนนี้ (+ คำถามกลางที่ทุกรุ่นเห็น) โดยใช้
    // เงื่อนไขปีเดียวกับตอนเข้าสู่ระบบด้วยรหัสนักศึกษา (studentYear ที่ได้จาก ?year= ใน URL
    // ซึ่งมาจากรหัสนักศึกษาที่กรอกในหน้า user.html — ดูส่วน "หน้า Login" ด้านบนของไฟล์นี้)
    // แสดงเป็นปุ่มบนแถบเมนูด้านบน กดแล้วเด้งป๊อบอัพขึ้นมาให้เลือก แทนการโชว์ค้างอยู่ในหน้าจอ
    // ==========================================
    const sqBtn           = document.getElementById("suggestedQuestionsBtn");
    const sqModalOverlay  = document.getElementById("sqModalOverlay");
    const sqModalBody     = document.getElementById("sqModalBody");
    const sqModalCloseBtn = document.getElementById("sqModalCloseBtn");
    let cachedSuggestedQuestions = [];

    function openSuggestedQuestionsModal()  { if (sqModalOverlay) sqModalOverlay.classList.add("open"); }
    function closeSuggestedQuestionsModal() { if (sqModalOverlay) sqModalOverlay.classList.remove("open"); }

    function renderSuggestedQuestionsModal() {
        if (!sqModalBody) return;
        if (cachedSuggestedQuestions.length === 0) {
            sqModalBody.innerHTML = `<p class="sq-modal-empty">ยังไม่มีคำถามแนะนำสำหรับคุณในตอนนี้</p>`;
            return;
        }
        sqModalBody.innerHTML = "";
        cachedSuggestedQuestions.forEach(q => {
            const chip = document.createElement("button");
            chip.type = "button";
            chip.className = "suggested-question-chip";
            chip.textContent = q.question;
            chip.addEventListener("click", function() {
                inputMessage.value = q.question;
                closeSuggestedQuestionsModal();
                sendButton.click();
            });
            sqModalBody.appendChild(chip);
        });
    }

    // โหลดล่วงหน้าตอนเปิดหน้า (ครั้งเดียว) แล้วเก็บไว้ใน cache — ปุ่มจะแสดงเฉพาะตอนที่รุ่นนี้
    // มีคำถามแนะนำจริงๆ เท่านั้น กันปุ่มค้างอยู่เฉยๆ โดยไม่มีอะไรให้กด
    async function loadSuggestedQuestions() {
        try {
            const res = await fetch(`${API}/api/suggested-questions?year=${encodeURIComponent(studentYear)}`);
            if (!res.ok) return;
            const data = await res.json();
            cachedSuggestedQuestions = data.questions || [];
            // หมายเหตุ: ต้องระบุค่า "inline-block" ตรงๆ (แทนที่จะเคลียร์เป็น "" เฉยๆ) เพราะ
            // #suggestedQuestionsBtn ถูกซ่อนไว้ด้วย CSS "display: none" ใน style.css ตั้งแต่แรก
            // ถ้าใช้ style.display = "" จะแค่ล้าง inline style แล้วตกกลับไปใช้กฎ CSS เดิม (none)
            // อยู่ดี ปุ่มเลยไม่มีทางโผล่มาเลยแม้จะมีคำถามแนะนำจริงก็ตาม
            if (sqBtn) sqBtn.style.display = cachedSuggestedQuestions.length > 0 ? "inline-block" : "none";
        } catch (error) {
            // เชื่อมต่อ backend ไม่ได้ — ซ่อนปุ่มไว้ก่อน ไม่ต้อง alert รบกวนผู้ใช้
            if (sqBtn) sqBtn.style.display = "none";
        }
    }
    loadSuggestedQuestions();

    if (sqBtn) {
        sqBtn.addEventListener("click", function() {
            renderSuggestedQuestionsModal();
            openSuggestedQuestionsModal();
        });
    }
    if (sqModalCloseBtn) {
        sqModalCloseBtn.addEventListener("click", closeSuggestedQuestionsModal);
    }
    if (sqModalOverlay) {
        // คลิกพื้นหลังนอกกล่องป๊อบอัพเพื่อปิด (เป็น div ธรรมดา ไม่ใช่ native dialog เหมือน
        // alert/confirm จึงไม่บล็อกการทำงานของหน้าเว็บส่วนอื่น)
        sqModalOverlay.addEventListener("click", function(event) {
            if (event.target === sqModalOverlay) closeSuggestedQuestionsModal();
        });
    }

    inputMessage.addEventListener("keypress", function(event) {
        if (event.key === "Enter") {
            event.preventDefault();
            sendButton.click();
        }
    });

    // แก้บั๊กสลับแชทระหว่างตอบ (ต่อจาก activeGenerations ด้านบน): เดิมใช้ isGenerating/
    // currentAbortController ตัวเดียวคุมทั้งหน้า เปลี่ยนมาผูกกับแต่ละแชทผ่าน activeGenerations
    // แทน ปุ่มส่ง/หยุดจึงทำงานเฉพาะกับ "แชทที่กำลังเปิดดูอยู่" เท่านั้น ส่วนแชทอื่นที่กำลังตอบ
    // อยู่เบื้องหลัง (ถูกสลับออกไปก่อนหน้านี้) จะไม่ถูกรบกวน ยังคงตอบต่อจนจบตามปกติ
    sendButton.addEventListener("click", async function() {
        const genKey = activeConversationId;  // ผูกกับแชทที่กำลังเปิดอยู่ ณ ตอนกดปุ่มนี้เท่านั้น

        // ถ้าแชทที่กำลังดูอยู่ตอนนี้มีคำตอบกำลังสตรีมอยู่แล้ว กดปุ่มนี้ซ้ำ = "หยุด" เฉพาะแชทนี้
        const existingGen = activeGenerations.get(genKey);
        if (existingGen && existingGen.status === "generating") {
            existingGen.abortController.abort();  // สั่งยกเลิกการเชื่อมต่อ Stream ของแชทนี้ทันที
            return;
        }

        const text = inputMessage.value.trim();
        if (text === "") return;

        const userMsgBox = appendMessage(text, "user", new Date());
        inputMessage.value = "";

        const loadingBox = appendMessage("", "bot", new Date());
        loadingBox.classList.add("typing-indicator");
        loadingBox.innerHTML =
            '<span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>';

        // session_id คำนวณจาก genKey ที่จำไว้ตอนกดส่ง ไม่ใช่ currentSessionId() ตรงๆ เพราะถ้า
        // ผู้ใช้สลับแชทไปแล้วระหว่าง await ค่า activeConversationId จะเปลี่ยนไปแล้ว ทำให้คำตอบ
        // นี้ไปบันทึกผิดแชทได้ — ต้อง "ล็อก" ไว้ตั้งแต่ตอนเริ่มยิงคำถามเท่านั้น
        const requestSessionId = genKey ? `${studentId}::${genKey}` : studentId;

        const gen = {
            status: "generating",
            fullAnswer: "",
            isFirstToken: true,
            loadingBox: loadingBox,
            rowEl: loadingBox._rowEl,
            userRowEl: userMsgBox._rowEl,  // แถวข้อความคำถามของผู้ใช้ — เก็บไว้ด้วย เผื่อสลับแชทออกไปแล้วกลับมาก่อนตอบจบ จะได้แปะคำถามคืนมาด้วย ไม่ใช่แค่คำตอบลอยๆ
            abortController: new AbortController()
        };
        activeGenerations.set(genKey, gen);
        refreshSendButtonUI();  // genKey ตรงกับแชทที่เปิดอยู่ตอนนี้อยู่แล้ว จะเปลี่ยนปุ่มเป็นไอคอนหยุดทันที
        refreshHistoryList();   // ขึ้น ⏳ หน้าชื่อแชทนี้ในแถบประวัติ (ถ้ามีแชทอื่นให้เห็น)

        // เช็คทุกจุดที่จะแตะหน้าจอ (loadingBox/sendButton/scroll) ว่าผู้ใช้ยังดูแชทนี้อยู่จริง
        // หรือไม่ ก่อนอัปเดต — ถ้าสลับไปแชทอื่นแล้ว จะข้ามการอัปเดตหน้าจอ (แต่ gen.fullAnswer/
        // loadingBox ยังถูกอัปเดตในตัวแปรตามปกติ รอไว้ให้ switchConversation ดึงกลับมาแสดงทีหลัง)
        const isStillViewing = () => activeConversationId === genKey;

        try {
            const response = await fetch(`${API}/api/chat/stream`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    ...authHeaders()
                },
                body: JSON.stringify({
                    message: text,
                    session_id: requestSessionId,
                    role:       userRole,
                    year: studentYear,
                    model: selectedAiModel  // ฟีเจอร์ใหม่: โมเดล AI ที่อาจารย์/บุคลากรเลือกไว้ (ว่าง = ใช้ค่าเริ่มต้นของระบบ) — backend เช็คสิทธิ์ role ซ้ำเสมอ
                }),
                signal: gen.abortController.signal
            });

            if (response.status === 429) {
                const errData = await response.json().catch(() => ({}));
                loadingBox.classList.remove("typing-indicator");
                loadingBox.innerHTML = "";
                loadingBox.textContent = errData.detail || t("serverError");
                loadingBox.style.color = "red";
                updateMessageTime(loadingBox, new Date());
                return;
            }

            if (response.status === 401 || response.status === 403) {
                loadingBox.classList.remove("typing-indicator");
                loadingBox.innerHTML = "";
                // เซสชันหมดอายุกระทบทั้งหน้า (ไม่ใช่แค่แชทนี้) เลยพากลับไปหน้าล็อกอินเสมอ ไม่ว่า
                // ผู้ใช้จะยังดูแชทนี้อยู่หรือสลับไปแชทอื่นแล้วก็ตาม
                handleAuthError(response.status);
                return;
            }

            if (!response.ok || !response.body) {
                throw new Error("Network response was not ok");
            }

            let sawError = false;

            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let buffer = "";

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });

                let sepIndex;
                while ((sepIndex = buffer.indexOf("\n\n")) !== -1) {
                    const rawEvent = buffer.slice(0, sepIndex).trim();
                    buffer = buffer.slice(sepIndex + 2);
                    if (!rawEvent.startsWith("data:")) continue;
                    const jsonStr = rawEvent.slice(5).trim();
                    if (!jsonStr) continue;

                    let payload;
                    try {
                        payload = JSON.parse(jsonStr);
                    } catch (parseErr) {
                        continue;
                    }

                    if (payload.type === "token") {
                        if (gen.isFirstToken) {
                            loadingBox.classList.remove("typing-indicator");
                            loadingBox.innerHTML = "";
                            gen.isFirstToken = false;
                        }
                        gen.fullAnswer += payload.content;
                        loadingBox.textContent = gen.fullAnswer;
                        if (isStillViewing()) chatDisplay.scrollTop = chatDisplay.scrollHeight;
                    } else if (payload.type === "meta") {
                        // ฟีเจอร์ใหม่: backend แจ้งชื่อโมเดลจริงที่ใช้ตอบคำถามนี้กลับมา (ดู
                        // /api/chat/stream ใน main.py) — แสดงเป็นป้ายเล็กๆ ใต้คำตอบ เฉพาะ
                        // อาจารย์/บุคลากรเท่านั้น (นักศึกษาใช้โมเดลเริ่มต้นของระบบเสมอ ไม่ต้อง
                        // โชว์ให้รก) เพื่อยืนยันได้จริงว่าคำตอบมาจากโมเดลที่เลือกไว้หรือไม่
                        if (userRole === "teacher" && payload.model) {
                            let modelContainer = loadingBox.parentNode.querySelector(".model-tag-container");
                            if (!modelContainer) {
                                modelContainer = document.createElement("div");
                                modelContainer.className = "model-tag-container";
                                modelContainer.style.fontSize = "11px";
                                modelContainer.style.color = "#a0a0a0";
                                modelContainer.style.marginTop = "4px";
                                modelContainer.textContent = "🤖 ตอบโดยโมเดล: " + payload.model;
                                loadingBox.parentNode.appendChild(modelContainer);
                            }
                        }
                    } else if (payload.type === "sources") {
                        if (payload.sources && payload.sources.length > 0) {
                            let sourceContainer = loadingBox.parentNode.querySelector(".source-tag-container");
                            if (!sourceContainer) {
                                sourceContainer = document.createElement("div");
                                sourceContainer.className = "source-tag-container";
                                sourceContainer.style.fontSize = "11px";
                                sourceContainer.style.color = "#a0a0a0";
                                sourceContainer.style.marginTop = "6px";
                                sourceContainer.style.borderTop = "1px solid rgba(255,255,255,0.1)";
                                sourceContainer.style.paddingTop = "4px";
                                sourceContainer.textContent = " แหล่งที่มา: " + [...new Set(payload.sources.map(s => s.source))].join(", ");
                                loadingBox.parentNode.appendChild(sourceContainer);
                            }
                        }
                    } else if (payload.type === "error") {
                        sawError = true;
                        if (gen.isFirstToken) {
                            loadingBox.classList.remove("typing-indicator");
                            loadingBox.innerHTML = "";
                            gen.isFirstToken = false;
                        }
                        loadingBox.textContent = payload.message || t("serverError");
                        loadingBox.style.color = "red";
                    }
                }
            }

            if (!sawError && !gen.fullAnswer) {
                if (gen.isFirstToken) {
                    loadingBox.classList.remove("typing-indicator");
                    loadingBox.innerHTML = "";
                }
                loadingBox.textContent = t("serverError");
                loadingBox.style.color = "red";
            }
            updateMessageTime(loadingBox, new Date());

        } catch (error) {
            // ดักจับจังหวะที่ผู้ใช้กดปุ่ม Stop (AbortError)
            if (error.name === 'AbortError') {
                loadingBox.classList.remove("typing-indicator");
                loadingBox.innerHTML = ""; // ลบจุดสามจุดทิ้งทันที

                // หากยังไม่มีข้อความตอบกลับมาเลย ให้แสดงข้อความแจ้งเตือนตามที่ต้องการ
                if (!gen.fullAnswer || gen.fullAnswer.trim() === "") {
                    loadingBox.textContent = "ถามคำถามใหม่ได้เลยค่ะ";
                }
                updateMessageTime(loadingBox, new Date());
            } else {
                loadingBox.classList.remove("typing-indicator");
                loadingBox.innerHTML = "";
                loadingBox.textContent = t("serverError");
                loadingBox.style.color = "red";
                updateMessageTime(loadingBox, new Date());
            }
        } finally {
            // จบการตอบของแชทนี้แล้ว (ตอบสำเร็จ/error/ถูกกด stop) — ไม่ต้องเก็บสถานะไว้ใน
            // activeGenerations อีกต่อไป (ถ้าตอบสำเร็จ backend บันทึกลง DB ไปแล้ว ครั้งหน้าที่
            // สลับมาแชทนี้ก็จะโหลดได้ถูกต้องจากฐานข้อมูลอยู่แล้ว) แล้วอัปเดตปุ่ม/แถบประวัติ
            // เฉพาะตอนที่ยังอยู่ในแชทนี้จริง (ถ้าสลับไปแชทอื่นแล้ว ปุ่ม/แถบของแชทอื่นจะยังคง
            // สภาพเดิมไม่ถูกรบกวน)
            activeGenerations.delete(genKey);
            if (isStillViewing()) refreshSendButtonUI();
            refreshHistoryList();
        }
    });

    // หมายเหตุ: โค้ดสองก้อนด้านล่างนี้ (คอมเมนต์ /* ... */ ทั้งหมดยาวถึงบรรทัด ~1007) เป็น
    // "sendButton" เวอร์ชันเก่า 2 รุ่นที่ถูกแทนที่ด้วยเวอร์ชันปัจจุบันด้านบนแล้ว (รุ่นแรกสุด
    // ยังไม่มีสตรีมคำตอบทีละ token, รุ่นถัดมามีสตรีมแต่ยังไม่รองรับสลับแชทระหว่างตอบ/เวลา
    // ข้อความ) เก็บไว้เฉยๆ เป็นข้อมูลอ้างอิงประวัติการพัฒนา ไม่ได้ถูกเรียกใช้งานจริง (dead code)
    // ลบทิ้งได้อย่างปลอดภัยถ้าต้องการให้ไฟล์สั้นลง
/*     sendButton.addEventListener("click", async function() {
        const text = inputMessage.value.trim();
        if (text !== "") {
            // แสดงข้อความนักศึกษา
            appendMessage(text, "user", new Date());
            inputMessage.value = "";

            // แสดงกล่องสถานะกำลังคิด (จุด 3 จุดจะค้างไว้ตรงนี้ยาวๆ จนกว่า AI จะตอบเสร็จ)
            const loadingBox = appendMessage("", "bot", new Date());
            loadingBox.classList.add("typing-indicator");
            loadingBox.innerHTML =
                '<span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>';

            try {
                const response = await fetch(`${API}/api/chat/stream`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        ...authHeaders()
                    },
                    body: JSON.stringify({
                        message: text,
                        session_id: currentSessionId(),
                        role:       userRole,
                        year: studentYear
                    })
                });

                if (response.status === 429) {
                    const errData = await response.json().catch(() => ({}));
                    loadingBox.classList.remove("typing-indicator");
                    loadingBox.innerHTML = "";
                    loadingBox.textContent = errData.detail || t("serverError");
                    loadingBox.style.color = "red";
                    updateMessageTime(loadingBox, new Date());
                    return;
                }

                if (response.status === 401 || response.status === 403) {
                    loadingBox.classList.remove("typing-indicator");
                    loadingBox.innerHTML = "";
                    handleAuthError(response.status);
                    return;
                }

                if (!response.ok || !response.body) {
                    throw new Error("Network response was not ok (Status: " + response.status + ")");
                }

                let fullAnswer = "";
                let sawError = false;
                let isFirstToken = true;

                const reader = response.body.getReader();
                const decoder = new TextDecoder("utf-8");
                let buffer = "";

                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;
                    buffer += decoder.decode(value, { stream: true });

                    let sepIndex;
                    while ((sepIndex = buffer.indexOf("\n\n")) !== -1) {
                        const rawEvent = buffer.slice(0, sepIndex).trim();
                        buffer = buffer.slice(sepIndex + 2);
                        if (!rawEvent.startsWith("data:")) continue;
                        const jsonStr = rawEvent.slice(5).trim();
                        if (!jsonStr) continue;

                        let payload;
                        try {
                            payload = JSON.parse(jsonStr);
                        } catch (parseErr) {
                            continue;
                        }

                        if (payload.type === "token") {
                            // เมื่อได้รับคำตอบคำแรกจาก AI ค่อยเอาจุด 3 จุดออก
                            if (isFirstToken) {
                                loadingBox.classList.remove("typing-indicator");
                                loadingBox.innerHTML = "";
                                isFirstToken = false;
                            }

                            fullAnswer += payload.content;
                            loadingBox.textContent = fullAnswer; 
                            chatDisplay.scrollTop = chatDisplay.scrollHeight;
                        } else if (payload.type === "sources") {
                            // แสดงแหล่งที่มาด้านล่าง
                            if (payload.sources && payload.sources.length > 0) {
                                let sourceContainer = loadingBox.parentNode.querySelector(".source-tag-container");
                                if (!sourceContainer) {
                                    sourceContainer = document.createElement("div");
                                    sourceContainer.className = "source-tag-container";
                                    sourceContainer.style.fontSize = "11px";
                                    sourceContainer.style.color = "#a0a0a0";
                                    sourceContainer.style.marginTop = "6px";
                                    sourceContainer.style.borderTop = "1px solid rgba(255,255,255,0.1)";
                                    sourceContainer.style.paddingTop = "4px";
                                    sourceContainer.textContent = "📖 แหล่งที่มา: " + [...new Set(payload.sources.map(s => s.source))].join(", ");
                                    loadingBox.parentNode.appendChild(sourceContainer);
                                }
                            }
                        } else if (payload.type === "error") {
                            sawError = true;
                            if (isFirstToken) {
                                loadingBox.classList.remove("typing-indicator");
                                loadingBox.innerHTML = "";
                                isFirstToken = false;
                            }
                            loadingBox.textContent = payload.message || t("serverError");
                            loadingBox.style.color = "red";
                        }
                    }
                }

                if (!sawError && !fullAnswer) {
                    if (isFirstToken) {
                        loadingBox.classList.remove("typing-indicator");
                        loadingBox.innerHTML = "";
                    }
                    loadingBox.textContent = "⚠️ ไม่ได้รับข้อมูลตอบกลับจาก AI (โมเดลอาจจะใช้เวลาประมวลผลนานเกินไป)";
                    loadingBox.style.color = "orange";
                }
                updateMessageTime(loadingBox, new Date());

            } catch (error) {
                console.error("Chat Stream Error:", error); // พิมพ์ Error ลงใน Console ของเบราว์เซอร์เพื่อให้เช็คได้
                loadingBox.classList.remove("typing-indicator");
                loadingBox.innerHTML = "";
                loadingBox.textContent = "❌ เกิดข้อผิดพลาดในการเชื่อมต่อ (ลองเช็ค Terminal ของ Python ดูว่ามี Error สีแดงขึ้นไหม)";
                loadingBox.style.color = "red";
                updateMessageTime(loadingBox, new Date());
            }
        }
    }); */
    /*sendButton.addEventListener("click", async function() {
        const text = inputMessage.value.trim();
        if (text !== "") {
            // แสดงข้อความนักศึกษา — ประทับเวลาที่กดส่งจริงไว้ด้วย (ฟีเจอร์ใหม่ ดู formatTimeHMS
            // ด้านล่าง มีวินาทีด้วยตามที่ขอ)
            appendMessage(text, "user", new Date());
            inputMessage.value = "";

            // แสดงกล่องสถานะกำลังคิด — ใช้ตัวบ่งชี้ "กำลังพิมพ์..." (จุด 3 จุดขยับไปมา)
            // แทนข้อความนิ่งๆ เดิม ให้ดูเหมือนบอทกำลังพิมพ์อยู่จริง — ประทับเวลาตอนเริ่มส่งคำถาม
            // ไปเช่นกัน (ไม่ใช่เวลาที่ AI ตอบเสร็จ) ให้ตรงกับเวลาบนบับเบิลของฝั่งผู้ใช้ที่อยู่คู่กัน
            const loadingBox = appendMessage("", "bot", new Date());
            loadingBox.classList.add("typing-indicator");
            loadingBox.innerHTML =
                '<span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>';

            try {
                // ส่งคำถามไปหา Python ผ่าน endpoint สตรีม (/api/chat/stream) แทน /chat เดิม
                // ที่ต้องรอคำตอบเต็มก้อนก่อนถึงจะเห็นอะไรเลย — ตอนนี้ตัวอักษรจะทยอยขึ้นทีละส่วน
                // เหมือน ChatGPT ทำให้รู้สึกว่าระบบตอบสนองเร็วขึ้นจริง (แก้ตรงจุดที่แบบประเมิน
                // ชี้ว่าคะแนนต่ำสุดคือ "ระบบตอบสนองได้รวดเร็ว") backend endpoint นี้กรองตาม
                // role/year เหมือน /chat ทุกประการอยู่แล้ว (ดู retrieve_chunks ใน main.py)
                const response = await fetch(`${API}/api/chat/stream`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        ...authHeaders()
                    },
                    body: JSON.stringify({
                        message: text,
                        session_id: currentSessionId(),
                        role:       userRole,
                        year: studentYear
                    })
                });

                if (response.status === 429) {
                    const errData = await response.json().catch(() => ({}));
                    loadingBox.classList.remove("typing-indicator");
                    loadingBox.innerHTML = "";
                    loadingBox.textContent = errData.detail || t("serverError");
                    loadingBox.style.color = "red";
                    updateMessageTime(loadingBox, new Date());
                    return;
                }

                if (response.status === 401 || response.status === 403) {
                    loadingBox.classList.remove("typing-indicator");
                    loadingBox.innerHTML = "";
                    handleAuthError(response.status);
                    return;
                }

                if (!response.ok || !response.body) {
                    throw new Error("Network response was not ok");
                }

                // เคลียร์ตัวบ่งชี้ "กำลังพิมพ์..." ทันทีที่ต่อสตรีมได้สำเร็จ แล้วค่อยๆ เติม
                // ข้อความทีละ token ที่ backend ส่งมาแทน (ดู event type "token" ด้านล่าง)
                loadingBox.classList.remove("typing-indicator");
                loadingBox.innerHTML = "";
                let sawError = false;

                // อ่าน response แบบสตรีมด้วย ReadableStream reader (ใช้ fetch ธรรมดาแทน
                // EventSource เพราะ EventSource รองรับเฉพาะ GET เท่านั้น ส่ง POST body ไม่ได้)
                // รูปแบบข้อความจาก backend เป็น Server-Sent Events: "data: {...}\n\n" ต่อ 1 event
                const reader = response.body.getReader();
                const decoder = new TextDecoder("utf-8");
                let buffer = "";

                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;
                    buffer += decoder.decode(value, { stream: true });

                    let sepIndex;
                    while ((sepIndex = buffer.indexOf("\n\n")) !== -1) {
                        const rawEvent = buffer.slice(0, sepIndex).trim();
                        buffer = buffer.slice(sepIndex + 2);
                        if (!rawEvent.startsWith("data:")) continue;
                        const jsonStr = rawEvent.slice(5).trim();
                        if (!jsonStr) continue;

                        let payload;
                        try {
                            payload = JSON.parse(jsonStr);
                        } catch (parseErr) {
                            continue; // ข้าม event ที่ parse ไม่ได้ ไม่ทำให้ทั้งสตรีมพัง
                        }

                        if (payload.type === "token") {
                            loadingBox.textContent += payload.content;
                            chatDisplay.scrollTop = chatDisplay.scrollHeight;
                        } else if (payload.type === "error") {
                            sawError = true;
                            loadingBox.textContent = payload.message || t("serverError");
                            loadingBox.style.color = "red";
                        }
                        // type === "sources"/"done" ไม่ต้องทำอะไรเพิ่มในหน้าแชทนี้ (sources มีไว้
                        // สำหรับ debug ฝั่ง dev console เท่านั้น)
                    }
                }

                if (!sawError && !loadingBox.textContent) {
                    loadingBox.textContent = t("serverError");
                    loadingBox.style.color = "red";
                }
                // อัปเดตเวลาให้เป็นตอนที่ตอบเสร็จจริง (ไม่ใช่เวลาตอนเริ่มถามที่ประทับไว้ตอน
                // สร้างกล่อง "กำลังพิมพ์..." ด้านบน) ตามที่ขอ — เวลา ณ ปัจจุบันตอนตอบมาจริงๆ
                updateMessageTime(loadingBox, new Date());

            } catch (error) {
                loadingBox.classList.remove("typing-indicator");
                loadingBox.innerHTML = "";
                loadingBox.textContent = t("serverError");
                loadingBox.style.color = "red";
                updateMessageTime(loadingBox, new Date());
            }
        }
    }); */

    if (newChatButton) {
        // เดิมปุ่มนี้ล้างประวัติทิ้งถาวรผ่าน /reset-memory ตอนนี้เปลี่ยนเป็น "สร้างแชทเธรดใหม่"
        // แทน (ดูฟังก์ชัน startNewConversation ด้านบน) — แชทเก่ายังอยู่ครบ ดูย้อนหลังได้จาก
        // แถบประวัติแชท ไม่หายไปไหนเหมือนพฤติกรรมเดิมอีกต่อไป
        newChatButton.addEventListener("click", startNewConversation);
    }

    function appendMessage(text, sender, timestamp) {
        // แถวครอบ [อวตาร์ + บับเบิลข้อความ] คู่กัน แล้วจัดชิดซ้าย/ขวาตามฝั่งผู้ส่ง
        // (ไม่แก้สไตล์เดิมของ msgBox เลยแม้แต่บรรทัดเดียว แค่ครอบด้วย row เพิ่ม)
        const row = document.createElement("div");
        row.style.display = "flex";
        row.style.alignItems = "flex-end";
        row.style.gap = "8px";
        row.style.marginBottom = "15px";
        row.style.justifyContent = sender === "user" ? "flex-end" : "flex-start";

        // คอลัมน์ครอบ [บับเบิลข้อความ + เวลา] (ฟีเจอร์ใหม่) ให้เวลาซ้อนอยู่ใต้บับเบิลพอดี
        // แยกจาก row เดิม เพราะฝั่งบอทมีอวตารอยู่ข้างๆ ด้วย ถ้าใส่เวลาไว้ใน row ตรงๆ
        // เวลาจะไปโผล่ใต้อวตารแทนที่จะอยู่ใต้บับเบิล จึงต้องมีคอลัมน์ย่อยนี้มาครอบเฉพาะบับเบิล
        const bubbleColumn = document.createElement("div");
        bubbleColumn.style.display = "flex";
        bubbleColumn.style.flexDirection = "column";
        bubbleColumn.style.alignItems = sender === "user" ? "flex-end" : "flex-start";
        bubbleColumn.style.maxWidth = "70%";
        bubbleColumn.style.minWidth = "0";

        const msgBox = document.createElement("div");
        msgBox.textContent = text;
        msgBox.style.padding = "10px 15px";
        msgBox.style.maxWidth = "100%";
        msgBox.style.width = "fit-content";
        msgBox.style.fontFamily = "'Prompt', sans-serif";
        msgBox.style.lineHeight = "1.5";

        if (sender === "user") {
            // ฝั่งผู้ใช้ไม่มีรูปอวตาร์แล้ว แสดงแค่บับเบิลข้อความ
            msgBox.style.background = "linear-gradient(135deg, #a8e063 0%, #56ab2f 100%)";
            msgBox.style.color = "white";
            msgBox.style.borderRadius = "15px 15px 0px 15px";
            bubbleColumn.appendChild(msgBox);
            row.appendChild(bubbleColumn);
        } else {
            const avatar = document.createElement("div");
            avatar.className = "chat-avatar";
            const img = document.createElement("img");
            img.src = "mascot.png";
            img.className = "chat-avatar-img";
            avatar.appendChild(img);

            msgBox.style.backgroundColor = "#430d0a";
            msgBox.style.color = "#ffffff";
            msgBox.style.borderRadius = "15px 15px 15px 0px";
            bubbleColumn.appendChild(msgBox);
            row.appendChild(avatar);
            row.appendChild(bubbleColumn);
        }

        // เวลาส่ง/ตอบข้อความ (ฟีเจอร์ใหม่ตามที่ขอ — เป็นเวลา ณ ปัจจุบัน มีวินาทีด้วย)
        // แสดงเฉพาะข้อความที่เกิดขึ้นสดๆ ในเซสชันนี้เท่านั้น (ดูจุดที่เรียก appendMessage
        // ประกอบ) ข้อความเก่าที่โหลดย้อนหลังมาจาก backend จะไม่ส่ง timestamp เข้ามา
        // (เพราะ backend ไม่ได้เก็บเวลาจริงตอนส่งไว้) จึงไม่มีเวลาโชว์ กันไม่ให้เข้าใจผิด
        // ว่าเป็นเวลาที่ส่งจริง
        if (timestamp) {
            const timeEl = document.createElement("span");
            timeEl.className = "msg-time";
            timeEl.textContent = formatTimeHMS(timestamp);
            bubbleColumn.appendChild(timeEl);
            // เก็บ reference ของ span เวลาไว้ที่ตัว msgBox เอง เพื่อให้จุดที่เรียก
            // appendMessage ตอนแรก (เช่น กล่อง "กำลังพิมพ์...") กลับมาอัปเดตเวลาใหม่ได้อีกครั้ง
            // ตอนคำตอบจริงมาถึง (ดู updateMessageTime ด้านล่าง + จุดเรียกใน sendButton handler)
            msgBox._timeEl = timeEl;
        }

        // เก็บ reference ของ "row" ครอบทั้งแถว (อวตาร+บับเบิล) ไว้ที่ msgBox ด้วย — ใช้ตอนสลับแชท
        // ระหว่างที่ AI กำลังตอบอยู่ (ดู activeGenerations/switchConversation ด้านล่าง) เพื่อดึง
        // แถวนี้กลับมาแปะใหม่ในหน้าจอได้ถูกต้อง ถ้าผู้ใช้สลับกลับมาดูแชทนี้อีกครั้งระหว่างตอบ
        msgBox._rowEl = row;

        chatDisplay.appendChild(row);
        chatDisplay.scrollTop = chatDisplay.scrollHeight;

        return msgBox;
    }

    // แปลงเวลาเป็นข้อความรูปแบบ HH:MM:SS แบบตายตัว (ฟีเจอร์ใหม่) — ตั้งใจไม่ใช้
    // toLocaleTimeString() เพราะรูปแบบจะเปลี่ยนไปตาม locale/OS ของเครื่องผู้ใช้แต่ละคน
    // (บางเครื่องได้ AM/PM บางเครื่องไม่มีวินาที) ทำให้เวลาที่โชว์ไม่สม่ำเสมอกัน จึงประกอบ
    // สตริงเองด้วย padStart ให้ได้ผลลัพธ์แบบเดียวกันทุกเครื่อง (มีวินาทีด้วยตามที่ขอ)
    function formatTimeHMS(date) {
        const pad = n => String(n).padStart(2, "0");
        return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
    }

    // อัปเดตเวลาที่โชว์ใต้บับเบิลของ msgBox ที่มีอยู่แล้วให้เป็นเวลาปัจจุบัน ณ ตอนนี้
    // (ฟีเจอร์ใหม่ — แก้ปัญหาที่กล่อง "กำลังพิมพ์..." ประทับเวลาไว้ตั้งแต่ตอนเริ่มถาม
    // ทำให้เวลาที่โชว์บนคำตอบจริงกลายเป็นเวลาที่ถามไป ไม่ใช่เวลาที่ตอบเสร็จจริง)
    function updateMessageTime(msgBox, date) {
        if (msgBox && msgBox._timeEl) {
            msgBox._timeEl.textContent = formatTimeHMS(date);
        }
    }
}

// ==========================================
// 4. ส่วนของหน้าเข้าสู่ระบบแอดมิน (Admin Login)
// ==========================================
const adminLoginBtn = document.getElementById("submit5");

if (adminLoginBtn) {
    const adminLoginForm = adminLoginBtn.closest("form");

    if (adminLoginForm) {
        adminLoginForm.addEventListener("submit", async function(event) {
            event.preventDefault();

            const emailInput = document.getElementById("adminlog") || document.getElementById("emailadmin");
            const passInput = document.getElementById("input-passwordlog") || document.getElementById("passwordadmin");

            if (emailInput && passInput && emailInput.value.trim() !== "" && passInput.value.trim() !== "") {

                try {
                    const response = await fetch(`${API}/admin/login`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            username: emailInput.value.trim(),
                            password: passInput.value.trim()
                        })
                    });

                    if (response.ok) {
                        const data = await response.json();
                        // เก็บ token ไว้ใช้ยืนยันตัวตนตอนอัปโหลดไฟล์ (หายเมื่อปิดแท็บ)
                        sessionStorage.setItem("admin_token", data.token);
                        alert(t("adminLoginSuccess"));
                        window.location.href = "upload.html";
                    } else {
                        alert(t("adminLoginFail"));
                    }
                } catch (error) {
                    alert(t("adminLoginServerError"));
                }

            } else {
                alert(t("adminLoginEmpty"));
            }
        });
    }
}

// ==========================================
// (เดิมส่วนที่ 5 เป็นฟอร์มลงทะเบียนแอดมิน (Register Admin) เรียก POST /admin/register —
// ลบออกแล้ว เพราะเป็น dead code: admin.html ไม่มีฟอร์มลงทะเบียนอีกต่อไป (ระบบอนุญาตแอดมิน
// บัญชีเดียวเท่านั้น เปลี่ยนเป็นข้อความ+ลิงก์กลับหน้าล็อกอินแทน) และ backend (main.py) ก็ไม่มี
// endpoint /admin/register อยู่แล้วด้วย โค้ดส่วนนี้จึงไม่เคยถูกเรียกใช้งานจริงเลย)
// ==========================================
// 6. ส่วนของหน้าจัดการไฟล์คู่มือ (Edit/Upload) -  เชื่อม Backend แล้ว
// ==========================================
const uploadForm = document.getElementById("uploadForm");
const searchForm = document.getElementById("searchForm");
const fileTableBody = document.getElementById("fileTableBody");

// หน้านี้ต้อง login แอดมินก่อนถึงจะใช้ได้ — ถ้าไม่มี token เลยไม่ต้องปล่อยให้เห็นหน้านี้
if (uploadForm && !sessionStorage.getItem("admin_token")) {
    alert("กรุณาเข้าสู่ระบบแอดมินก่อน");
    window.location.href = "loginadmin.html";
}

// แสดงปีการศึกษาของแต่ละไฟล์เป็นข้อความล้วน (เอาช่องแก้ไข + ปุ่มบันทึกออกแล้วตามที่ขอ
// ถ้าจะแก้ปีของไฟล์ ต้องลบแล้วอัปโหลดใหม่พร้อมระบุปีในฟอร์มด้านบนแทน)
function renderFileRow(rowNumber, filename, year) {
    const row = document.createElement("tr");
    row.innerHTML = `
        <td>${rowNumber}</td>
        <td>${escapeHtml(filename)}</td>
        <td>${escapeHtml(year || "ทุกรุ่น")}</td>
        <td class="row-actions">
            <span class="status-badge">✅ อัปเดตแล้ว</span>
            <button type="button" class="delete-file-btn">ลบ</button>
        </td>
    `;

    const deleteBtn = row.querySelector(".delete-file-btn");

    // ปุ่มลบไฟล์ (แอดมิน) — เชื่อมกับ /admin/files/{filename} ที่เพิ่มใหม่ใน main.py
    // ลบทั้งไฟล์บนดิสก์และ chunk ที่เกี่ยวข้องใน vector store แล้วเอาแถวออกจากตารางทันที
    deleteBtn.addEventListener("click", async function() {
        const confirmed = confirm(
            `ยืนยันลบไฟล์ "${filename}" ถาวรหรือไม่?\n` +
            `การลบจะเอาทั้งไฟล์และข้อมูลที่ AI ใช้ตอบคำถามจากไฟล์นี้ออกทั้งหมด กู้คืนไม่ได้`
        );
        if (!confirmed) return;

        const adminToken = sessionStorage.getItem("admin_token");
        deleteBtn.disabled = true;
        const originalLabel = deleteBtn.textContent;
        deleteBtn.textContent = "กำลังลบ...";

        try {
            const response = await fetch(`${API}/admin/files/${encodeURIComponent(filename)}`, {
                method: "DELETE",
                headers: { "Authorization": "Bearer " + adminToken }
            });

            if (response.status === 401) {
                sessionStorage.removeItem("admin_token");
                alert("เซสชันหมดอายุ กรุณาเข้าสู่ระบบใหม่");
                window.location.href = "loginadmin.html";
                return;
            }

            const data = await response.json();
            if (response.ok) {
                row.remove();
                // เรียงเลขลำดับใหม่ให้ต่อเนื่องหลังลบแถวออก
                if (fileTableBody) {
                    Array.from(fileTableBody.children).forEach((r, i) => {
                        if (r.children[0]) r.children[0].textContent = i + 1;
                    });
                }
            } else {
                alert("ลบไม่สำเร็จ: " + (data.detail || ""));
                deleteBtn.disabled = false;
                deleteBtn.textContent = originalLabel;
            }
        } catch (error) {
            alert(t("uploadServerError"));
            deleteBtn.disabled = false;
            deleteBtn.textContent = originalLabel;
        }
    });

    return row;
}

// โหลดรายการไฟล์คู่มือทั้งหมดจาก backend ตอนเปิดหน้า (ไฟล์เก่าที่เคยอัปโหลดไว้จะเห็นด้วย
// ไม่ใช่ว่างเปล่าทุกครั้งที่รีเฟรชแบบเดิม)
async function loadFileTable() {
    if (!fileTableBody) return;
    const adminToken = sessionStorage.getItem("admin_token");
    try {
        const response = await fetch(`${API}/admin/files`, {
            headers: { "Authorization": "Bearer " + adminToken }
        });
        if (response.status === 401) {
            sessionStorage.removeItem("admin_token");
            alert("เซสชันหมดอายุ กรุณาเข้าสู่ระบบใหม่");
            window.location.href = "loginadmin.html";
            return;
        }
        const data = await response.json();
        fileTableBody.innerHTML = "";
        (data.files || []).forEach((f, i) => {
            fileTableBody.appendChild(renderFileRow(i + 1, f.source, f.year));
        });
    } catch (error) {
        // เชื่อมต่อ backend ไม่ได้ตอนโหลดหน้า — ปล่อยตารางว่างไว้ ไม่ต้อง alert รบกวน
    }
}
loadFileTable();

if (uploadForm) {
    uploadForm.addEventListener("submit", async function(event) {
        event.preventDefault();

        const fileUpload = document.getElementById("fileUpload");
        const fileYear = document.getElementById("fileYear");
        const submitBtn = uploadForm.querySelector('input[type="submit"]');
        const adminToken = sessionStorage.getItem("admin_token");

        if (fileUpload && fileUpload.files.length > 0) {
            const file = fileUpload.files[0];
            const yearValue = (fileYear ? fileYear.value : "").trim();

            if (yearValue && !/^\d{2}$/.test(yearValue)) {
                alert("กรุณากรอกรหัสรุ่น 2 หลัก เช่น 66 หรือเว้นว่างไว้");
                return;
            }

            const formData = new FormData();
            formData.append("file", file);
            formData.append("year", yearValue);

            // เปลี่ยนปุ่มเป็นสถานะกำลังโหลด
            submitBtn.value = t("uploading");
            submitBtn.disabled = true;
            submitBtn.style.backgroundColor = "gray";

            try {
                const response = await fetch(`${API}/admin/upload`, {
                    method: "POST",
                    headers: { "Authorization": "Bearer " + adminToken },
                    body: formData
                });

                // เซสชันหมดอายุ/ไม่ถูกต้อง -> ให้ login ใหม่
                if (response.status === 401) {
                    sessionStorage.removeItem("admin_token");
                    alert("เซสชันหมดอายุ กรุณาเข้าสู่ระบบใหม่");
                    window.location.href = "loginadmin.html";
                    return;
                }

                const data = await response.json();

                if (response.ok) {
                    alert(data.message || t("uploadSuccess"));

                    if (fileTableBody) {
                        const rowCount = fileTableBody.children.length + 1;
                        fileTableBody.appendChild(
                            renderFileRow(rowCount, data.filename || file.name, data.year || yearValue)
                        );
                    }
                    fileUpload.value = "";
                    if (fileYear) fileYear.value = "";
                } else {
                    alert("เกิดข้อผิดพลาด: " + data.detail);
                }

            } catch (error) {
                alert(t("uploadServerError"));
            } finally {
                submitBtn.value = t("uploadBtn");
                submitBtn.disabled = false;
                submitBtn.style.backgroundColor = "";
            }

        } else {
            alert(t("uploadEmpty"));
        }
    });
}

// ป้องกันชื่อไฟล์ที่มีอักขระ HTML พิเศษ ไม่ให้กลายเป็นโค้ดที่รันได้ (XSS)
function escapeHtml(s){
  return String(s).replace(/[&<>"']/g, c => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[c]));
}

// 6.2 การจัดการปุ่ม "ค้นหาไฟล์" — เชื่อมกับ backend endpoint /admin/files/search ที่มีอยู่แล้ว
// (เดิมเป็นแค่ mockup ที่ alert ข้อความเฉยๆ ตอนนี้ค้นหาไฟล์จริงและอัปเดตตารางให้)
if (searchForm) {
    searchForm.addEventListener("submit", async function(event) {
        event.preventDefault();

        const searchInput = document.getElementById("searchInput");
        const keyword = searchInput ? searchInput.value.trim() : "";
        const adminToken = sessionStorage.getItem("admin_token");

        try {
            const response = await fetch(`${API}/admin/files/search?q=${encodeURIComponent(keyword)}`, {
                headers: { "Authorization": "Bearer " + adminToken }
            });

            if (response.status === 401) {
                sessionStorage.removeItem("admin_token");
                alert("เซสชันหมดอายุ กรุณาเข้าสู่ระบบใหม่");
                window.location.href = "loginadmin.html";
                return;
            }

            const data = await response.json();
            if (fileTableBody) {
                fileTableBody.innerHTML = "";
                (data.files || []).forEach((f, i) => {
                    fileTableBody.appendChild(renderFileRow(i + 1, f.source, f.year));
                });
            }
        } catch (error) {
            alert(t("uploadServerError"));
        }
    });
}

// ==========================================
// 7. จัดการ "คำถามแนะนำประจำปี" (upload.html ฝั่งแอดมิน) — เชื่อมกับ backend ใหม่
//    /admin/suggested-questions (เพิ่ม/แก้ไข/ลบ) — เป็นไกด์ไลน์คำถามที่ผู้ใช้แต่ละรุ่น
//    จะเห็นเป็นปุ่มลัดในหน้าแชท (ดู "คำถามแนะนำประจำปี" ในส่วนหน้าแชทด้านบนของไฟล์นี้)
//    ฟีเจอร์ใหม่ทั้งหมด แยกจากการจัดการไฟล์เอกสารเดิม (ส่วนที่ 6) โดยสิ้นเชิง
// ==========================================
const sqForm = document.getElementById("sqForm");
const sqTableBody = document.getElementById("sqTableBody");

function renderSqRow(rowNumber, item) {
    const row = document.createElement("tr");
    row.innerHTML = `
        <td>${rowNumber}</td>
        <td>${escapeHtml(item.year || "ทุกรุ่น")}</td>
        <td style="text-align:left;">${escapeHtml(item.question)}</td>
        <td class="row-actions">
            <button type="button" class="sq-edit-btn">แก้ไข</button>
            <button type="button" class="delete-file-btn sq-delete-btn">ลบ</button>
        </td>
    `;

    const editBtn   = row.querySelector(".sq-edit-btn");
    const deleteBtn = row.querySelector(".sq-delete-btn");

    // แก้ไขคำถามแนะนำ/ปีที่ผูกไว้ — ใช้ prompt() ให้สอดคล้องกับรูปแบบเดิมของ
    // ระบบ (เช่น การตั้งชื่อผู้ใช้ในหน้าแชท) แทนการเพิ่มฟอร์มแก้ไขแยกซับซ้อน
    editBtn.addEventListener("click", async function() {
        const newQuestion = prompt("แก้ไขคำถามแนะนำ:", item.question);
        if (newQuestion === null || newQuestion.trim() === "") return;

        const newYear = prompt(
            "รหัสรุ่น 2 หลัก เช่น 66 (เว้นว่างไว้ถ้าเป็นคำถามกลางที่ทุกรุ่นเห็น):",
            item.year || ""
        );
        if (newYear === null) return;
        const yearValue = newYear.trim();
        if (yearValue && !/^\d{2}$/.test(yearValue)) { alert(t("sqYearFormatError")); return; }

        const adminToken = sessionStorage.getItem("admin_token");
        try {
            const response = await fetch(`${API}/admin/suggested-questions/${item.id}`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + adminToken
                },
                body: JSON.stringify({ year: yearValue, question: newQuestion.trim() })
            });
            if (response.status === 401) {
                sessionStorage.removeItem("admin_token");
                alert("เซสชันหมดอายุ กรุณาเข้าสู่ระบบใหม่");
                window.location.href = "loginadmin.html";
                return;
            }
            const data = await response.json();
            if (response.ok) {
                alert(data.message || t("sqUpdateSuccess"));
                loadSuggestedQuestionsAdmin();
            } else {
                alert("เกิดข้อผิดพลาด: " + data.detail);
            }
        } catch (error) {
            alert(t("sqServerError"));
        }
    });

    // ลบคำถามแนะนำถาวร — เชื่อมกับ DELETE /admin/suggested-questions/{id}
    deleteBtn.addEventListener("click", async function() {
        const confirmed = confirm(`ยืนยันลบคำถามแนะนำ "${item.question}" หรือไม่?`);
        if (!confirmed) return;

        const adminToken = sessionStorage.getItem("admin_token");
        deleteBtn.disabled = true;
        const originalLabel = deleteBtn.textContent;
        deleteBtn.textContent = "กำลังลบ...";

        try {
            const response = await fetch(`${API}/admin/suggested-questions/${item.id}`, {
                method: "DELETE",
                headers: { "Authorization": "Bearer " + adminToken }
            });
            if (response.status === 401) {
                sessionStorage.removeItem("admin_token");
                alert("เซสชันหมดอายุ กรุณาเข้าสู่ระบบใหม่");
                window.location.href = "loginadmin.html";
                return;
            }
            const data = await response.json();
            if (response.ok) {
                row.remove();
                if (sqTableBody) {
                    Array.from(sqTableBody.children).forEach((r, i) => {
                        if (r.children[0]) r.children[0].textContent = i + 1;
                    });
                    if (sqTableBody.children.length === 0) {
                        sqTableBody.innerHTML = `<tr><td colspan="4" class="sq-empty">ยังไม่มีคำถามแนะนำ</td></tr>`;
                    }
                }
            } else {
                alert("ลบไม่สำเร็จ: " + (data.detail || ""));
                deleteBtn.disabled = false;
                deleteBtn.textContent = originalLabel;
            }
        } catch (error) {
            alert(t("sqServerError"));
            deleteBtn.disabled = false;
            deleteBtn.textContent = originalLabel;
        }
    });

    return row;
}

// โหลดรายการคำถามแนะนำทั้งหมด (ทุกรุ่น + คำถามกลาง) มาเติมตารางตอนเปิดหน้า/หลังแก้ไข
async function loadSuggestedQuestionsAdmin() {
    if (!sqTableBody) return;
    const adminToken = sessionStorage.getItem("admin_token");
    try {
        const response = await fetch(`${API}/admin/suggested-questions`, {
            headers: { "Authorization": "Bearer " + adminToken }
        });
        if (response.status === 401) {
            sessionStorage.removeItem("admin_token");
            alert("เซสชันหมดอายุ กรุณาเข้าสู่ระบบใหม่");
            window.location.href = "loginadmin.html";
            return;
        }
        const data = await response.json();
        sqTableBody.innerHTML = "";
        const items = data.items || [];
        if (items.length === 0) {
            sqTableBody.innerHTML = `<tr><td colspan="4" class="sq-empty">ยังไม่มีคำถามแนะนำ</td></tr>`;
            return;
        }
        items.forEach((item, i) => {
            sqTableBody.appendChild(renderSqRow(i + 1, item));
        });
    } catch (error) {
        // เชื่อมต่อ backend ไม่ได้ตอนโหลดหน้า — ปล่อยตารางว่างไว้ ไม่ต้อง alert รบกวน
    }
}
loadSuggestedQuestionsAdmin();

// เพิ่มคำถามแนะนำใหม่ — เชื่อมกับ POST /admin/suggested-questions
if (sqForm) {
    sqForm.addEventListener("submit", async function(event) {
        event.preventDefault();

        const sqYearInput     = document.getElementById("sqYear");
        const sqQuestionInput = document.getElementById("sqQuestion");
        const submitBtn       = sqForm.querySelector('input[type="submit"]');
        const adminToken      = sessionStorage.getItem("admin_token");

        const yearValue     = (sqYearInput ? sqYearInput.value : "").trim();
        const questionValue = (sqQuestionInput ? sqQuestionInput.value : "").trim();

        if (!questionValue) { alert(t("sqEmptyQuestion")); return; }
        if (yearValue && !/^\d{2}$/.test(yearValue)) { alert(t("sqYearFormatError")); return; }

        submitBtn.disabled = true;
        try {
            const response = await fetch(`${API}/admin/suggested-questions`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + adminToken
                },
                body: JSON.stringify({ year: yearValue, question: questionValue })
            });
            if (response.status === 401) {
                sessionStorage.removeItem("admin_token");
                alert("เซสชันหมดอายุ กรุณาเข้าสู่ระบบใหม่");
                window.location.href = "loginadmin.html";
                return;
            }
            const data = await response.json();
            if (response.ok) {
                alert(data.message || t("sqAddSuccess"));
                if (sqYearInput) sqYearInput.value = "";
                if (sqQuestionInput) sqQuestionInput.value = "";
                loadSuggestedQuestionsAdmin();
            } else {
                alert("เกิดข้อผิดพลาด: " + data.detail);
            }
        } catch (error) {
            alert(t("sqServerError"));
        } finally {
            submitBtn.disabled = false;
        }
    });
}

// นำเข้าคำถามแนะนำจากไฟล์ Excel (.xlsx) แบบยกชุด — เชื่อมกับ
// POST /admin/suggested-questions/import ใน main.py ใช้กรณีมีคำถามจำนวนมากอยู่แล้ว
// ไม่ต้องกรอกทีละข้อผ่านฟอร์ม sqForm ด้านบน
const sqImportBtn  = document.getElementById("sqImportBtn");
const sqImportFile = document.getElementById("sqImportFile");
if (sqImportBtn) {
    sqImportBtn.addEventListener("click", async function() {
        if (!sqImportFile || !sqImportFile.files || sqImportFile.files.length === 0) {
            alert("กรุณาเลือกไฟล์ Excel (.xlsx) ก่อนกดนำเข้า");
            return;
        }
        const file = sqImportFile.files[0];
        const adminToken = sessionStorage.getItem("admin_token");
        const formData = new FormData();
        formData.append("file", file);

        sqImportBtn.disabled = true;
        const originalLabel = sqImportBtn.textContent;
        sqImportBtn.textContent = "กำลังนำเข้า...";

        try {
            const response = await fetch(`${API}/admin/suggested-questions/import`, {
                method: "POST",
                headers: { "Authorization": "Bearer " + adminToken },
                body: formData
            });
            if (response.status === 401) {
                sessionStorage.removeItem("admin_token");
                alert("เซสชันหมดอายุ กรุณาเข้าสู่ระบบใหม่");
                window.location.href = "loginadmin.html";
                return;
            }
            const data = await response.json();
            if (response.ok) {
                let msg = data.message || "นำเข้าคำถามแนะนำสำเร็จ";
                if (data.errors && data.errors.length > 0) {
                    msg += "\n\nแถวที่ข้าม:\n" + data.errors.join("\n");
                }
                alert(msg);
                sqImportFile.value = "";
                loadSuggestedQuestionsAdmin();
            } else {
                alert("นำเข้าไม่สำเร็จ: " + (data.detail || ""));
            }
        } catch (error) {
            alert(t("sqServerError"));
        } finally {
            sqImportBtn.disabled = false;
            sqImportBtn.textContent = originalLabel;
        }
    });
}
const changePasswordForm = document.getElementById("changePasswordForm");
if (changePasswordForm) {
    changePasswordForm.addEventListener("submit", async function(event) {
        event.preventDefault();
        const oldPassword = document.getElementById("oldPassword").value.trim();
        const newPassword = document.getElementById("newPassword").value.trim();
        const adminToken = sessionStorage.getItem("admin_token");

        if (newPassword.length < 6) {
            alert("รหัสผ่านใหม่ต้องมีความยาวอย่างน้อย 6 ตัวอักษร");
            return;
        }

        try {
            const response = await fetch(`${API}/admin/change-password`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + adminToken
                },
                body: JSON.stringify({ old_password: oldPassword, new_password: newPassword })
            });

            const data = await response.json();
            if (response.ok) {
                alert(data.message || "เปลี่ยนรหัสผ่านสำเร็จ");
                changePasswordForm.reset();
            } else {
                alert("เกิดข้อผิดพลาด: " + (data.detail || "ไม่สามารถเปลี่ยนรหัสผ่านได้"));
            }
        } catch (error) {
            alert("เชื่อมต่อเซิร์ฟเวอร์ไม่ได้");
        }
    });
}

// หมายเหตุ: เดิมตรงนี้เคยมีโค้ด "ส่วนที่ 8 — Developer Console (dev.html)" ก็อปปี้มาไว้ในไฟล์
// นี้ด้วย แต่ตรวจแล้วว่า dev.html ไม่ได้ <script src="java.js"> เลย (มี inline <script> ของ
// ตัวเองที่ทำงานซ้ำกันอยู่แล้วครบถ้วน) โค้ดส่วนนั้นจึงไม่เคยถูกเรียกใช้งานจริงเลยตั้งแต่แรก —
// ลบออกจากไฟล์นี้ (dead code) เหลือไว้แค่ในตัว dev.html เองที่เดียว ไม่กระทบการทำงานใดๆ