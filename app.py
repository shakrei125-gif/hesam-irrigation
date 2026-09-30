import json
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
import paho.mqtt.client as mqtt

app = Flask(__name__)
app.secret_key = "hesam_travis_scott_secure_key"

# =========================================================
# MQTT CONFIGURATION
# =========================================================

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883

TOPIC_CMD = "hesam/irrigation/cmd"
TOPIC_STATUS = "hesam/irrigation/status"

latest_device_data = {
    "temp": 0.0,
    "hum": 0.0,
    "soil": 0,
    "valve": "خاموش",
    "door": "بسته",
    "ram": 0,
    "wifi_rssi": 0,
    "cpu": 0,
    "keypad_pin": ""
}

recent_logs = []

def on_connect(client, userdata, flags, rc):
    print("MQTT Connected with code:", rc)
    client.subscribe(TOPIC_STATUS)

def on_message(client, userdata, msg):
    global latest_device_data
    try:
        data = json.loads(msg.payload.decode('utf-8'))
        latest_device_data.update(data)
    except Exception as e:
        print("MQTT JSON Parse Error:", e)

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start()
except Exception as e:
    print("MQTT Connection Error:", e)

# =========================================================
# USER DATABASE
# =========================================================

users_db = {
    "admin": "123456"
}

# =========================================================
# ROUTE: INDEX & LOGIN
# =========================================================

@app.route("/")
def index():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template_string(HTML_TEMPLATE, data=latest_device_data)

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
        return jsonify({"status": "error", "message": "احراز هویت نشده‌اید."}), 401

    data = request.get_json(silent=True) or {}
    old_password = data.get("old_pass")
    new_password = data.get("new_pass")

    if users_db.get(session["user"]) == old_password:
        users_db[session["user"]] = new_password
        return jsonify({"status": "success", "message": "رمز عبور با موفقیت تغییر کرد."})

    return jsonify({"status": "error", "message": "رمز فعلی اشتباه است."}), 400

@app.route("/api/send_cmd", methods=["POST"])
def send_cmd():
    if "user" not in session:
        return jsonify({"status": "error", "message": "احراز هویت نشده‌اید."}), 401

    data = request.get_json(silent=True) or {}
    cmd = data.get("cmd")

    if not cmd:
        return jsonify({"status": "error", "message": "دستور نامعتبر است."}), 400

    try:
        mqtt_client.publish(TOPIC_CMD, cmd)

        event_text = ""
        status_text = ""

        if "VALVE_ON" in cmd:
            event_text = "شروع آبیاری دستی"
            status_text = "فعال"
        elif "VALVE_OFF" in cmd:
            event_text = "پایان آبیاری دستی"
            status_text = "غیرفعال"
        elif "OPEN_DOOR" in cmd:
            event_text = "باز کردن درب از وب‌پنل"
            status_text = "انجام شد"
        elif "SET_PASS_" in cmd:
            event_text = f"تغییر رمز کیپد 3x4 به {cmd.replace('SET_PASS_', '')}"
            status_text = "بروزرسانی"

        if event_text:
            recent_logs.insert(0, {
                "event": event_text,
                "status": status_text,
                "temp": latest_device_data.get("temp", 0),
                "soil": latest_device_data.get("soil", 0)
            })
            recent_logs[:] = recent_logs[:20]

        return jsonify({"status": "success", "message": "دستور با موفقیت ارسال شد."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/get_data")
def get_data():
    if "user" not in session:
        return jsonify({"status": "error"}), 401
    return jsonify({
        "data": latest_device_data,
        "logs": recent_logs[:5]
    })

# =========================================================
# LOGIN TEMPLATE
# =========================================================

LOGIN_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>HESAM SYSTEM - LOGIN</title>
<style>
* { box-sizing: border-box; }
body {
    margin: 0;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: Tahoma, Arial, sans-serif;
    color: #241810;
    background: radial-gradient(circle at 20% 10%, rgba(255,255,255,.65), transparent 30%),
                radial-gradient(circle at 80% 90%, rgba(85,50,28,.15), transparent 35%),
                #d8c3a5;
    overflow: hidden;
}
body::before {
    content: ""; position: fixed; inset: 0; pointer-events: none; opacity: .18;
    background-image: repeating-linear-gradient(45deg, rgba(60,35,20,.15) 0px, rgba(60,35,20,.15) 1px, transparent 1px, transparent 4px);
}
.login-wrapper { width: 390px; padding: 18px; position: relative; }
.login-card {
    position: relative;
    background: linear-gradient(145deg, #4b2f20, #291910);
    color: #f5e8d2; padding: 42px 35px; border-radius: 28px;
    border: 2px solid #806044;
    box-shadow: 0 30px 70px rgba(35,20,10,.45), inset 0 1px 0 rgba(255,255,255,.12);
}
.login-card::before {
    content: ""; position: absolute; inset: 10px; border: 1px dashed #c4a477;
    border-radius: 21px; opacity: .6; pointer-events: none;
}
.logo { text-align: center; font-size: 44px; font-weight: 900; letter-spacing: -3px; color: #e6c28f; }
.subtitle { text-align: center; font-size: 11px; letter-spacing: 4px; opacity: .65; margin-bottom: 35px; }
label { display: block; margin-bottom: 8px; font-size: 13px; color: #d9c2a0; }
input {
    width: 100%; padding: 14px 16px; margin-bottom: 18px; border-radius: 12px;
    border: 1px solid #735239; background: #1e120c; color: white; outline: none;
}
input:focus { border-color: #d5ad76; box-shadow: 0 0 0 3px rgba(213,173,118,.12); }
.login-btn {
    width: 100%; padding: 15px; border: none; border-radius: 13px;
    background: #c19a69; color: #24170e; font-weight: 900; cursor: pointer; transition: .2s;
}
.login-btn:hover { transform: translateY(-2px); background: #e0bc87; }
.error { background: #5d211b; color: #ffd7ce; padding: 10px; border-radius: 10px; margin-bottom: 15px; font-size: 13px; text-align: center; }
</style>
</head>
<body>
<div class="login-wrapper">
    <div class="login-card">
        <div class="logo">HESAM</div>
        <div class="subtitle">SMART IRRIGATION SYSTEM</div>
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
        <form method="POST">
            <label>نام کاربری</label>
            <input type="text" name="username" autocomplete="username" required>
            <label>رمز عبور</label>
            <input type="password" name="password" autocomplete="current-password" required>
            <button type="submit" class="login-btn">ورود به سیستم</button>
        </form>
    </div>
</div>
</body>
</html>
"""

# =========================================================
# MAIN HTML DASHBOARD TEMPLATE
# =========================================================

HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>HESAM IRRIGATION & ACCESS SYSTEM</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
    margin: 0; font-family: "Vazirmatn", Tahoma, sans-serif; color: #281a11; min-height: 100vh;
    background: radial-gradient(circle at 10% 10%, rgba(255,255,255,.7), transparent 28%),
                radial-gradient(circle at 90% 80%, rgba(88,54,31,.14), transparent 35%),
                #d8c3a5;
    overflow-x: hidden;
}
body::before {
    content: ""; position: fixed; inset: 0; pointer-events: none; opacity: .16;
    background-image: repeating-linear-gradient(0deg, rgba(65,38,22,.18) 0px, rgba(65,38,22,.18) 1px, transparent 1px, transparent 4px),
                      repeating-linear-gradient(90deg, rgba(255,255,255,.12) 0px, rgba(255,255,255,.12) 1px, transparent 1px, transparent 6px);
    z-index: 9999;
}
.navbar {
    height: 76px; position: fixed; top: 0; left: 0; right: 0; z-index: 1000;
    display: flex; align-items: center; justify-content: space-between; padding: 0 28px;
    color: #f4e6d0; background: linear-gradient(135deg, #4b3020, #24170f);
    border-bottom: 2px solid #9a7956; box-shadow: 0 10px 35px rgba(35,20,10,.35);
}
.brand { display: flex; align-items: center; gap: 13px; }
.brand-mark {
    width: 45px; height: 45px; display: flex; align-items: center; justify-content: center;
    border-radius: 13px; background: #c49c6a; color: #29190f; font-weight: 900; font-size: 20px;
    transform: rotate(-6deg); box-shadow: 5px 5px 0 #18100b;
}
.brand-title { font-weight: 900; font-size: 18px; letter-spacing: 1px; }
.brand-sub { font-size: 9px; opacity: .55; letter-spacing: 2px; }
.menu-button {
    width: 44px; height: 44px; border-radius: 12px; border: 1px solid #806044;
    background: #352116; color: #e5c18f; cursor: pointer; font-size: 20px;
}
.overlay { position: fixed; inset: 0; background: rgba(18,10,5,.65); backdrop-filter: blur(5px); display: none; z-index: 1040; }
.overlay.active { display: block; }
.side-menu {
    position: fixed; top: 0; right: -350px; width: 330px; height: 100vh; z-index: 1050;
    padding: 30px; color: #f4e6d0; background: linear-gradient(150deg, #43291b, #20130c);
    border-left: 2px solid #806044; box-shadow: -20px 0 60px rgba(0,0,0,.35); transition: .35s;
}
.side-menu.active { right: 0; }
.side-title { font-size: 20px; font-weight: 900; color: #dfba87; }
.side-input { width: 100%; background: #1a0f09; border: 1px solid #63482f; color: white; border-radius: 10px; padding: 12px; margin-bottom: 10px; outline: none; }
.side-btn { width: 100%; padding: 12px; border: none; border-radius: 10px; background: #bd9667; color: #21130b; font-weight: 800; cursor: pointer; margin-bottom: 10px; }
.logout { display: block; text-decoration: none; text-align: center; padding: 12px; border-radius: 10px; background: #642b23; color: white; }
.page { max-width: 1400px; margin: auto; padding: 110px 25px 50px; }
.hero {
    position: relative; min-height: 230px; padding: 40px; overflow: hidden; border-radius: 25px;
    color: #f8ead5; background: linear-gradient(135deg, #503322, #21140d);
    box-shadow: 0 20px 45px rgba(52,31,18,.3); border: 1px solid #866647; margin-bottom: 25px;
}
.hero::before { content: "H"; position: absolute; left: -20px; bottom: -80px; font-size: 330px; line-height: 1; font-weight: 900; color: rgba(255,255,255,.035); transform: rotate(-10deg); }
.hero-content { position: relative; z-index: 2; }
.eyebrow { color: #d5ae79; font-size: 11px; font-weight: 800; letter-spacing: 4px; margin-bottom: 10px; }
.hero h1 { margin: 0; font-size: clamp(28px, 5vw, 52px); font-weight: 900; letter-spacing: -2px; }
.hero p { color: #cdb99f; max-width: 620px; margin: 12px 0 0; line-height: 2; font-size: 13px; }
.grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 22px; }
.stat-card {
    position: relative; overflow: hidden; padding: 22px; min-height: 145px; border-radius: 18px;
    background: rgba(249,238,218,.72); border: 1px solid rgba(104,72,46,.35);
    box-shadow: 0 10px 25px rgba(74,45,24,.12); backdrop-filter: blur(8px);
}
.stat-label { color: #806044; font-size: 12px; font-weight: 700; }
.stat-value { margin-top: 13px; font-size: 30px; font-weight: 900; color: #352116; }
.stat-icon { position: absolute; top: 20px; left: 20px; font-size: 25px; opacity: .45; }
.card { margin-bottom: 20px; border-radius: 20px; overflow: hidden; background: linear-gradient(145deg, rgba(249,238,218,.94), rgba(225,207,178,.88)); border: 1px solid rgba(101,70,43,.4); box-shadow: 0 12px 30px rgba(70,42,22,.14); }
.card-header { padding: 20px 23px; display: flex; align-items: center; justify-content: space-between; background: #3b2518; color: #eed8b8; font-weight: 900; }
.card-body { padding: 23px; }
.controls { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.control-btn { border: none; border-radius: 14px; padding: 17px; cursor: pointer; font-family: inherit; font-weight: 900; color: #fff; transition: .2s; box-shadow: 0 7px 0 rgba(0,0,0,.18); }
.control-btn:hover { transform: translateY(-2px); }
.control-btn:active { transform: translateY(3px); box-shadow: none; }
.on { background: #557044; }
.off { background: #7b3930; }
.door { background: #6b5038; }
.hardware { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
.metric { background: #3b2518; color: #f4e5cf; padding: 18px; border-radius: 15px; }
.metric-top { display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 10px; }
.progress { height: 10px; border-radius: 20px; background: #1f130c; overflow: hidden; }
.progress-bar { height: 100%; width: 0; border-radius: inherit; background: linear-gradient(90deg, #a87d4f, #e2bf8b); transition: .4s; }
.program-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 18px; }
.program { padding: 20px; border-radius: 17px; background: rgba(255,248,236,.65); border: 1px dashed #876b4e; }
.program-title { font-weight: 900; margin-bottom: 15px; color: #4a2e1c; }
.program-inputs { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.program input { width: 100%; padding: 12px; border-radius: 10px; border: 1px solid #ad9272; background: #eee0c7; color: #24170e; outline: none; }
.program button { width: 100%; margin-top: 10px; padding: 11px; border: none; border-radius: 10px; background: #60412b; color: white; cursor: pointer; font-weight: 800; }
.log { display: flex; align-items: center; justify-content: space-between; padding: 16px; margin-bottom: 10px; border-radius: 13px; background: rgba(255,248,235,.75); border-right: 5px solid #705037; }
.log-title { font-weight: 800; color: #382318; }
.log-meta { color: #856f57; font-size: 11px; margin-top: 5px; }
.badge { padding: 6px 10px; border-radius: 20px; font-size: 10px; background: #5b753e; color: white; }
.footer { text-align: center; padding: 25px; color: #765e45; font-size: 10px; letter-spacing: 2px; }

@media(max-width: 1000px) { .grid { grid-template-columns: repeat(2,1fr); } .hardware { grid-template-columns: 1fr; } }
@media(max-width: 700px) { .page { padding: 95px 14px 30px; } .hero { padding: 28px; } .grid { grid-template-columns: 1fr 1fr; } .controls { grid-template-columns: 1fr; } .program-grid { grid-template-columns: 1fr; } }
@media(max-width: 480px) { .grid { grid-template-columns: 1fr; } .navbar { padding: 0 15px; } .brand-sub { display: none; } }
</style>
</head>
<body>

<nav class="navbar">
    <div class="brand">
        <div class="brand-mark">H</div>
        <div>
            <div class="brand-title">HESAM IRRIGATION</div>
            <div class="brand-sub">SMART ACCESS & CONTROL</div>
        </div>
    </div>
    <button class="menu-button" id="menuBtn">☰</button>
</nav>

<div class="overlay" id="overlay"></div>

<div class="side-menu" id="sideMenu">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:30px;">
        <div class="side-title">تنظیمات سیستم</div>
        <button id="closeMenu" style="background:none; border:none; color:white; font-size:25px; cursor:pointer;">×</button>
    </div>

    <div style="color:#d0b898; font-size:13px; margin-bottom:12px;">تغییر رمز وب‌پنل</div>
    <input id="oldPass" class="side-input" type="password" placeholder="رمز فعلی وب">
    <input id="newPass" class="side-input" type="password" placeholder="رمز جدید وب">
    <button class="side-btn" onclick="changePassword()">ذخیره رمز جدید وب</button>

    <hr style="border-color: #63482f; margin: 20px 0;">

    <div style="color:#d0b898; font-size:13px; margin-bottom:12px;">تنظیم رمز جدید کیپد 3x4</div>
    <input id="keypadPass" class="side-input" type="text" placeholder="رمز ۴ رقمی جدید کیپد">
    <button class="side-btn" onclick="updateKeypadPin()">ارسال رمز به ESP32</button>

    <a href="/logout" class="logout" style="margin-top:20px;">خروج از حساب</a>
</div>

<main class="page">
<section class="hero">
    <div class="hero-content">
        <div class="eyebrow">HESAM / SMART GARDEN & ACCESS</div>
        <h1>کنترل هوشمند آبیاری و قفل درب</h1>
        <p>پایش آنلاین سنسورها، شیر برقی، کیپد ۳ در ۴ و قفل درب به همراه مدیریت سخت‌افزار ESP32.</p>
    </div>
</section>

<section class="grid">
    <div class="stat-card">
        <div class="stat-label">دمای محیط</div>
        <div class="stat-value" id="lblTemp">-- °C</div>
        <div class="stat-icon">🌡</div>
    </div>
    <div class="stat-card">
        <div class="stat-label">رطوبت هوا</div>
        <div class="stat-value" id="lblHum">-- %</div>
        <div class="stat-icon">💧</div>
    </div>
    <div class="stat-card">
        <div class="stat-label">رطوبت خاک</div>
        <div class="stat-value" id="lblSoil">-- %</div>
        <div class="stat-icon">🌱</div>
    </div>
    <div class="stat-card">
        <div class="stat-label">وضعیت شیر / قفل</div>
        <div class="stat-value" id="lblValve" style="font-size:20px;">--</div>
        <div class="stat-icon">🚿</div>
    </div>
</section>

<section class="card">
    <div class="card-header">
        <span>کنترل مستقیم تجهیزات</span>
        <span>LIVE</span>
    </div>
    <div class="card-body">
        <div class="controls">
            <button class="control-btn on" onclick="sendCmd('VALVE_ON')">▶ باز کردن شیر</button>
            <button class="control-btn off" onclick="sendCmd('VALVE_OFF')">■ بستن شیر</button>
            <button class="control-btn door" onclick="sendCmd('OPEN_DOOR')">🔓 باز کردن درب</button>
        </div>
    </div>
</section>

<section class="card">
    <div class="card-header">
        <span>وضعیت سخت‌افزار ESP32</span>
        <span>SYSTEM</span>
    </div>
    <div class="card-body">
        <div class="hardware">
            <div class="metric">
                <div class="metric-top">
                    <span>RAM Free</span>
                    <span id="lblRam">0 KB</span>
                </div>
                <div class="progress">
                    <div class="progress-bar" id="barRam"></div>
                </div>
            </div>
            <div class="metric">
                <div class="metric-top">
                    <span>Wi-Fi Signal</span>
                    <span id="lblWifi">0 dBm</span>
                </div>
                <div class="progress">
                    <div class="progress-bar" id="barWifi"></div>
                </div>
            </div>
            <div class="metric">
                <div class="metric-top">
                    <span>Keypad PIN Entry</span>
                    <span id="lblKeypadEntry">---</span>
                </div>
                <div class="progress">
                    <div class="progress-bar" id="barKeypad" style="width: 100%;"></div>
                </div>
            </div>
        </div>
    </div>
</section>

<section class="card">
    <div class="card-header">
        <span>برنامه‌ریزی آبیاری</span>
        <span>SCHEDULE</span>
    </div>
    <div class="card-body">
        <div class="program-grid">
            <div class="program">
                <div class="program-title">برنامه ۱</div>
                <div class="program-inputs">
                    <input type="number" id="p1_h" min="0" max="23" placeholder="ساعت">
                    <input type="number" id="p1_m" min="0" max="59" placeholder="دقیقه">
                    <input type="number" id="p1_d" min="1" placeholder="مدت (دقیقه)">
                </div>
                <button onclick="saveProg(1)">ذخیره برنامه ۱</button>
            </div>
            <div class="program">
                <div class="program-title">برنامه ۲</div>
                <div class="program-inputs">
                    <input type="number" id="p2_h" min="0" max="23" placeholder="ساعت">
                    <input type="number" id="p2_m" min="0" max="59" placeholder="دقیقه">
                    <input type="number" id="p2_d" min="1" placeholder="مدت (دقیقه)">
                </div>
                <button onclick="saveProg(2)">ذخیره برنامه ۲</button>
            </div>
        </div>
    </div>
</section>

<section class="card">
    <div class="card-header">
        <span>آخرین رویدادهای سیستم</span>
        <span>LOG</span>
    </div>
    <div class="card-body" id="logContainer">
        <div style="text-align:center; color:#806a52; padding:20px;">هنوز گزارشی ثبت نشده است.</div>
    </div>
</section>

<div class="footer">HESAM SMART IRRIGATION & ACCESS CONTROL SYSTEM · ESP32 · MQTT</div>
</main>

<script>
// =========================================================
// SIDE MENU HANDLERS
// =========================================================
const menuBtn = document.getElementById("menuBtn");
const sideMenu = document.getElementById("sideMenu");
const overlay = document.getElementById("overlay");
const closeMenu = document.getElementById("closeMenu");

menuBtn.onclick = () => { sideMenu.classList.add("active"); overlay.classList.add("active"); };
function closeSideMenu() { sideMenu.classList.remove("active"); overlay.classList.remove("active"); }
closeMenu.onclick = closeSideMenu;
overlay.onclick = closeSideMenu;

// =========================================================
// COMMAND & API CALLS
// =========================================================
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
    })
    .catch(err => console.error(err));
}

function updateKeypadPin() {
    const pin = document.getElementById('keypadPass').value;
    if (!pin) { alert('لطفا رمز جدید را وارد کنید'); return; }
    sendCmd('SET_PASS_' + pin);
    document.getElementById('keypadPass').value = '';
    closeSideMenu();
    alert('رمز جدید کیپد برای ESP32 ارسال شد.');
}

function changePassword() {
    const oldPass = document.getElementById('oldPass').value;
    const newPass = document.getElementById('newPass').value;

    fetch('/api/change_password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ old_pass: oldPass, new_pass: newPass })
    })
    .then(r => r.json())
    .then(res => {
        alert(res.message);
        if (res.status === 'success') {
            document.getElementById('oldPass').value = '';
            document.getElementById('newPass').value = '';
            closeSideMenu();
        }
    });
}

function saveProg(progNum) {
    const h = document.getElementById(`p${progNum}_h`).value || 0;
    const m = document.getElementById(`p${progNum}_m`).value || 0;
    const d = document.getElementById(`p${progNum}_d`).value || 0;
    sendCmd(`SET_PROG_${progNum}_${h}_${m}_${d}`);
    alert(`برنامه ${progNum} با موفقیت ارسال شد.`);
}

// =========================================================
// LIVE DATA REFRESH (POLLING)
// =========================================================
function fetchData() {
    fetch('/api/get_data')
    .then(r => r.json())
    .then(res => {
        if (res.data) {
            const d = res.data;
            document.getElementById('lblTemp').innerText = (d.temp || 0) + ' °C';
            document.getElementById('lblHum').innerText = (d.hum || 0) + ' %';
            document.getElementById('lblSoil').innerText = (d.soil || 0) + ' %';
            document.getElementById('lblValve').innerText = `شیر: ${d.valve || 'خاموش'} | درب: ${d.door || 'بسته'}`;

            // Hardware Metrics
            const ramKb = d.ram || 0;
            document.getElementById('lblRam').innerText = ramKb + ' KB';
            document.getElementById('barRam').style.width = Math.min(100, (ramKb / 320) * 100) + '%';

            const wifiRssi = d.wifi_rssi || -60;
            document.getElementById('lblWifi').innerText = wifiRssi + ' dBm';
            document.getElementById('barWifi').style.width = Math.max(0, Math.min(100, (wifiRssi + 100) * 2)) + '%';

            document.getElementById('lblKeypadEntry').innerText = d.keypad_pin || '---';
        }

        if (res.logs && res.logs.length > 0) {
            let html = '';
            res.logs.forEach(l => {
                html += `
                <div class="log">
                    <div>
                        <div class="log-title">${l.event}</div>
                        <div class="log-meta">دما: ${l.temp}°C | رطوبت خاک: ${l.soil}%</div>
                    </div>
                    <span class="badge">${l.status}</span>
                </div>`;
            });
            document.getElementById('logContainer').innerHTML = html;
        }
    })
    .catch(err => console.error(err));
}

setInterval(fetchData, 2000);
fetchData();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
