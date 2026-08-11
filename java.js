const API = "";

const txt = {
    studentIdError: "กรุณากรอกรหัสนักศึกษาให้ครบ 11 หลัก และต้องเป็นตัวเลขเท่านั้น",
    connecting: "กำลังค้นหาข้อมูลในคู่มือ...",
    serverError: " ขออภัยครับ ไม่สามารถเชื่อมต่อกับเซิร์ฟเวอร์ได้ โปรดตรวจสอบว่าเปิด Backend รันอยู่หรือไม่",
    adminLoginSuccess: "เข้าสู่ระบบแอดมินสำเร็จ",
    adminLoginFail: "ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง",
    adminLoginServerError: "เชื่อมต่อเซิร์ฟเวอร์ไม่ได้",
    adminLoginEmpty: "กรุณากรอกข้อมูลให้ครบถ้วน",
    registerSuccess: "ลงทะเบียนสำเร็จ! กรุณาเข้าสู่ระบบ",
    registerFail: "ลงทะเบียนไม่สำเร็จ: ",
    registerServerError: "เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ครับ",
    registerEmpty: "กรุณากรอกอีเมลและรหัสผ่านให้ครบถ้วนครับ",
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
};

function t(key) {
    return txt[key];
}

// ==========================================
// หน้า Login — user.html
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
        if (!res.ok) {
            let detail = t("invalidCode");
            try { const data = await res.json(); if (data.detail) detail = data.detail; } catch {}
            alert(detail);
            return;
        }

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

    // แสดง role ข้าง title (เดิมมี <span id="roleName"> ในหน้า chatbot.html แต่ไม่เคยถูกเติมข้อความ)
    const roleNameEl = document.getElementById("roleName");
    if (roleNameEl) {
        roleNameEl.textContent = userRole === "teacher" ? t("roleTeacher") : t("roleStudent");
    }

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

    // ข้อความทักทายตอนเปิดหน้าครั้งแรก (แสดงครั้งเดียว ไม่แสดงซ้ำถ้ามีข้อความอยู่แล้ว
    // เช่น ตอนเรียก appendMessage มาก่อนหน้านี้ในโค้ดส่วนอื่น)
    if (chatDisplay.children.length === 0) {
        appendMessage("สวัสดีเจ้า มีอะหยังหื้อน้องกาสะลองจ่วยก่อเจ้า?", "bot");
    }

    inputMessage.addEventListener("keypress", function(event) {
        if (event.key === "Enter") {
            event.preventDefault();
            sendButton.click();
        }
    });

    sendButton.addEventListener("click", async function() {
        const text = inputMessage.value.trim();
        if (text !== "") {
            // แสดงข้อความนักศึกษา
            appendMessage(text, "user");
            inputMessage.value = "";

            // แสดงกล่องสถานะกำลังคิด — ใช้ตัวบ่งชี้ "กำลังพิมพ์..." (จุด 3 จุดขยับไปมา)
            // แทนข้อความนิ่งๆ เดิม ให้ดูเหมือนบอทกำลังพิมพ์อยู่จริง
            const loadingBox = appendMessage("", "bot");
            loadingBox.classList.add("typing-indicator");
            loadingBox.innerHTML =
                '<span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>';

            try {
                // ส่งคำถามไปหา Python
                const response = await fetch(`${API}/chat`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        question: text,
                        session_id: studentId,
                        role:       userRole,
                        year: studentYear
                    })
                });

                if (!response.ok) {
                    throw new Error("Network response was not ok");
                }

                const data = await response.json();
                // เอาคำตอบจาก AI มาใส่แทนตัวบ่งชี้กำลังพิมพ์
                loadingBox.classList.remove("typing-indicator");
                loadingBox.innerHTML = "";
                loadingBox.textContent = data.answer || data.detail;

            } catch (error) {
                loadingBox.classList.remove("typing-indicator");
                loadingBox.innerHTML = "";
                loadingBox.textContent = t("serverError");
                loadingBox.style.color = "red";
            }
        }
    });

    if (newChatButton) {
        newChatButton.addEventListener("click", async function() {
            chatDisplay.innerHTML = "";
            appendMessage("สวัสดีเจ้า มีอะหยังหื้อน้องกาสะลองจ่วยก่อเจ้า?", "bot");
            try {
                await fetch(`${API}/reset-memory/${studentId}`, {
                    method: "POST"
                });
            } catch (error) {
                // ล้างความจำฝั่ง server ไม่สำเร็จ แต่หน้าจอแชทถูกล้างแล้ว ไม่ต้องแจ้งเตือนผู้ใช้
            }
        });
    }

    function appendMessage(text, sender) {
        // แถวครอบ [อวตาร์ + บับเบิลข้อความ] คู่กัน แล้วจัดชิดซ้าย/ขวาตามฝั่งผู้ส่ง
        // (ไม่แก้สไตล์เดิมของ msgBox เลยแม้แต่บรรทัดเดียว แค่ครอบด้วย row เพิ่ม)
        const row = document.createElement("div");
        row.style.display = "flex";
        row.style.alignItems = "flex-end";
        row.style.gap = "8px";
        row.style.marginBottom = "15px";
        row.style.justifyContent = sender === "user" ? "flex-end" : "flex-start";

        const msgBox = document.createElement("div");
        msgBox.textContent = text;
        msgBox.style.padding = "10px 15px";
        msgBox.style.maxWidth = "70%";
        msgBox.style.width = "fit-content";
        msgBox.style.fontFamily = "'Prompt', sans-serif";
        msgBox.style.lineHeight = "1.5";

        if (sender === "user") {
            // ฝั่งผู้ใช้ไม่มีรูปอวตาร์แล้ว แสดงแค่บับเบิลข้อความ
            msgBox.style.background = "linear-gradient(135deg, #a8e063 0%, #56ab2f 100%)";
            msgBox.style.color = "white";
            msgBox.style.borderRadius = "15px 15px 0px 15px";
            row.appendChild(msgBox);
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
            row.appendChild(avatar);
            row.appendChild(msgBox);
        }

        chatDisplay.appendChild(row);
        chatDisplay.scrollTop = chatDisplay.scrollHeight;

        return msgBox;
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
// 5. ส่วนของหน้าลงทะเบียน (Register Admin) -  เชื่อม Backend แล้ว
// ==========================================
const regisBtn = document.getElementById("submitadmin");

if (regisBtn) {
    const regisForm = regisBtn.closest("form");

    if (regisForm) {
        regisForm.addEventListener("submit", async function(event) {
            event.preventDefault();

            const emailRegis = document.getElementById("emailadmin");
            const passRegis = document.getElementById("passwordadmin");

            if (emailRegis && passRegis && emailRegis.value.trim() !== "" && passRegis.value.trim() !== "") {

                try {
                    const response = await fetch(`${API}/admin/register`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            username: emailRegis.value.trim(),
                            password: passRegis.value.trim()
                        })
                    });

                    if (response.ok) {
                        alert(t("registerSuccess"));
                        window.location.href = "loginadmin.html";
                    } else {
                        const err = await response.json();
                        alert(t("registerFail") + err.detail);
                    }
                } catch (error) {
                    alert(t("registerServerError"));
                }

            } else {
                alert(t("registerEmpty"));
            }
        });
    }
}

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

const autoTagBtn = document.getElementById("autoTagBtn");
if (autoTagBtn) {
    autoTagBtn.addEventListener("click", async function() {
        const confirmed = confirm(
            "ระบบจะไล่เดาปีการศึกษาให้ไฟล์เก่าที่ยังไม่ได้ระบุปีทั้งหมดโดยอัตโนมัติ (ไฟล์ที่มีปีอยู่แล้วจะไม่ถูกแตะต้อง) ดำเนินการต่อหรือไม่?"
        );
        if (!confirmed) return;

        const adminToken = sessionStorage.getItem("admin_token");
        autoTagBtn.disabled = true;
        const originalLabel = autoTagBtn.textContent;
        autoTagBtn.textContent = "กำลังเดาปี...";
        try {
            const response = await fetch(`${API}/admin/files/auto-tag`, {
                method: "POST",
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
                alert(data.message || "ติดปีอัตโนมัติเรียบร้อย");
                loadFileTable();
            } else {
                alert("เกิดข้อผิดพลาด: " + data.detail);
            }
        } catch (error) {
            alert(t("uploadServerError"));
        } finally {
            autoTagBtn.disabled = false;
            autoTagBtn.textContent = originalLabel;
        }
    });
}

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