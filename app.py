import sqlite3
import json
from flask import Flask, render_template_string, jsonify, request
import paho.mqtt.client as mqtt

app = Flask(__name__)

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
        CREATE TABLE IF NOT EXISTS sensor_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            temp REAL,
            hum REAL,
            soil INTEGER,
            valve TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- MQTT CLIENT SETUP ---
mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    print("[MQTT] Connected to Broker")
    client.subscribe(TOPIC_STATUS)

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        conn = sqlite3.connect("irrigation.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sensor_logs (temp, hum, soil, valve) VALUES (?, ?, ?, ?)",
            (data.get("temp"), data.get("hum"), data.get("soil"), data.get("valve"))
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print("[MQTT ERROR]", e)

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()

# --- MOBILE RESPONSIVE HTML & PWA TEMPLATE ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>کنترل آبیاری حسام</title>
    <meta name="theme-color" content="#0d6efd">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        body { background-color: #f0f2f5; font-family: system-ui, -apple-system, sans-serif; user-select: none; }
        .app-header { background: #0d6efd; color: white; padding: 15px; border-radius: 0 0 20px 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        .stat-card { background: white; border-radius: 16px; padding: 15px; border: none; box-shadow: 0 2px 8px rgba(0,0,0,0.05); text-align: center; }
        .stat-card i { font-size: 1.8rem; margin-bottom: 5px; }
        .val-text { font-size: 1.4rem; font-weight: bold; }
        .btn-control { border-radius: 14px; padding: 14px; font-weight: bold; font-size: 1.1rem; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        .valve-on { background-color: #198754; color: white; }
        .valve-off { background-color: #dc3545; color: white; }
    </style>
</head>
<body>

    <!-- Header -->
    <div class="app-header text-center mb-3">
        <h5 class="m-0 fw-bold"><i class="bi bi-droplet-half me-2"></i>سامانه آبیاری حسام</h5>
        <small class="opacity-75">کنترل از راه دور (Mobile Web App)</small>
    </div>

    <div class="container px-3">
        <!-- Status Grid -->
        <div class="row g-2 mb-3">
            <div class="col-6">
                <div class="stat-card">
                    <i class="bi bi-thermometer-half text-danger"></i>
                    <div class="text-muted small">دمای محیط</div>
                    <div class="val-text text-danger" id="temp">-- C°</div>
                </div>
            </div>
            <div class="col-6">
                <div class="stat-card">
                    <i class="bi bi-moisture text-info"></i>
                    <div class="text-muted small">رطوبت هوا</div>
                    <div class="val-text text-info" id="hum">-- %</div>
                </div>
            </div>
            <div class="col-6">
                <div class="stat-card">
                    <i class="bi bi-flower2 text-success"></i>
                    <div class="text-muted small">رطوبت خاک</div>
                    <div class="val-text text-success" id="soil">-- %</div>
                </div>
            </div>
            <div class="col-6">
                <div class="stat-card">
                    <i class="bi bi-power text-warning"></i>
                    <div class="text-muted small">وضعیت شیر</div>
                    <div class="val-text" id="valve">--</div>
                </div>
            </div>
        </div>

        <!-- Controls -->
        <div class="stat-card p-3 mb-3">
            <h6 class="fw-bold mb-3"><i class="bi bi-sliders me-1"></i>فرمان سریع</h6>
            <div class="d-grid gap-2">
                <button class="btn btn-success btn-control" onclick="sendCommand('VALVE_ON')">
                    <i class="bi bi-play-circle me-1"></i> باز کردن شیر آبیاری
                </button>
                <button class="btn btn-danger btn-control" onclick="sendCommand('VALVE_OFF')">
                    <i class="bi bi-stop-circle me-1"></i> بستن شیر آبیاری
                </button>
            </div>
        </div>
    </div>

    <script>
        function updateDashboard() {
            fetch('/api/latest')
                .then(res => res.json())
                .then(data => {
                    if (data) {
                        document.getElementById('temp').innerText = data.temp + ' C°';
                        document.getElementById('hum').innerText = data.hum + ' %';
                        document.getElementById('soil').innerText = data.soil + ' %';
                        
                        const valveElem = document.getElementById('valve');
                        if (data.valve === 'ON') {
                            valveElem.innerText = 'OPEN';
                            valveElem.className = 'val-text text-success';
                        } else {
                            valveElem.innerText = 'CLOSED';
                            valveElem.className = 'val-text text-danger';
                        }
                    }
                });
        }

        function sendCommand(cmd) {
            fetch('/api/control', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({command: cmd})
            });
        }

        setInterval(updateDashboard, 2000);
    </script>
</body>
</html>
"""

# --- ROUTES ---
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/latest')
def get_latest():
    conn = sqlite3.connect("irrigation.db")
    cursor = conn.cursor()
    cursor.execute("SELECT temp, hum, soil, valve FROM sensor_logs ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return jsonify({"temp": row[0], "hum": row[1], "soil": row[2], "valve": row[3]})
    return jsonify(None)

@app.route('/api/control', methods=['POST'])
def control():
    cmd = request.json.get('command')
    if cmd:
        mqtt_client.publish(TOPIC_COMMAND, cmd)
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)