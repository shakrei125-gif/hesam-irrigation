// ============================================================
// CLOUD CONTROL WORKER - SECURED & ENHANCED UI
// ============================================================

let deviceState = {
  temperature: 0,
  humidity: 0,
  soil: 0,
  valve1: false,
  valve2: false,
  valveText: "OFF",
  date: "----/--/--",
  time: "--:--:--",
  mode: "Cloud",
  ip: "Online",
  serial: "HESAM-IRR-01",
  firmware: "3.3.0",
  lastSeen: 0
};

let pendingCommands = [];
let loginAttempts = {}; // جهت جلوگیری از حملات حدس رمز (Rate Limiting)

// پیش‌فرض کد مستر (قابلیت تغییر از داخل پنل وجود دارد)
let MASTER_CODE = "138712"; 

// ------------------------------------------------------------
// 1. DASHBOARD PAGE (HTML / CSS / JS)
// ------------------------------------------------------------
const APP_PAGE = `
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Hesam Irrigation - Cloud Panel</title>
<style>
:root {
  --bg-gradient: linear-gradient(135deg, #d8d0c1, #a8a090);
  --glass: rgba(255, 255, 255, 0.45);
  --glass-border: rgba(255, 255, 255, 0.6);
  --text-primary: #362f2d;
  --accent-green: #486a5a;
  --accent-red: #8f4a43;
  --accent-blue: #3d5a80;
}
* { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
body { margin: 0; min-height: 100vh; background: var(--bg-gradient); color: var(--text-primary); padding: 20px; }
.container { max-width: 1000px; margin: 0 auto; }
header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; backdrop-filter: blur(10px); background: var(--glass); padding: 15px 20px; border-radius: 20px; border: 1px solid var(--glass-border); }
.brand { display: flex; align-items: center; gap: 14px; }
.logo { width: 48px; height: 48px; border-radius: 14px; background: var(--accent-green); color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 900; font-size: 22px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
h1 { margin: 0; font-size: 20px; font-weight: 700; }
.sub { font-size: 12px; opacity: 0.7; }
.btn-logout { background: rgba(0,0,0,0.06); border: 1px solid rgba(0,0,0,0.1); padding: 8px 16px; border-radius: 12px; cursor: pointer; font-weight: 600; color: var(--text-primary); transition: 0.2s; }
.btn-logout:hover { background: rgba(0,0,0,0.12); }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 25px; }
.card { padding: 20px; border-radius: 20px; background: var(--glass); border: 1px solid var(--glass-border); backdrop-filter: blur(15px); box-shadow: 0 10px 30px rgba(0,0,0,0.05); }
.card-title { font-size: 11px; font-weight: 800; letter-spacing: 0.5px; opacity: 0.6; }
.card-value { margin-top: 10px; font-size: 26px; font-weight: 800; }
.panel { padding: 25px; border-radius: 24px; background: var(--glass); border: 1px solid var(--glass-border); backdrop-filter: blur(15px); margin-bottom: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); }
.panel h2 { margin-top: 0; font-size: 18px; margin-bottom: 20px; }
.controls { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }
button.action-btn { border: 0; padding: 16px; border-radius: 14px; background: var(--accent-green); color: #fff; font-weight: 700; font-size: 14px; cursor: pointer; transition: transform 0.1s, opacity 0.2s; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
button.action-btn:active { transform: scale(0.98); }
button.action-btn.danger { background: var(--accent-red); }
button.action-btn.blue { background: var(--accent-blue); }
.form-group { margin-bottom: 15px; }
label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px; }
input[type="password"] { width: 100%; padding: 12px 16px; border-radius: 12px; border: 1px solid rgba(0,0,0,0.15); background: rgba(255,255,255,0.7); outline: none; font-size: 15px; }
.valve-on { color: var(--accent-green); }
.valve-off { color: #666; }
</style>
</head>
<body>
<div class="container">
  <header>
    <div class="brand">
      <div class="logo">H</div>
      <div>
        <h1>Hesam Irrigation</h1>
        <div class="sub">Cloud Remote Control Center</div>
      </div>
    </div>
    <button class="btn-logout" onclick="logout()">خروج</button>
  </header>

  <div class="cards">
    <div class="card"><div class="card-title">دما (TEMPERATURE)</div><div class="card-value" id="temp">-- °C</div></div>
    <div class="card"><div class="card-title">رطوبت هوا (HUMIDITY)</div><div class="card-value" id="hum">-- %</div></div>
    <div class="card"><div class="card-title">رطوبت خاک (SOIL)</div><div class="card-value" id="soil">-- %</div></div>
    <div class="card"><div class="card-title">وضعیت شیر (VALVE)</div><div class="card-value" id="valveStatus">OFF</div></div>
  </div>

  <section class="panel">
    <h2>کنترل آنلاین تجهیزات</h2>
    <div class="controls">
      <button class="action-btn" onclick="sendCommand('VALVE1_ON')">روشن کردن شیر ۱</button>
      <button class="action-btn danger" onclick="sendCommand('VALVE1_OFF')">خاموش کردن شیر ۱</button>
      <button class="action-btn blue" onclick="sendCommand('VALVE2_PULSE')">پالس شیر ۲ (۱ ثانیه)</button>
    </div>
  </section>

  <section class="panel">
    <h2>تنظیمات امنیت پنل ابری</h2>
    <div style="max-width: 400px;">
      <div class="form-group">
        <label>رمز عبور جدید پنل وب:</label>
        <input type="password" id="newPass" autocomplete="new-password">
      </div>
      <button class="action-btn" style="width:100%" onclick="changePassword()">تغییر رمز عبور وب</button>
    </div>
  </section>
</div>

<script>
async function updateStatus(){
  try {
    const r = await fetch('/api/remote/status');
    if(r.status === 401) { location.href = '/login'; return; }
    const j = await r.json();
    if(j.ok && j.state) {
      document.getElementById('temp').textContent = j.state.temperature.toFixed(1) + ' °C';
      document.getElementById('hum').textContent = j.state.humidity.toFixed(1) + ' %';
      document.getElementById('soil').textContent = j.state.soil + ' %';
      const v = document.getElementById('valveStatus');
      v.textContent = j.state.valveText;
      v.className = (j.state.valve1 || j.state.valve2) ? 'card-value valve-on' : 'card-value valve-off';
    }
  } catch(e){}
}

async function sendCommand(cmd) {
  const r = await fetch('/api/remote/command', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ command: cmd })
  });
  if(r.ok) { alert('دستور ارسال شد.'); updateStatus(); }
}

async function changePassword() {
  const newPass = document.getElementById('newPass').value;
  if(!newPass) { alert('لطفاً رمز عبور جدید را وارد کنید.'); return; }
  
  const r = await fetch('/api/remote/change-pass', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ newPassword: newPass })
  });
  const j = await r.json();
  if(j.ok) {
    alert('رمز عبور وب با موفقیت تغییر کرد.');
    document.getElementById('newPass').value = '';
  } else { alert(j.error || 'خطا در تغییر رمز عبور'); }
}

async function logout() {
  await fetch('/api/logout', { method: 'POST' });
  location.href = '/login';
}

setInterval(updateStatus, 2500);
updateStatus();
</script>
</body>
</html>
`;

// ------------------------------------------------------------
// 2. LOGIN PAGE (HTML / CSS / SECURED JS WITH SHA-256)
// ------------------------------------------------------------
const LOGIN_PAGE = `
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ورود به سیستم کنترل ابری</title>
<style>
body { margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center; font-family: Tahoma, sans-serif; background: linear-gradient(135deg, #d8d0c1, #a8a090); color: #333; }
.login-card { width: min(380px, 90%); padding: 35px 30px; border-radius: 24px; background: rgba(255, 255, 255, 0.5); backdrop-filter: blur(20px); border: 1px solid rgba(255,255,255,0.7); box-shadow: 0 15px 35px rgba(0,0,0,0.1); text-align: center; }
.logo { width: 60px; height: 60px; margin: 0 auto 15px; border-radius: 18px; background: #486a5a; color: white; display: flex; align-items: center; justify-content: center; font-size: 26px; font-weight: bold; }
h2 { margin: 0 0 8px; font-size: 22px; }
p { font-size: 13px; color: #666; margin-bottom: 25px; }
input[type="password"] { width: 100%; padding: 14px; border-radius: 12px; border: 1px solid rgba(0,0,0,0.15); background: rgba(255,255,255,0.8); outline: none; font-size: 16px; box-sizing: border-box; text-align: center; margin-bottom: 15px; }
button { width: 100%; padding: 14px; border: 0; border-radius: 12px; background: #486a5a; color: white; font-weight: bold; font-size: 16px; cursor: pointer; transition: 0.2s; }
button:hover { background: #3a5648; }
.error { color: #8f4a43; font-size: 13px; margin-top: 12px; }
</style>
</head>
<body>
<div class="login-card">
  <div class="logo">H</div>
  <h2>احراز هویت سیستم ابری</h2>
  <p>آبیاری و مدیریت هوشمند حسام</p>
  <input type="password" id="pass" autocomplete="current-password">
  <button onclick="login()">ورود به پنل</button>
  <div id="err" class="error"></div>
</div>

<script>
document.getElementById('pass').addEventListener('keydown', e => { if(e.key==='Enter') login(); });

async function sha256(str) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(str));
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, "0")).join("");
}

async function login(){
  const pass = document.getElementById('pass').value;
  if(!pass) { document.getElementById('err').textContent = 'لطفاً رمز عبور را وارد نمایید.'; return; }
  
  const hash = await sha256(pass);
  const r = await fetch('/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ hash })
  });
  
  const j = await r.json();
  if(j.ok) { location.href = '/'; }
  else { document.getElementById('err').textContent = j.error || 'رمز عبور اشتباه است.'; }
}
</script>
</body>
</html>
`;

// ------------------------------------------------------------
// 3. WORKER ROUTING & SECURITY ENGINE
// ------------------------------------------------------------
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;
    const clientIP = request.headers.get("CF-Connecting-IP") || "0.0.0.0";

    // امنیت کوکی‌ها
    const cookie = request.headers.get("Cookie") || "";
    const isAuth = cookie.includes("HESAM_CLOUD_AUTH=1");

    // تابع هش SHA256 در سمت سرور
    async function hashString(str) {
      const myText = new TextEncoder().encode(str);
      const hashBuffer = await crypto.subtle.digest('SHA-256', myText);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    }

    // ۱. مسیریابی صفحات
    if (path === "/login") {
      return new Response(LOGIN_PAGE, { headers: { "Content-Type": "text/html; charset=utf-8" } });
    }

    if (path === "/" && !isAuth) {
      return Response.redirect(url.origin + "/login", 302);
    }

    if (path === "/" && isAuth) {
      return new Response(APP_PAGE, { headers: { "Content-Type": "text/html; charset=utf-8" } });
    }

    // ۲. پردازش ورود با هش رمز (API /api/login)
    if (path === "/api/login" && request.method === "POST") {
      // بررسی Rate Limiting جهت جلوگیری از حدس زدن رمز عبور
      const now = Date.now();
      if (loginAttempts[clientIP] && loginAttempts[clientIP].count >= 5 && (now - loginAttempts[clientIP].time < 60000)) {
        return new Response(JSON.stringify({ ok: false, error: "تعداد تلاش‌های ناموفق زیاد. ۱ دقیقه صبر کنید." }), { status: 429 });
      }

      const { hash } = await request.json();
      const expectedHash = await hashString(MASTER_CODE);

      if (hash === expectedHash) {
        delete loginAttempts[clientIP];
        return new Response(JSON.stringify({ ok: true }), {
          headers: {
            "Content-Type": "application/json",
            "Set-Cookie": "HESAM_CLOUD_AUTH=1; Path=/; Secure; HttpOnly; SameSite=Strict; Max-Age=86400"
          }
        });
      } else {
        if (!loginAttempts[clientIP]) loginAttempts[clientIP] = { count: 0, time: now };
        loginAttempts[clientIP].count++;
        loginAttempts[clientIP].time = now;
        return new Response(JSON.stringify({ ok: false, error: "رمز عبور اشتباه است." }), { status: 401 });
      }
    }

    // ۳. خروج از حساب
    if (path === "/api/logout" && request.method === "POST") {
      return new Response(JSON.stringify({ ok: true }), {
        headers: {
          "Content-Type": "application/json",
          "Set-Cookie": "HESAM_CLOUD_AUTH=; Path=/; Max-Age=0"
        }
      });
    }

    // ۴. ارتباط دستگاه ESP32 با Cloudflare (نیاز به API Key دارد)
    const apiKey = request.headers.get("X-API-KEY");
    if (path === "/api/device/sync" && request.method === "POST") {
      if (apiKey !== MASTER_CODE) return new Response("Unauthorized", { status: 401 });
      
      const data = await request.json();
      deviceState = { ...data, lastSeen: Date.now() };
      const cmdsToSend = [...pendingCommands];
      pendingCommands = [];
      return new Response(JSON.stringify({ ok: true, commands: cmdsToSend }), { headers: { "Content-Type": "application/json" } });
    }

    // ۵. احراز هویت درخواست‌های وب‌سایت آنلاین (مرورگر)
    if (!isAuth) {
      return new Response(JSON.stringify({ ok: false, error: "Unauthorized" }), { status: 401 });
    }

    if (path === "/api/remote/status" && request.method === "GET") {
      return new Response(JSON.stringify({ ok: true, state: deviceState }), { headers: { "Content-Type": "application/json" } });
    }

    if (path === "/api/remote/command" && request.method === "POST") {
      const body = await request.json();
      if (body.command) pendingCommands.push(body.command);
      return new Response(JSON.stringify({ ok: true }), { headers: { "Content-Type": "application/json" } });
    }

    if (path === "/api/remote/change-pass" && request.method === "POST") {
      const body = await request.json();
      if (body.newPassword && body.newPassword.length >= 4) {
        MASTER_CODE = body.newPassword;
        return new Response(JSON.stringify({ ok: true, message: "Password updated successfully" }), { headers: { "Content-Type": "application/json" } });
      }
      return new Response(JSON.stringify({ ok: false, error: "رمز عبور باید حداقل ۴ کاراکتر باشد." }), { status: 400 });
    }

    return new Response("Not Found", { status: 404 });
  }
};
