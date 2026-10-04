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

const MASTER_CODE = "138712";

const APP_PAGE = `
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Hesam Irrigation - Cloud Panel</title>
<style>
:root{--cream:#eee5d4;--gray:#a59e94;--brown:#5c5145;--moss:#687653;--jade:#52766b;--glass:rgba(255,255,255,.34);--line:rgba(80,70,60,.16);}
*{box-sizing:border-box;}
html,body{margin:0;min-height:100vh;color:#40382f;font-family:Arial,sans-serif;background:linear-gradient(135deg,#eee5d4,#d2c7b7,#9d968b);padding:15px;}
.container{max-width:1200px;margin:auto;}
header{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;}
.brand{display:flex;align-items:center;gap:12px;}
.logo{width:52px;height:52px;border-radius:17px;background:linear-gradient(145deg,var(--brown),var(--moss));color:white;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:22px;}
h1{margin:0;font-size:22px;}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:18px;}
.card{padding:18px;border-radius:22px;background:var(--glass);border:1px solid rgba(255,255,255,.5);box-shadow:0 15px 40px rgba(60,50,40,.13);backdrop-filter:blur(18px);}
.cardTitle{font-size:12px;opacity:.65;}
.cardValue{margin-top:7px;font-size:25px;font-weight:900;}
.valveOn{color:var(--jade);}
.valveOff{color:#777;}
.panel{padding:20px;border-radius:24px;background:var(--glass);border:1px solid rgba(255,255,255,.5);backdrop-filter:blur(18px);margin-bottom:20px;}
.controls{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;}
button{border:0;padding:15px;border-radius:14px;background:var(--moss);color:white;font-weight:800;cursor:pointer;}
button.danger{background:#80584f;}
@media(max-width:800px){.cards,.controls{grid-template-columns:repeat(2,1fr);}}
@media(max-width:520px){.cards,.controls{grid-template-columns:1fr;}}
</style>
</head>
<body>
<div class="container">
<header>
  <div class="brand">
    <div class="logo">H</div>
    <div><h1>Hesam Irrigation</h1><div class="small" id="headerInfo">Cloud Remote Panel</div></div>
  </div>
  <button onclick="logout()" style="width:auto;padding:10px 14px;background:rgba(255,255,255,.3);color:var(--brown);">LOG OUT</button>
</header>
<div class="cards">
  <div class="card"><div class="cardTitle">TEMPERATURE</div><div class="cardValue" id="temp">-- °C</div></div>
  <div class="card"><div class="cardTitle">HUMIDITY</div><div class="cardValue" id="hum">-- %</div></div>
  <div class="card"><div class="cardTitle">SOIL MOISTURE</div><div class="cardValue" id="soil">-- %</div></div>
  <div class="card"><div class="cardTitle">VALVE STATUS</div><div class="cardValue" id="valveStatus">OFF</div></div>
</div>
<section class="panel">
  <h2>Cloud Remote Control</h2>
  <div class="controls">
    <button onclick="sendCommand('VALVE1_ON')">VALVE 1 ON</button>
    <button class="danger" onclick="sendCommand('VALVE1_OFF')">VALVE 1 OFF</button>
    <button onclick="sendCommand('VALVE2_PULSE')">VALVE 2 · 1 SECOND</button>
  </div>
</section>
</div>
<script>
async function updateStatus(){
  try{
    const r = await fetch('/api/remote/status',{headers:{'X-API-KEY':'138712'}});
    if(r.status===401){ location.href='/login'; return; }
    const j = await r.json();
    if(j.ok && j.state){
      document.getElementById('temp').textContent = j.state.temperature.toFixed(1)+' °C';
      document.getElementById('hum').textContent = j.state.humidity.toFixed(1)+' %';
      document.getElementById('soil').textContent = j.state.soil+' %';
      const v = document.getElementById('valveStatus');
      v.textContent = j.state.valveText;
      v.className = (j.state.valve1 || j.state.valve2) ? 'cardValue valveOn' : 'cardValue valveOff';
    }
  }catch(e){}
}
async function sendCommand(cmd){
  await fetch('/api/remote/command',{
    method:'POST',
    headers:{'Content-Type':'application/json','X-API-KEY':'138712'},
    body:JSON.stringify({command:cmd})
  });
  alert('Command Sent');
  updateStatus();
}
async function logout(){
  document.cookie = "HESAM_REMOTE_AUTH=; Max-Age=0; path=/";
  location.href = "/login";
}
setInterval(updateStatus,2000);
updateStatus();
</script>
</body>
</html>
`;

const LOGIN_PAGE = `
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cloud Login</title>
<style>
body{min-height:100vh;margin:0;display:flex;align-items:center;justify-content:center;font-family:Arial,sans-serif;background:linear-gradient(135deg,#eee5d4,#cfc5b5,#9d968b);}
.login{width:min(380px,90%);padding:30px;border-radius:24px;background:rgba(255,255,255,.4);backdrop-filter:blur(15px);text-align:center;}
input{width:100%;padding:14px;margin:15px 0;border-radius:12px;border:1px solid rgba(0,0,0,.15);font-size:16px;}
button{width:100%;padding:14px;border:0;border-radius:12px;background:#657353;color:white;font-weight:bold;cursor:pointer;}
</style>
</head>
<body>
<div class="login">
  <h2>Cloud Security</h2>
  <input type="password" id="pass" placeholder="Enter Master Code (138712)">
  <button onclick="login()">ENTER</button>
</div>
<script>
async function login(){
  const pass = document.getElementById('pass').value;
  if(pass === "${MASTER_CODE}"){
    document.cookie = "HESAM_REMOTE_AUTH=1; path=/; max-age=86400";
    location.href = "/";
  } else { alert('Wrong Code'); }
}
</script>
</body>
</html>
`;

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;
    const cookie = request.headers.get("Cookie") || "";
    const isAuth = cookie.includes("HESAM_REMOTE_AUTH=1");

    if (path === "/login") {
      return new Response(LOGIN_PAGE, { headers: { "Content-Type": "text/html" } });
    }

    if (path === "/" && !isAuth) {
      return Response.redirect(url.origin + "/login", 302);
    }

    if (path === "/" && isAuth) {
      return new Response(APP_PAGE, { headers: { "Content-Type": "text/html" } });
    }

    const apiKey = request.headers.get("X-API-KEY");
    if (apiKey !== MASTER_CODE) {
      return new Response(JSON.stringify({ ok: false, error: "Unauthorized" }), { status: 401 });
    }

    if (path === "/api/device/sync" && request.method === "POST") {
      const data = await request.json();
      deviceState = { ...data, lastSeen: Date.now() };
      const cmdsToSend = [...pendingCommands];
      pendingCommands = [];
      return new Response(JSON.stringify({ ok: true, commands: cmdsToSend }));
    }

    if (path === "/api/remote/status" && request.method === "GET") {
      return new Response(JSON.stringify({ ok: true, state: deviceState }));
    }

    if (path === "/api/remote/command" && request.method === "POST") {
      const body = await request.json();
      if (body.command) {
        pendingCommands.push(body.command);
        return new Response(JSON.stringify({ ok: true }));
      }
    }

    return new Response(JSON.stringify({ ok: false }), { status: 404 });
  }
};
