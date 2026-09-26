import sqlite3
import json
from flask import Flask, render_template_string, jsonify, request, session
import paho.mqtt.client as mqtt

app = Flask(__name__)
app.secret_key = "hesam_secret_key_pro_irrigation"

# --- MQTT CONFIGURATION ---
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
TOPIC_COMMAND = "hesam/irrigation/cmd"
TOPIC_STATUS = "hesam/irrigation/status"

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("irrigation.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            temp REAL,
            hum REAL,
            soil INTEGER,
            valve TEXT,
            wifi_ssid TEXT,
            wifi_rssi INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Set default password if not set
    cursor.execute("INSERT OR IGNORE INTO system_config (key, value) VALUES ('password', '12345678')")
    conn.commit()
    conn.close()

init_db()

# --- MQTT CLIENT ---
mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    print("[MQTT] Connected")
    client.subscribe(TOPIC_STATUS)

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        conn = sqlite3.connect("irrigation.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sensor_logs (temp, hum, soil, valve, wifi_ssid, wifi_rssi) VALUES (?, ?, ?, ?, ?, ?)",
            (data.get("temp"), data.get("hum"), data.get("soil"), data.get("valve"), data.get("wifi_ssid"), data.get("wifi_rssi"))
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print("[MQTT ERROR]", e)

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()

# --- HTML TEMPLATE WITH LIVE BACKGROUND & FULL UI ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>سامانه هوشمند حسام</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        @keyframes gradientBG {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        body {
            background: linear-gradient(-45deg, #0f172a, #1e1b4b, #311042, #0284c7);
            background-size: 400% 400%;
            animation: gradientBG 12s ease infinite;
            color: #ffffff;
            font-family: system-ui, -apple-system, sans-serif;
            min-height: 100vh;
            padding-bottom: 30px;
        }
        .glass-card {
            background: rgba(255, 255, 255, 0.12);
            backdrop-filter: blur(12px);
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
            padding: 18px;
            margin-bottom: 15px;
        }
        .btn-custom {
            border-radius: 14px;
            padding: 12px;
            font-weight: bold;
            border: none;
            transition: all 0.2s ease;
        }
        .btn-custom:active { transform: scale(0.96); }
        .val-text { font-size: 1.5rem; font-weight: bold; }
    </style>
</head>
<body>

{% if not logged_in %}
<!-- LOGIN FORM -->
<div class="container d-flex align-items-center justify-content-center" style="min-height: 90vh;">
    <div class="glass-card text-center w-100" style="max-width: 380px;">
        <i class="bi bi-shield-lock-fill text-warning display-4 mb-3"></i>
        <h4 class="fw-bold mb-3">ورود به پنل حسام</h4>
        <form action="/login" method="POST">
            <div class="mb-3">
                <input type="password" name="password" class="form-control text-center fs-5" placeholder="رمز عبور" required>
            </div>
            <button type="submit" class="btn btn-primary w-100 btn-custom">ورود به سیستم</button>
        </form>
    </div>
</div>
{% else %}

<!-- MAIN DASHBOARD -->
<div class="container py-3" style="max-width: 500px;">
    <!-- HEADER -->
    <div class="glass-card d-flex justify-content-between align-items-center">
        <div>
            <h5 class="fw-bold m-0"><i class="bi bi-cpu-fill me-2 text-info"></i>پنل مدیریت حسام</h5>
            <small class="text-light opacity-75" id="wifi-info"><i class="bi bi-wifi"></i> WiFi: -- | --%</small>
        </div>
        <a href="/logout" class="btn btn-outline-light btn-sm rounded-pill"><i class="bi bi-box-arrow-right"></i></a>
    </div>

    <!-- SENSORS GRID -->
    <div class="row g-2 mb-2">
        <div class="col-6">
            <div class="glass-card text-center p-3">
                <i class="bi bi-thermometer-half text-danger fs-3"></i>
                <div class="small opacity-75">دمای محیط</div>
                <div class="val-text text-danger" id="temp">-- C°</div>
            </div>
        </div>
        <div class="col-6">
            <div class="glass-card text-center p-3">
                <i class="bi bi-droplet-fill text-info fs-3"></i>
                <div class="small opacity-75">رطوبت محیط</div>
                <div class="val-text text-info" id="hum">-- %</div>
            </div>
        </div>
        <div class="col-6">
            <div class="glass-card text-center p-3">
                <i class="bi bi-flower2 text-success fs-3"></i>
                <div class="small opacity-75">رطوبت خاک</div>
                <div class="val-text text-success" id="soil">-- %</div>
            </div>
        </div>
        <div class="col-6">
            <div class="glass-card text-center p-3">
                <i class="bi bi-toggle-on text-warning fs-3"></i>
                <div class="small opacity-75">وضعیت آبیاری</div>
                <div class="val-text" id="valve">--</div>
            </div>
        </div>
    </div>

    <!-- CONTROLS & DOOR OPENER -->
    <div class="glass-card">
        <h6 class="fw-bold mb-3"><i class="bi bi-sliders me-1"></i>کنترل دستی</h6>
        <div class="d-grid gap-2">
            <button class="btn btn-success btn-custom" onclick="sendCmd('VALVE_ON')"><i class="bi bi-play-circle me-1"></i> باز کردن شیر آبیاری</button>
            <button class="btn btn-danger btn-custom" onclick="sendCmd('VALVE_OFF')"><i class="bi bi-stop-circle me-1"></i> بستن شیر آبیاری</button>
            <button class="btn btn-warning btn-custom text-dark fw-bold" onclick="sendCmd('OPEN_DOOR')"><i class="bi bi-door-open-fill me-1"></i> باز کردن درب (رله ۲ - ۲ ثانیه)</button>
        </div>
    </div>

    <!-- AUTO SOIL THERMOSTAT CONTROL -->
    <div class="glass-card">
        <h6 class="fw-bold mb-3"><i class="bi bi-robot me-1"></i>تنظیمات اتوماتیک (ترموستات خاک)</h6>
        <div class="input-group mb-2">
            <span class="input-group-text bg-transparent text-light border-secondary">حد آستانه (%)</span>
            <input type="number" id="soilThresh" class="form-control bg-transparent text-light border-secondary text-center" value="20">
            <button class="btn btn-info" onclick="setSoilThresh()">ثبت</button>
        </div>
        <div class="d-flex justify-content-between align-items-center mt-2">
            <span>برنامه‌ریزی اتوماتیک:</span>
            <button class="btn btn-sm btn-outline-light" id="autoBtn" onclick="toggleAuto()">فعال‌سازی</button>
        </div>
    </div>

    <!-- RECENT LOGS -->
    <div class="glass-card">
        <h6 class="fw-bold mb-2"><i class="bi bi-clock-history me-1"></i>آخرین گزارش‌ها</h6>
        <div class="table-responsive">
            <table class="table table-sm table-borderless text-light small m-0">
                <thead><tr class="opacity-50"><th>زمان</th><th>دما</th><th>رطوبت</th><th>خاک</th><th>شیر</th></tr></thead>
                <tbody id="logsTable"></tbody>
            </table>
        </div>
    </div>

    <!-- CHANGE PASSWORD -->
    <div class="glass-card">
        <h6 class="fw-bold mb-2"><i class="bi bi-key me-1"></i>تغییر رمز عبور پنل</h6>
        <div class="input-group">
            <input type="password" id="newPass" class="form-control bg-transparent text-light border-secondary" placeholder="رمز جدید">
            <button class="btn btn-warning" onclick="changePass()">ذخیره</button>
        </div>
    </div>
</div>

<script>
    let isAutoMode = false;

    function updateData() {
        fetch('/api/status')
            .then(res => res.json())
            .then(data => {
                if(data.latest) {
                    document.getElementById('temp').innerText = data.latest.temp + ' C°';
                    document.getElementById('hum').innerText = data.hum ? data.hum + ' %' : data.latest.hum + ' %';
                    document.getElementById('soil').innerText = data.latest.soil + ' %';
                    document.getElementById('valve').innerText = data.latest.valve === 'ON' ? 'OPEN' : 'CLOSED';
                    document.getElementById('wifi-info').innerHTML = `<i class="bi bi-wifi"></i> ${data.latest.wifi_ssid || 'WiFi'} | ${data.latest.wifi_rssi || 0}%`;
                }
                
                let tableHtml = '';
                data.logs.forEach(row => {
                    tableHtml += `<tr><td>${row[5].split(' ')[1]}</td><td>${row[1]}C°</td><td>${row[2]}%</td><td>${row[3]}%</td><td>${row[4]}</td></tr>`;
                });
                document.getElementById('logsTable').innerHTML = tableHtml;
            });
    }

    function sendCmd(cmd) {
        fetch('/api/command', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({cmd}) });
    }

    function setSoilThresh() {
        let val = document.getElementById('soilThresh').value;
        sendCmd('SET_SOIL_' + val);
    }

    function toggleAuto() {
        isAutoMode = !isAutoMode;
        document.getElementById('autoBtn').innerText = isAutoMode ? 'غیرفعال‌سازی' : 'فعال‌سازی';
        document.getElementById('autoBtn').className = isAutoMode ? 'btn btn-sm btn-success' : 'btn btn-sm btn-outline-light';
        sendCmd(isAutoMode ? 'AUTO_ON' : 'AUTO_OFF');
    }

    function changePass() {
        let pass = document.getElementById('newPass').value;
        if(pass.length >= 4) {
            fetch('/api/change_pass', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({pass}) })
                .then(() => alert('رمز عبور تغییر یافت!'));
        }
    }

    setInterval(updateData, 2000);
</script>
{% endif %}
</body>
</html>
"""

# --- ROUTES ---
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, logged_in=session.get('logged_in', False))

@app.route('/login', methods=['POST'])
def login():
    conn = sqlite3.connect("irrigation.db")
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM system_config WHERE key='password'")
    db_pass = cursor.fetchone()[0]
    conn.close()

    if request.form.get('password') == db_pass:
        session['logged_in'] = True
    return index()

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return index()

@app.route('/api/status')
def get_status():
    conn = sqlite3.connect("irrigation.db")
    cursor = conn.cursor()
    cursor.execute("SELECT temp, hum, soil, valve, wifi_ssid, wifi_rssi, timestamp FROM sensor_logs ORDER BY id DESC LIMIT 1")
    latest = cursor.fetchone()
    
    cursor.execute("SELECT id, temp, hum, soil, valve, timestamp FROM sensor_logs ORDER BY id DESC LIMIT 5")
    logs = cursor.fetchall()
    conn.close()

    latest_data = None
    if latest:
        latest_data = {"temp": latest[0], "hum": latest[1], "soil": latest[2], "valve": latest[3], "wifi_ssid": latest[4], "wifi_rssi": latest[5]}

    return jsonify({"latest": latest_data, "logs": logs})

@app.route('/api/command', methods=['POST'])
def handle_command():
    if not session.get('logged_in'): return jsonify({"error": "Unauthorized"}), 401
    cmd = request.json.get('cmd')
    mqtt_client.publish(TOPIC_COMMAND, cmd)
    return jsonify({"status": "sent"})

@app.route('/api/change_pass', methods=['POST'])
def change_pass():
    if not session.get('logged_in'): return jsonify({"error": "Unauthorized"}), 401
    new_pass = request.json.get('pass')
    conn = sqlite3.connect("irrigation.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE system_config SET value=? WHERE key='password'", (new_pass,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
