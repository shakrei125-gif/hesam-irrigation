import json
import time
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
import paho.mqtt.client as mqtt

app = Flask(__name__)
app.secret_key = "hesam_os_leather_secure_key"

# =========================================================
# MQTT CONFIGURATION (MATCHING ESP32 CODE)
# =========================================================

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883

TOPIC_CMD = "hesam/irrigation/cmd"
TOPIC_STATUS = "hesam/irrigation/status"

# Data store matching ESP32 JSON payload
latest_device_data = {
    "temp": 0.0,
    "hum": 0.0,
    "soil": 0,
    "valve": "خاموش",
    "ram": 0,
    "wifi_rssi": 0,
    "keypad_pin": "1234"
}

recent_logs = []

def on_connect(client, userdata, flags, rc):
    print("MQTT Connected with result code:", rc)
    client.subscribe(TOPIC_STATUS)

def on_message(client, userdata, msg):
    global latest_device_data
    try:
        data = json.loads(msg.payload.decode('utf-8'))
        latest_device_data.update(data)
    except Exception as e:
        print("MQTT JSON Error:", e)

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start()
except Exception as e:
    print("MQTT Connection Error:", e)

# =========================================================
# USER AUTHENTICATION DATABASE
# =========================================================

users_db = {
    "admin": "123456"
}

# =========================================================
# ROUTE CONTROLLERS
# =========================================================

@app.route("/")
def index():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template_string(MAIN_OS_TEMPLATE, data=latest_device_data)

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username in users_db and users_db[username] == password:
            session["user"] = username
            return redirect(url_for("index"))
        error = "نام کاربری یا رمز عبور اشتباه است."
    return render_template_string(LOGIN_TEMPLATE, error=error)

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

# =========================================================
# API ENDPOINTS
# =========================================================

@app.route("/api/change_password", methods=["POST"])
def change_password():
    if "user" not in session:
        return jsonify({"status": "error", "message": "دسترسی غیرمجاز"}), 401

    data = request.get_json(silent=True) or {}
    old_pass = data.get("old_pass")
    new_pass = data.get("new_pass")

    if users_db.get(session["user"]) == old_pass:
        users_db[session["user"]] = new_pass
        return jsonify({"status": "success", "message": "رمز عبور با موفقیت به‌روزرسانی شد."})
    return jsonify({"status": "error", "message": "رمز فعلی اشتباه است."}), 400

@app.route("/api/send_cmd", methods=["POST"])
def send_cmd():
    if "user" not in session:
        return jsonify({"status": "error", "message": "دسترسی غیرمجاز"}), 401

    data = request.get_json(silent=True) or {}
    cmd = data.get("cmd")

    if not cmd:
        return jsonify({"status": "error", "message": "دستور خالی است."}), 400

    try:
        mqtt_client.publish(TOPIC_CMD, cmd)

        event_text = ""
        status_text = "ارسال شد"

        if cmd == "VALVE_ON":
            event_text = "دستور شروع آبیاری دستی"
        elif cmd == "VALVE_OFF":
            event_text = "دستور قطع آبیاری دستی"
        elif cmd == "OPEN_DOOR":
            event_text = "دستور باز کردن قفل درب"
        elif cmd.startswith("SET_PASS_"):
            new_pin = cmd.replace("SET_PASS_", "")
            event_text = f"ارسال رمز جدید کیپد ({new_pin}) به ESP32"

        if event_text:
            recent_logs.insert(0, {
                "event": event_text,
                "status": status_text,
                "temp": latest_device_data.get("temp", 0),
                "soil": latest_device_data.get("soil", 0),
                "time": time.strftime("%H:%M:%S")
            })
            recent_logs[:] = recent_logs[:20]

        return jsonify({"status": "success", "message": "دستور صادر شد."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/get_data")
def get_data():
    if "user" not in session:
        return jsonify({"status": "error"}), 401
    return jsonify({
        "data": latest_device_data,
        "logs": recent_logs[:6]
    })

# =========================================================
# LOGIN UI TEMPLATE
# =========================================================

LOGIN_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>HESAM OS - LOGIN</title>
<style>
* { box-sizing: border-box; font-family: Tahoma, sans-serif; }
body {
    margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center;
    background: radial-gradient(circle at 50% 30%, #3e271a, #1a0f0a); color: #f2e2ce;
}
.login-card {
    width: 380px; padding: 40px 30px; border-radius: 24px;
    background: linear-gradient(145deg, #4d3121, #281910);
    border: 2px solid #8c6847; box-shadow: 0 25px 60px rgba(0,0,0,0.6);
    position: relative; text-align: center;
}
.login-card::after {
    content: ""; position: absolute; inset: 8px; border: 1px dashed #b8956c;
    border-radius: 18px; pointer-events: none; opacity: 0.5;
}
h2 { margin: 0 0 5px; font-size: 28px; color: #e8c497; letter-spacing: 1px; }
p { font-size: 11px; color: #a88c70; margin-bottom: 25px; letter-spacing: 2px; }
input {
    width: 100%; padding: 14px; margin-bottom: 15px; border-radius: 12px;
    border: 1px solid #6e4e35; background: #180d08; color: #fff; outline: none; text-align: center;
}
button {
    width: 100%; padding: 14px; border: none; border-radius: 12px;
    background: linear-gradient(180deg, #c99e6b, #9e7547); color: #1a0d07;
    font-weight: bold; font-size: 15px; cursor: pointer; transition: 0.2s;
}
button:hover { filter: brightness(1.1); transform: translateY(-1px); }
.error { background: #611e18; color: #ffc4be; padding: 10px; border-radius: 8px; font-size: 12px; margin-bottom: 15px; }
</style>
</head>
<body>
<div class="login-card">
    <h2>HESAM OS</h2>
    <p>IRRIGATION & DOOR ACCESS</p>
    {% if error %}<div class="error">{{ error }}</div>{% endif %}
    <form method="POST">
        <input type="text" name="username" placeholder="نام کاربری" required>
        <input type="password" name="password" placeholder="رمز عبور" required>
        <button type="submit">ورود به سیستم</button>
    </form>
</div>
</body>
</html>
"""

# =========================================================
# MAIN OS DASHBOARD & SPLASH SCREEN TEMPLATE
# =========================================================

MAIN_OS_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>HESAM OS v3.0</title>
<link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;600;800;900&display=swap" rel="stylesheet">
<style>
* { box-sizing: border-box; }
body {
    margin: 0; font-family: 'Vazirmatn', sans-serif; background: #160c07; color: #f7e9d7;
    overflow-x: hidden; min-height: 100vh;
}

/* ================= SPLASH BOOT SCREEN ================= */
#splash-screen {
    position: fixed; inset: 0; z-index: 99999;
    background: radial-gradient(circle at center, #3d2517, #100804);
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    transition: opacity 0.8s ease, visibility 0.8s;
}
.splash-logo {
    width: 120px; height: 120px; border-radius: 50%;
    background: linear-gradient(135deg, #c79c6d, #52341e);
    display: flex; align-items: center; justify-content: center; font-size: 50px;
    box-shadow: 0 0 40px rgba(199, 156, 109, 0.4), inset 0 0 15px rgba(0,0,0,0.5);
    animation: pulse 2s infinite alternate; margin-bottom: 25px;
}
@keyframes pulse {
    0% { transform: scale(0.95); box-shadow: 0 0 20px rgba(199, 156, 109, 0.2); }
    100% { transform: scale(1.05); box-shadow: 0 0 50px rgba(199, 156, 109, 0.6); }
}
.splash-title { font-size: 26px; font-weight: 900; color: #e6c59c; letter-spacing: 2px; }
.splash-sub { font-size: 12px; color: #8a7057; margin-top: 5px; letter-spacing: 4px; }
.loader-bar {
    width: 240px; height: 6px; background: #26160d; border-radius: 10px;
    margin-top: 35px; overflow: hidden; border: 1px solid #543925;
}
.loader-progress {
    width: 0%; height: 100%; background: linear-gradient(90deg, #8a5a30, #e6c59c);
    border-radius: 10px; transition: width 0.3s ease;
}
.loader-status { font-size: 11px; color: #a3886f; margin-top: 12px; font-family: monospace; }

/* ================= MAIN DASHBOARD UI ================= */
.app-container { opacity: 0; transition: opacity 0.6s ease; padding: 25px; max-width: 1300px; margin: 0 auto; }
.header {
    display: flex; justify-content: space-between; align-items: center; padding: 20px 30px;
    background: linear-gradient(145deg, #472d1d, #24160d); border-radius: 20px;
    border: 1px solid #826042; box-shadow: 0 15px 35px rgba(0,0,0,0.4); margin-bottom: 25px;
}
.brand-box { display: flex; align-items: center; gap: 15px; }
.brand-icon {
    width: 48px; height: 48px; background: #c29868; color: #1f1109; border-radius: 14px;
    display: flex; align-items: center; justify-content: center; font-weight: 900; font-size: 24px;
    box-shadow: 3px 3px 0px #120904;
}
.title { font-size: 20px; font-weight: 900; color: #ebd4b9; }
.subtitle { font-size: 10px; color: #9c7f63; letter-spacing: 2px; }
.btn-menu {
    background: #331f13; border: 1px solid #75553a; color: #e6c59c;
    padding: 10px 18px; border-radius: 12px; cursor: pointer; font-weight: bold;
}

/* CARDS & METRICS */
.grid-4 { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; margin-bottom: 25px; }
.card {
    background: linear-gradient(145deg, rgba(64,41,26,0.85), rgba(31,19,12,0.9));
    border: 1px solid #705137; border-radius: 20px; padding: 22px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.3); position: relative; overflow: hidden;
}
.card::before {
    content: ""; position: absolute; inset: 6px; border: 1px dashed rgba(184, 149, 108, 0.25);
    border-radius: 15px; pointer-events: none;
}
.card-label { font-size: 12px; color: #a3876e; font-weight: 600; }
.card-val { font-size: 32px; font-weight: 900; color: #f5e5d3; margin-top: 10px; }
.card-unit { font-size: 16px; color: #c29868; }

/* CONTROLS */
.controls-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-top: 15px; }
.btn-action {
    padding: 18px; border: none; border-radius: 15px; font-weight: 900; font-size: 14px;
    cursor: pointer; transition: 0.2s; color: white; text-align: center;
    box-shadow: 0 6px 0 rgba(0,0,0,0.3);
}
.btn-action:active { transform: translateY(4px); box-shadow: none; }
.btn-water-on { background: linear-gradient(180deg, #4a7337, #2f4f20); }
.btn-water-off { background: linear-gradient(180deg, #8c3b30, #5c221a); }
.btn-door-open { background: linear-gradient(180deg, #8c6e30, #5c451a); }

/* HARDWARE MONITOR */
.hw-bar-bg { width: 100%; height: 8px; background: #140b07; border-radius: 10px; overflow: hidden; margin-top: 10px; }
.hw-bar-fill { height: 100%; background: linear-gradient(90deg, #8c643b, #dca870); width: 0%; transition: width 0.5s; }

/* SIDEBAR MODAL */
.sidebar {
    position: fixed; top: 0; right: -360px; width: 340px; height: 100vh;
    background: linear-gradient(160deg, #382215, #140a05); z-index: 10000;
    border-left: 2px solid #78573a; padding: 30px; transition: 0.4s ease;
    box-shadow: -10px 0 40px rgba(0,0,0,0.7);
}
.sidebar.active { right: 0; }
.sidebar-overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 9999;
    display: none; backdrop-filter: blur(4px);
}
.sidebar-overlay.active { display: block; }
.sidebar input {
    width: 100%; padding: 12px; margin: 8px 0 15px; border-radius: 10px;
    border: 1px solid #63452b; background: #1a0e08; color: #fff; outline: none;
}
.sidebar button {
    width: 100%; padding: 12px; border: none; border-radius: 10px;
    background: #c29868; color: #1a0e08; font-weight: bold; cursor: pointer;
}

/* LOGS TABLE */
.log-item {
    display: flex; justify-content: space-between; align-items: center;
    padding: 12px 16px; background: rgba(255,255,255,0.03); border-radius: 10px;
    margin-bottom: 8px; border-right: 4px solid #c29868; font-size: 13px;
}

@media (max-width: 768px) {
    .controls-grid { grid-template-columns: 1fr; }
}
</style>
</head>
<body>

<!-- BOOT / LOADING SCREEN -->
<div id="splash-screen">
    <div class="splash-logo">🌱</div>
    <div class="splash-title">HESAM OS</div>
    <div class="splash-sub">IRRIGATION v3.0 SYSTEM</div>
    <div class="loader-bar">
        <div class="loader-progress" id="splash-bar"></div>
    </div>
    <div class="loader-status" id="splash-status">Connecting to ESP32 Telemetry...</div>
</div>

<!-- SIDEBAR MODAL -->
<div class="sidebar-overlay" id="overlay" onclick="toggleSidebar(false)"></div>
<div class="sidebar" id="sidebar">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:25px;">
        <h3 style="margin:0; color:#e6c59c;">تنظیمات و امنیت OS</h3>
        <span onclick="toggleSidebar(false)" style="cursor:pointer; font-size:24px;">×</span>
    </div>

    <p style="font-size:12px; color:#a3886f;">تغییر PIN کیپد ۳x۴ (NVS Memory):</p>
    <input type="text" id="keypadPinInput" placeholder="رمز ۴ رقمی جدید کیپد">
    <button onclick="updateKeypadPin()">ارسال و ذخیره روی ESP32</button>

    <hr style="border-color:#422a19; margin:25px 0;">

    <p style="font-size:12px; color:#a3886f;">تغییر رمز ورود به وب‌پنل:</p>
    <input type="password" id="oldWebPass" placeholder="رمز فعلی وب">
    <input type="password" id="newWebPass" placeholder="رمز جدید وب">
    <button onclick="changeWebPassword()">تغییر رمز وب</button>

    <a href="/logout" style="display:block; text-align:center; margin-top:40px; color:#e87364; text-decoration:none; font-weight:bold;">خروج از حساب</a>
</div>

<!-- MAIN APPLICATION UI -->
<div class="app-container" id="app">
    <header class="header">
        <div class="brand-box">
            <div class="brand-icon">H</div>
            <div>
                <div class="title">HESAM OS v3.0</div>
                <div class="subtitle">AUTOMATED IRRIGATION & ACCESS CONTROL</div>
            </div>
        </div>
        <button class="btn-menu" onclick="toggleSidebar(true)">⚙ تنظیمات سیستم</button>
    </header>

    <!-- METRICS GRID -->
    <div class="grid-4">
        <div class="card">
            <div class="card-label">دمای محیط (DHT22)</div>
            <div class="card-val"><span id="lblTemp">--</span> <span class="card-unit">°C</span></div>
        </div>
        <div class="card">
            <div class="card-label">رطوبت محیط</div>
            <div class="card-val"><span id="lblHum">--</span> <span class="card-unit">%</span></div>
        </div>
        <div class="card">
            <div class="card-label">رطوبت خاک</div>
            <div class="card-val"><span id="lblSoil">--</span> <span class="card-unit">%</span></div>
        </div>
        <div class="card">
            <div class="card-label">وضعیت شیر آبیاری</div>
            <div class="card-val" id="lblValve" style="font-size:24px; color:#9ce6a2;">--</div>
        </div>
    </div>

    <!-- CONTROLS & HARDWARE MONITOR -->
    <div style="display:grid; grid-template-columns: 2fr 1fr; gap:20px; margin-bottom:25px;">
        <div class="card">
            <div class="card-label">کنترل مستقیم تجهیزات</div>
            <div class="controls-grid">
                <button class="btn-action btn-water-on" onclick="sendCmd('VALVE_ON')">💧 شروع آبیاری</button>
                <button class="btn-action btn-water-off" onclick="sendCmd('VALVE_OFF')">🛑 قطع آبیاری</button>
                <button class="btn-action btn-door-open" onclick="sendCmd('OPEN_DOOR')">🔓 باز کردن درب</button>
            </div>
        </div>

        <div class="card">
            <div class="card-label">وضعیت کارت ESP32</div>
            <div style="margin-top:15px;">
                <div style="display:flex; justify-content:space-between; font-size:12px;">
                    <span>حافظه RAM آزاد:</span>
                    <span id="lblRam">0 KB</span>
                </div>
                <div class="hw-bar-bg"><div class="hw-bar-fill" id="barRam"></div></div>

                <div style="display:flex; justify-content:space-between; font-size:12px; margin-top:15px;">
                    <span>سیگنال Wi-Fi:</span>
                    <span id="lblWifi">0 dBm</span>
                </div>
                <div class="hw-bar-bg"><div class="hw-bar-fill" id="barWifi"></div></div>
                
                <div style="display:flex; justify-content:space-between; font-size:12px; margin-top:15px;">
                    <span>رمز فعال کیپد:</span>
                    <span id="lblKeypadPin" style="color:#c29868; font-weight:bold;">----</span>
                </div>
            </div>
        </div>
    </div>

    <!-- RECENT LOGS -->
    <div class="card">
        <div class="card-label" style="margin-bottom:15px;">آخرین گزارش‌های ثبت شده</div>
        <div id="logContainer">
            <div style="text-align:center; color:#785c43; padding:15px;">در حال دریافت اطلاعات...</div>
        </div>
    </div>
</div>

<script>
// ================= BOOT SCREEN ANIMATION =================
const steps = [
    { progress: "25%", text: "Connecting to MQTT Broker..." },
    { progress: "50%", text: "Fetching ESP32 Telemetry..." },
    { progress: "80%", text: "Initializing Leather OS Shell..." },
    { progress: "100%", text: "System Ready!" }
];

let stepIdx = 0;
const splashInterval = setInterval(() => {
    if (stepIdx < steps.length) {
        document.getElementById('splash-bar').style.width = steps[stepIdx].progress;
        document.getElementById('splash-status').innerText = steps[stepIdx].text;
        stepIdx++;
    } else {
        clearInterval(splashInterval);
        setTimeout(() => {
            const splash = document.getElementById('splash-screen');
            splash.style.opacity = '0';
            splash.style.visibility = 'hidden';
            document.getElementById('app').style.opacity = '1';
        }, 300);
    }
}, 350);

// ================= SIDEBAR HANDLERS =================
function toggleSidebar(show) {
    document.getElementById('sidebar').classList.toggle('active', show);
    document.getElementById('overlay').classList.toggle('active', show);
}

// ================= API CALLS =================
function sendCmd(cmd) {
    fetch('/api/send_cmd', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cmd: cmd })
    })
    .then(r => r.json())
    .then(res => {
        if (res.status === 'success') {
            fetchData();
        } else {
            alert('خطا: ' + res.message);
        }
    });
}

function updateKeypadPin() {
    const pin = document.getElementById('keypadPinInput').value;
    if (!pin) return alert('رمز جدید کیپد را وارد کنید');
    sendCmd('SET_PASS_' + pin);
    document.getElementById('keypadPinInput').value = '';
    toggleSidebar(false);
    alert('دستور ثبت رمز جدید برای ESP32 ارسال شد.');
}

function changeWebPassword() {
    const oldPass = document.getElementById('oldWebPass').value;
    const newPass = document.getElementById('newWebPass').value;
    fetch('/api/change_password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ old_pass: oldPass, new_pass: newPass })
    })
    .then(r => r.json())
    .then(res => {
        alert(res.message);
        if (res.status === 'success') {
            document.getElementById('oldWebPass').value = '';
            document.getElementById('newWebPass').value = '';
            toggleSidebar(false);
        }
    });
}

// ================= REALTIME DATA POLLING =================
function fetchData() {
    fetch('/api/get_data')
    .then(r => r.json())
    .then(res => {
        if (res.data) {
            const d = res.data;
            document.getElementById('lblTemp').innerText = d.temp || 0;
            document.getElementById('lblHum').innerText = d.hum || 0;
            document.getElementById('lblSoil').innerText = d.soil || 0;
            document.getElementById('lblValve').innerText = d.valve || 'خاموش';

            // Hardware Metrics
            document.getElementById('lblRam').innerText = (d.ram || 0) + ' KB';
            document.getElementById('barRam').style.width = Math.min(100, ((d.ram || 0) / 320) * 100) + '%';
            
            document.getElementById('lblWifi').innerText = (d.wifi_rssi || 0) + ' dBm';
            document.getElementById('barWifi').style.width = Math.max(0, Math.min(100, ((d.wifi_rssi || -100) + 100) * 2)) + '%';
            
            document.getElementById('lblKeypadPin').innerText = d.keypad_pin || '----';
        }

        if (res.logs && res.logs.length > 0) {
            let html = '';
            res.logs.forEach(l => {
                html += `
                <div class="log-item">
                    <div>
                        <strong>${l.event}</strong>
                        <div style="font-size:10px; color:#8c7158;">زمان: ${l.time} | دما: ${l.temp}°C | خاک: ${l.soil}%</div>
                    </div>
                    <span style="color:#64b566; font-weight:bold;">${l.status}</span>
                </div>`;
            });
            document.getElementById('logContainer').innerHTML = html;
        }
    });
}

setInterval(fetchData, 2000);
fetchData();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
