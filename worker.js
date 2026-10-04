let deviceState = {
  temp: 0,
  hum: 0,
  soil: 0,
  valve1: false,
  valve2: false,
  lastSeen: 0
};

let pendingCommands = [];

// صفحه HTML برای کنترل از راه دور از طریق مرورگر
const DASHBOARD_HTML = `
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>سیستم آبیاری حسام - کنترل از راه دور</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: Tahoma, sans-serif; background: #eef2f5; padding: 20px; text-align: center; color: #333; margin: 0; }
    .card { background: white; padding: 20px; border-radius: 16px; margin: 12px auto; max-width: 420px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); }
    .status { font-weight: bold; font-size: 18px; margin: 10px 0; color: #444; }
    button { background: #657353; color: white; border: none; padding: 14px 20px; margin: 6px; border-radius: 12px; cursor: pointer; font-size: 16px; font-weight: bold; width: 100%; }
    button.off { background: #80584f; }
    button.blue { background: #52766b; }
    h2 { color: #5c5145; margin-bottom: 20px; }
  </style>
</head>
<body>

  <h2>کنترل از راه دور (Cloud)</h2>

  <div class="card">
    <div class="status">دما: <span id="temp">--</span> °C</div>
    <div class="status">رطوبت هوا: <span id="hum">--</span> %</div>
    <div class="status">رطوبت خاک: <span id="soil">--</span> %</div>
    <div class="status">وضعیت شیر ۱: <span id="v1">--</span></div>
  </div>

  <div class="card">
    <button onclick="sendCommand('VALVE1_ON')">روشن کردن شیر ۱</button>
    <button class="off" onclick="sendCommand('VALVE1_OFF')">خاموش کردن شیر ۱</button>
    <button class="blue" onclick="sendCommand('VALVE2_PULSE')">پالس شیر ۲ (۱ ثانیه)</button>
  </div>

<script>
  const API_KEY = "138712";

  async function fetchStatus() {
    try {
      const res = await fetch("/api/remote/status", {
        headers: { "X-API-KEY": API_KEY }
      });
      const data = await res.json();
      if(data.ok && data.state) {
        document.getElementById('temp').textContent = data.state.temp || '--';
        document.getElementById('hum').textContent = data.state.hum || '--';
        document.getElementById('soil').textContent = data.state.soil || '--';
        document.getElementById('v1').textContent = data.state.valve1 ? 'روشن' : 'خاموش';
      }
    } catch(e) { console.error(e); }
  }

  async function sendCommand(cmd) {
    try {
      await fetch("/api/remote/command", {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-API-KEY': API_KEY 
        },
        body: JSON.stringify({ command: cmd })
      });
      alert('دستور ارسال شد.');
    } catch(e) { alert('خطا در ارسال دستور'); }
  }

  setInterval(fetchStatus, 3000);
  fetchStatus();
</script>
</body>
</html>
`;

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    const headers = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, X-API-KEY",
      "Content-Type": "application/json"
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { headers });
    }

    // ۱. اگر آدرس اصلی در مرورگر باز شد، صفحه داشبورد وب را نمایش بده
    if (path === "/" && request.method === "GET") {
      return new Response(DASHBOARD_HTML, {
        headers: { "Content-Type": "text/html; charset=utf-8" }
      });
    }

    // بررسی کلید امنیتی برای APIها
    const apiKey = request.headers.get("X-API-KEY");
    const VALID_KEY = "138712";

    if (apiKey !== VALID_KEY) {
      return new Response(JSON.stringify({ ok: false, error: "Unauthorized" }), { status: 401, headers });
    }

    // ۲. سینک ESP32 با ورکر
    if (path === "/api/device/sync" && request.method === "POST") {
      const data = await request.json();
      deviceState = { ...data, lastSeen: Date.now() };

      const cmdsToSend = [...pendingCommands];
      pendingCommands = [];

      return new Response(JSON.stringify({ ok: true, commands: cmdsToSend }), { headers });
    }

    // ۳. خواندن وضعیت توسط داشبورد وب
    if (path === "/api/remote/status" && request.method === "GET") {
      return new Response(JSON.stringify({ ok: true, state: deviceState }), { headers });
    }

    // ۴. ثبت دستور جدید از داشبورد وب
    if (path === "/api/remote/command" && request.method === "POST") {
      const body = await request.json();
      if (body.command) {
        pendingCommands.push(body.command);
        return new Response(JSON.stringify({ ok: true, message: "Command queued" }), { headers });
      }
      return new Response(JSON.stringify({ ok: false, error: "Invalid command" }), { status: 400, headers });
    }

    return new Response(JSON.stringify({ ok: false, error: "Not found" }), { status: 404, headers });
  }
};
