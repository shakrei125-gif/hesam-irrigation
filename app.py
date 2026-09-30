import json
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
import paho.mqtt.client as mqtt

app = Flask(__name__)
app.secret_key = "hesam_travis_scott_secure_key"

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
TOPIC_CMD = "hesam/irrigation/cmd"
TOPIC_STATUS = "hesam/irrigation/status"

latest_device_data = {
    "temp": 0.0, "hum": 0.0, "soil": 0, "valve": "خاموش",
    "wifi_rssi": 0, "ram_free": 0, "flash_used": 0, "cpu_usage": 0
}
recent_logs = []

def on_connect(client, userdata, flags, rc):
    client.subscribe(TOPIC_STATUS)

def on_message(client, userdata, msg):
    global latest_device_data
    try:
        data = json.loads(msg.payload.decode())
        latest_device_data.update(data)
    except Exception:
        pass

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start()
except Exception as e:
    print("MQTT Connection Error:", e)

users_db = {"admin": "123456"}

@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template_string(HTML_TEMPLATE, data=latest_device_data)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        u, p = request.form.get('username'), request.form.get('password')
        if u in users_db and users_db[u] == p:
            session['user'] = u
            return redirect(url_for('index'))
        error = "نام کاربری یا رمز عبور نادرست است."
    return render_template_string(LOGIN_TEMPLATE, error=error)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/api/change_password', methods=['POST'])
def change_password():
    if 'user' not in session: return jsonify({"status": "error"}), 401
    old_p, new_p = request.form.get('old_pass'), request.form.get('new_pass')
    if users_db.get(session['user']) == old_p:
        users_db[session['user']] = new_p
        return jsonify({"status": "success", "message": "رمز عبور تغییر یافت."})
    return jsonify({"status": "error", "message": "رمز فعلی اشتباه است."})

@app.route('/api/send_cmd', methods=['POST'])
def send_cmd():
    if 'user' not in session: return jsonify({"status": "error"}), 401
    cmd = request.json.get('cmd')
    if cmd:
        mqtt_client.publish(TOPIC_CMD, cmd)
        if "VALVE_ON" in cmd:
            recent_logs.insert(0, {"event": "شروع آبیاری دستی", "status": "فعال", "temp": latest_device_data['temp'], "soil": latest_device_data['soil']})
        elif "VALVE_OFF" in cmd:
            recent_logs.insert(0, {"event": "پایان آبیاری دستی", "status": "غیرفعال", "temp": latest_device_data['temp'], "soil": latest_device_data['soil']})
        return jsonify({"status": "success", "message": f"دستور {cmd} ارسال شد."})
    return jsonify({"status": "error"})

@app.route('/api/get_data')
def get_data():
    return jsonify({"data": latest_device_data, "logs": recent_logs[:5]})

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>ورود | سیستم هوشمند حسام</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css" rel="stylesheet">
    <style>
        body { background: #1c1410; color: #f2e9d8; height: 100vh; display: flex; align-items: center; justify-content: center; font-family: Tahoma, sans-serif; }
        .card { background: #2b1e16; border: 2px solid #8c6d53; border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.8); width: 360px; }
        .btn-custom { background: #8c6d53; color: #fff; border: none; font-weight: bold; }
        .btn-custom:hover { background: #a68265; color: #fff; }
        .form-control { background: #1c1410; border: 1px solid #594231; color: #f2e9d8; }
        .form-control:focus { background: #2b1e16; color: #fff; border-color: #8c6d53; box-shadow: none; }
    </style>
</head>
<body>
    <div class="card p-4">
        <h4 class="text-center mb-4" style="color:#d9b382;">سیستم هوشمند حسام</h4>
        {% if error %}<div class="alert alert-danger py-2 small">{{ error }}</div>{% endif %}
        <form method="POST">
            <div class="mb-3"><label class="form-label">نام کاربری</label><input type="text" name="username" class="form-control" required></div>
            <div class="mb-3"><label class="form-label">رمز عبور</label><input type="password" name="password" class="form-control" required></div>
            <button type="submit" class="btn btn-custom w-100 py-2">ورود به سیستم</button>
        </form>
    </div>
</body>
</html>
"""

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>پنل مدیریت هوشمند حسام</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body {
            background-color: #120c09;
            background-image: radial-gradient(#2b1e16 1px, transparent 0);
            background-size: 24px 24px;
            color: #f2e9d8;
            font-family: Tahoma, sans-serif;
            padding-top: 70px;
        }
        .navbar { background: #2b1e16; border-bottom: 2px solid #594231; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
        .card {
            background: linear-gradient(145deg, #231710, #1c1410);
            border: 1px solid #423023;
            border-radius: 14px;
            box-shadow: 0 8px 20px rgba(0,0,0,0.4);
            margin-bottom: 20px;
        }
        .card-header {
            background: #2b1e16;
            border-bottom: 1px solid #423023;
            color: #d9b382;
            font-weight: bold;
            cursor: pointer;
        }
        .side-menu {
            position: fixed; top: 0; right: -300px; width: 300px; height: 100%;
            background: #1c1410; border-left: 2px solid #594231; transition: 0.3s; z-index: 1050; padding: 25px;
        }
        .side-menu.active { right: 0; }
        .overlay { position: fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.7); display:none; z-index:1040; }
        .overlay.active { display:block; }
        .btn-brown { background: #8c6d53; color: white; border: none; }
        .btn-brown:hover { background: #a68265; color: white; }
        .progress { background-color: #120c09; height: 10px; border-radius: 5px; }
        .progress-bar { background-color: #d9b382; }
        .stat-box { background: #1a110c; border: 1px solid #36261c; border-radius: 10px; padding: 15px; text-align: center; }
        .form-control { background: #120c09; border: 1px solid #423023; color: #f2e9d8; }
        .form-control:focus { background: #1a110c; color: #fff; border-color: #8c6d53; box-shadow: none; }
    </style>
</head>
<body>

    <nav class="navbar navbar-dark fixed-top px-3">
        <span class="navbar-brand mb-0 h1" style="color:#d9b382;"><i class="fa-solid fa-leaf me-2"></i> سیستم آبیاری حسام</span>
        <button class="btn btn-outline-light border-0" id="menuBtn"><i class="fa-solid fa-bars fs-4" style="color:#d9b382;"></i></button>
    </nav>

    <div class="overlay" id="overlay"></div>
    <div class="side-menu" id="sideMenu">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h5 class="m-0" style="color:#d9b382;">تنظیمات کاربری</h5>
            <button class="btn-close btn-close-white" id="closeMenu"></button>
        </div>
        <hr style="border-color:#594231;">
        <div class="mb-4">
            <h6><i class="fa-solid fa-lock me-2"></i> تغییر رمز عبور</h6>
            <input type="password" id="oldPass" class="form-control form-control-sm mb-2" placeholder="رمز فعلی">
            <input type="password" id="newPass" class="form-control form-control-sm mb-2" placeholder="رمز جدید">
            <button class="btn btn-sm btn-brown w-100" onclick="changePassword()">ثبت تغییر رمز</button>
        </div>
        <hr style="border-color:#594231;">
        <a href="/logout" class="btn btn-danger w-100"><i class="fa-solid fa-right-from-bracket me-2"></i> خروج</a>
    </div>

    <div class="container mt-3">
        
        <!-- Accordion 1: Realtime Status -->
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center" data-bs-toggle="collapse" data-bs-target="#secStatus">
                <span><i class="fa-solid fa-gauge-high me-2"></i> وضعیت لحظه‌ای سیستم</span>
                <i class="fa-solid fa-chevron-down"></i>
            </div>
            <div id="secStatus" class="collapse show card-body">
                <div class="row g-3">
                    <div class="col-6 col-md-3"><div class="stat-box"><div class="text-muted small">دما</div><h3 id="lblTemp" style="color:#e06d53;">-- °C</h3></div></div>
                    <div class="col-6 col-md-3"><div class="stat-box"><div class="text-muted small">رطوبت هوا</div><h3 id="lblHum" style="color:#53a6e0;">-- %</h3></div></div>
                    <div class="col-6 col-md-3"><div class="stat-box"><div class="text-muted small">رطوبت خاک</div><h3 id="lblSoil" style="color:#e0b353;">-- %</h3></div></div>
                    <div class="col-6 col-md-3"><div class="stat-box"><div class="text-muted small">وضعیت شیر</div><h3 id="lblValve" style="color:#53e085;">--</h3></div></div>
                </div>
                <div class="d-flex justify-content-center gap-2 mt-4">
                    <button class="btn btn-success px-4" onclick="sendCmd('VALVE_ON')"><i class="fa-solid fa-play me-1"></i> باز کردن شیر</button>
                    <button class="btn btn-danger px-4" onclick="sendCmd('VALVE_OFF')"><i class="fa-solid fa-stop me-1"></i> بستن شیر</button>
                    <button class="btn btn-brown px-4" onclick="sendCmd('OPEN_DOOR')"><i class="fa-solid fa-door-open me-1"></i> درب‌بازکن</button>
                </div>
            </div>
        </div>

        <!-- Accordion 2: OS Hardware Stats -->
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center" data-bs-toggle="collapse" data-bs-target="#secHardware">
                <span><i class="fa-solid fa-microchip me-2"></i> آمار سیستم‌عامل (ESP32 OS)</span>
                <i class="fa-solid fa-chevron-down"></i>
            </div>
            <div id="secHardware" class="collapse card-body">
                <div class="mb-3">
                    <div class="d-flex justify-content-between small mb-1"><span>درگیری پردازنده (CPU Load)</span><span id="lblCpu">0%</span></div>
                    <div class="progress"><div id="barCpu" class="progress-bar" style="width: 0%"></div></div>
                </div>
                <div class="mb-3">
                    <div class="d-flex justify-content-between small mb-1"><span>حافظه RAM آزاد</span><span id="lblRam">0 KB</span></div>
                    <div class="progress"><div id="barRam" class="progress-bar bg-info" style="width: 0%"></div></div>
                </div>
                <div class="mb-3">
                    <div class="d-flex justify-content-between small mb-1"><span>حافظه Flash استفاده شده</span><span id="lblFlash">0 KB</span></div>
                    <div class="progress"><div id="barFlash" class="progress-bar bg-warning" style="width: 0%"></div></div>
                </div>
            </div>
        </div>

        <!-- Accordion 3: Scheduler Program -->
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center" data-bs-toggle="collapse" data-bs-target="#secProg">
                <span><i class="fa-regular fa-clock me-2"></i> تنظیمات پروگرم آبیاری</span>
                <i class="fa-solid fa-chevron-down"></i>
            </div>
            <div id="secProg" class="collapse card-body">
                <div class="row g-3">
                    <div class="col-md-6">
                        <div class="stat-box text-start">
                            <h6>برنامه ۱</h6>
                            <div class="row g-2 mb-2">
                                <div class="col"><input type="number" id="p1_h" class="form-control" placeholder="ساعت"></div>
                                <div class="col"><input type="number" id="p1_m" class="form-control" placeholder="دقیقه"></div>
                                <div class="col"><input type="number" id="p1_d" class="form-control" placeholder="مدت (دقیقه)"></div>
                            </div>
                            <button class="btn btn-sm btn-brown w-100" onclick="saveProg(1)">ذخیره برنامه ۱</button>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="stat-box text-start">
                            <h6>برنامه ۲</h6>
                            <div class="row g-2 mb-2">
                                <div class="col"><input type="number" id="p2_h" class="form-control" placeholder="ساعت"></div>
                                <div class="col"><input type="number" id="p2_m" class="form-control" placeholder="دقیقه"></div>
                                <div class="col"><input type="number" id="p2_d" class="form-control" placeholder="مدت (دقیقه)"></div>
                            </div>
                            <button class="btn btn-sm btn-brown w-100" onclick="saveProg(2)">ذخیره برنامه ۲</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Accordion 4: Logs -->
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center" data-bs-toggle="collapse" data-bs-target="#secLogs">
                <span><i class="fa-solid fa-receipt me-2"></i> آخرین گزارش‌های سیستم</span>
                <i class="fa-solid fa-chevron-down"></i>
            </div>
            <div id="secLogs" class="collapse show card-body" id="logContainer">
                <div class="text-center text-muted">گزارشی ثبت نشده است.</div>
            </div>
        </div>

    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        const menuBtn = document.getElementById('menuBtn'), sideMenu = document.getElementById('sideMenu'), overlay = document.getElementById('overlay'), closeMenu = document.getElementById('closeMenu');
        menuBtn.onclick = () => { sideMenu.classList.add('active'); overlay.classList.add('active'); };
        closeMenu.onclick = overlay.onclick = () => { sideMenu.classList.remove('active'); overlay.classList.remove('active'); };

        function sendCmd(cmd) {
            fetch('/api/send_cmd', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({cmd: cmd}) })
            .then(r => r.json()).then(d => alert(d.message));
        }

        function saveProg(num) {
            let h = document.getElementById(`p${num}_h`).value, m = document.getElementById(`p${num}_m`).value, d = document.getElementById(`p${num}_d`).value;
            sendCmd(`SET_PROG_${num}_${h}_${m}_${d}`);
        }

        function changePassword() {
            let formData = new FormData();
            formData.append('old_pass', document.getElementById('oldPass').value);
            formData.append('new_pass', document.getElementById('newPass').value);
            fetch('/api/change_password', { method: 'POST', body: formData }).then(r => r.json()).then(d => alert(d.message));
        }

        setInterval(() => {
            fetch('/api/get_data').then(r => r.json()).then(res => {
                let d = res.data;
                document.getElementById('lblTemp').innerText = d.temp + ' °C';
                document.getElementById('lblHum').innerText = d.hum + ' %';
                document.getElementById('lblSoil').innerText = d.soil + ' %';
                document.getElementById('lblValve').innerText = d.valve;

                document.getElementById('lblCpu').innerText = (d.cpu_usage || 0) + '%';
                document.getElementById('barCpu').style.width = (d.cpu_usage || 0) + '%';
                document.getElementById('lblRam').innerText = (d.ram_free || 0) + ' KB';
                document.getElementById('barRam').style.width = (((320 - (d.ram_free || 180))/320)*100) + '%';
                document.getElementById('lblFlash').innerText = (d.flash_used || 0) + ' KB';
                document.getElementById('barFlash').style.width = (((d.flash_used || 1000)/4096)*100) + '%';

                let logHtml = '';
                res.logs.forEach(l => {
                    logHtml += `<div class="p-2 mb-2 rounded" style="background:#1a110c; border-right:4px solid #8c6d53;">
                        <div class="d-flex justify-content-between"><strong>${l.event}</strong><span class="badge bg-secondary">${l.status}</span></div>
                        <div class="small text-muted mt-1">دما: ${l.temp}°C | خاک: ${l.soil}%</div>
                    </div>`;
                });
                if(logHtml !== '') document.getElementById('logContainer').innerHTML = logHtml;
            });
        }, 3000);
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
