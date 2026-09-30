import json
import random
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
import paho.mqtt.client as mqtt

app = Flask(__name__)
app.secret_key = "hesam_secret_key_secure_123"

# ==========================================
# MQTT CONFIGURATION (Server Side)
# ==========================================
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
TOPIC_CMD = "hesam/irrigation/cmd"
TOPIC_STATUS = "hesam/irrigation/status"

latest_device_data = {
    "temp": 0.0,
    "hum": 0.0,
    "soil": 0,
    "valve": "OFF",
    "wifi_ssid": "N/A",
    "wifi_rssi": 0,
    "ram_free": 0,
    "ram_total": 320,  # ESP32 Standard SRAM KB
    "flash_used": 0,
    "flash_total": 4096, # 4MB
    "cpu_usage": 0
}

recent_logs = []

def on_connect(client, userdata, flags, rc):
    client.subscribe(TOPIC_STATUS)

def on_message(client, userdata, msg):
    global latest_device_data
    try:
        data = json.loads(msg.payload.decode())
        latest_device_data.update(data)
    except Exception as e:
        pass

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start()
except Exception as e:
    print("MQTT Connection Error:", e)

# ==========================================
# USER DATABASE (Mock - Can be SQLite)
# ==========================================
users_db = {
    "admin": "123456"
}

# ==========================================
# ROUTES
# ==========================================
@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template_string(HTML_TEMPLATE, data=latest_device_data, logs=recent_logs)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username in users_db and users_db[username] == password:
            session['user'] = username
            return redirect(url_for('index'))
        error = "نام کاربری یا رمز عبور اشتباه است."
    return render_template_string(LOGIN_TEMPLATE, error=error)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/api/change_password', methods=['POST'])
def change_password():
    if 'user' not in session:
        return jsonify({"status": "error", "message": "عدم دسترسی"}), 401
    
    old_pass = request.form.get('old_pass')
    new_pass = request.form.get('new_pass')
    current_user = session['user']
    
    if users_db.get(current_user) == old_pass:
        users_db[current_user] = new_pass
        return jsonify({"status": "success", "message": "رمز عبور با موفقیت تغییر کرد"})
    return jsonify({"status": "error", "message": "رمز عبور فعلی اشتباه است"})

@app.route('/api/send_cmd', methods=['POST'])
def send_cmd():
    if 'user' not in session:
        return jsonify({"status": "error", "message": "عدم دسترسی"}), 401
    
    cmd = request.json.get('cmd')
    if cmd:
        mqtt_client.publish(TOPIC_CMD, cmd)
        
        # Log event if valve or door action
        if "VALVE_ON" in cmd:
            recent_logs.insert(0, {
                "event": "شروع آبیاری (باز شدن رله)",
                "temp": latest_device_data['temp'],
                "hum": latest_device_data['hum'],
                "soil": latest_device_data['soil'],
                "status": "تایید وجود رطوبت اولیه"
            })
        elif "VALVE_OFF" in cmd:
            recent_logs.insert(0, {
                "event": "پایان آبیاری (بستن رله)",
                "temp": latest_device_data['temp'],
                "hum": latest_device_data['hum'],
                "soil": latest_device_data['soil'],
                "status": "تایید اتمام فرایند"
            })
            
        return jsonify({"status": "success", "message": f"دستور {cmd} ارسال شد"})
    return jsonify({"status": "error", "message": "دستور نامعتبر"})

@app.route('/api/get_data')
def get_data():
    return jsonify({"data": latest_device_data, "logs": recent_logs[:5]})

# ==========================================
# FRONTEND TEMPLATES (HTML/CSS/JS)
# ==========================================
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ورود به سامانه هوشمند حسام</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css" rel="stylesheet">
    <style>
        body { background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); height: 100vh; display: flex; align-items: center; justify-content: center; font-family: Tahoma, sans-serif; }
        .card { width: 380px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); border: none; }
        .btn-primary { background: #2a5298; border: none; }
    </style>
</head>
<body>
    <div class="card p-4">
        <h4 class="text-center mb-4 text-primary fw-bold">ورود به پنل مدیریت</h4>
        {% if error %}<div class="alert alert-danger py-2">{{ error }}</div>{% endif %}
        <form method="POST">
            <div class="mb-3">
                <label class="form-label">نام کاربری</label>
                <input type="text" name="username" class="form-control" required>
            </div>
            <div class="mb-3">
                <label class="form-label">رمز عبور</label>
                <input type="password" name="password" class="form-control" required>
            </div>
            <button type="submit" class="btn btn-primary w-100 py-2">ورود به سیستم</button>
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
    <title>مدیریت هوشمند آبیاری حسام</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { background-color: #f4f6f9; font-family: Tahoma, sans-serif; padding-top: 60px; }
        .navbar { background: #1a237e; box-shadow: 0 2px 10px rgba(0,0,0,0.2); }
        .side-menu { position: fixed; top: 0; right: -280px; width: 280px; height: 100%; background: #283593; color: white; transition: 0.3s; z-index: 1050; padding: 20px; }
        .side-menu.active { right: 0; }
        .overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); display: none; z-index: 1040; }
        .overlay.active { display: block; }
        .card { border-radius: 12px; border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px; }
        .card-header { background: white; border-bottom: 1px solid #edf2f7; font-weight: bold; cursor: pointer; }
        .progress { height: 12px; border-radius: 6px; }
        .log-card { border-right: 4px solid #1a237e; background: #fff; padding: 15px; border-radius: 8px; margin-bottom: 10px; }
    </style>
</head>
<body>

    <!-- Top Navbar -->
    <nav class="navbar navbar-dark fixed-top px-3">
        <span class="navbar-brand mb-0 h1"><i class="fa-solid fa-seedling me-2"></i> سیستم آبیاری حسام</span>
        <button class="btn btn-outline-light" id="menuBtn"><i class="fa-solid fa-bars fs-5"></i></button>
    </nav>

    <!-- Side Drawer Menu -->
    <div class="overlay" id="overlay"></div>
    <div class="side-menu" id="sideMenu">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h5 class="m-0">منوی کاربری</h5>
            <button class="btn btn-sm btn-close btn-close-white" id="closeMenu"></button>
        </div>
        <hr>
        <div class="mb-4">
            <h6><i class="fa-solid fa-key me-2"></i> تغییر رمز عبور</h6>
            <input type="password" id="oldPass" class="form-control form-control-sm mb-2" placeholder="رمز فعلی">
            <input type="password" id="newPass" class="form-control form-control-sm mb-2" placeholder="رمز جدید">
            <button class="btn btn-sm btn-warning w-100" onclick="changePassword()">ثبت تغییر رمز</button>
        </div>
        <hr>
        <a href="/logout" class="btn btn-danger w-100"><i class="fa-solid fa-right-from-bracket me-2"></i> خروج از حساب</a>
    </div>

    <div class="container mt-4">
        
        <!-- Accordion Section 1: Dashboard Status -->
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center" data-bs-toggle="collapse" data-bs-target="#secStatus">
                <span><i class="fa-solid fa-gauge-high text-primary me-2"></i> وضعیت لحظه‌ای سیستم</span>
                <i class="fa-solid fa-chevron-down"></i>
            </div>
            <div id="secStatus" class="collapse show card-body">
                <div class="row text-center">
                    <div class="col-md-3 col-6 mb-3">
                        <div class="p-3 bg-light rounded">
                            <i class="fa-solid fa-temperature-half fa-2x text-danger mb-2"></i>
                            <div class="text-muted small">دما</div>
                            <h4 id="lblTemp">-- °C</h4>
                        </div>
                    </div>
                    <div class="col-md-3 col-6 mb-3">
                        <div class="p-3 bg-light rounded">
                            <i class="fa-solid fa-droplet fa-2x text-info mb-2"></i>
                            <div class="text-muted small">رطوبت هوا</div>
                            <h4 id="lblHum">-- %</h4>
                        </div>
                    </div>
                    <div class="col-md-3 col-6 mb-3">
                        <div class="p-3 bg-light rounded">
                            <i class="fa-solid fa-water fa-2x text-primary mb-2"></i>
                            <div class="text-muted small">رطوبت خاک</div>
                            <h4 id="lblSoil">-- %</h4>
                        </div>
                    </div>
                    <div class="col-md-3 col-6 mb-3">
                        <div class="p-3 bg-light rounded">
                            <i class="fa-solid fa-toggle-on fa-2x text-success mb-2"></i>
                            <div class="text-muted small">وضعیت رله شیر</div>
                            <h4 id="lblValve">--</h4>
                        </div>
                    </div>
                </div>
                <div class="d-flex justify-content-center gap-2 mt-2">
                    <button class="btn btn-success px-4" onclick="sendCmd('VALVE_ON')"><i class="fa-solid fa-play me-1"></i> باز کردن رله</button>
                    <button class="btn btn-danger px-4" onclick="sendCmd('VALVE_OFF')"><i class="fa-solid fa-stop me-1"></i> بستن رله</button>
                    <button class="btn btn-secondary px-4" onclick="sendCmd('OPEN_DOOR')"><i class="fa-solid fa-door-open me-1"></i> درب‌بازکن</button>
                </div>
            </div>
        </div>

        <!-- Accordion Section 2: Device Hardware Diagnostics -->
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center" data-bs-toggle="collapse" data-bs-target="#secHardware">
                <span><i class="fa-solid fa-microchip text-warning me-2"></i> اطلاعات سخت‌افزاری و پردازنده (ESP32)</span>
                <i class="fa-solid fa-chevron-down"></i>
            </div>
            <div id="secHardware" class="collapse card-body">
                <div class="mb-3">
                    <div class="d-flex justify-content-between small mb-1">
                        <span>میزان درگیری پردازنده (CPU)</span>
                        <span id="lblCpu">0%</span>
                    </div>
                    <div class="progress"><div id="barCpu" class="progress-bar bg-warning" style="width: 0%"></div></div>
                </div>
                <div class="mb-3">
                    <div class="d-flex justify-content-between small mb-1">
                        <span>حافظه رم آزاد (SRAM)</span>
                        <span id="lblRam">0 KB</span>
                    </div>
                    <div class="progress"><div id="barRam" class="progress-bar bg-info" style="width: 0%"></div></div>
                </div>
                <div class="mb-3">
                    <div class="d-flex justify-content-between small mb-1">
                        <span>حافظه فلش استفاده شده (Flash)</span>
                        <span id="lblFlash">0 KB</span>
                    </div>
                    <div class="progress"><div id="barFlash" class="progress-bar bg-danger" style="width: 0%"></div></div>
                </div>
            </div>
        </div>

        <!-- Accordion Section 3: Timer Program Settings -->
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center" data-bs-toggle="collapse" data-bs-target="#secPrograms">
                <span><i class="fa-regular fa-clock text-success me-2"></i> تنظیم زمان‌بندی آبیاری (پروگرم)</span>
                <i class="fa-solid fa-chevron-down"></i>
            </div>
            <div id="secPrograms" class="collapse card-body">
                <div class="row g-3">
                    <div class="col-md-6">
                        <div class="border p-3 rounded">
                            <h6>برنامه شماره ۱</h6>
                            <div class="row g-2 mb-2">
                                <div class="col"><input type="number" id="p1_h" class="form-control" placeholder="ساعت (0-23)"></div>
                                <div class="col"><input type="number" id="p1_m" class="form-control" placeholder="دقیقه (0-59)"></div>
                                <div class="col"><input type="number" id="p1_d" class="form-control" placeholder="مدت (دقیقه)"></div>
                            </div>
                            <button class="btn btn-sm btn-outline-success w-100" onclick="saveProg(1)">ذخیره برنامه ۱</button>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="border p-3 rounded">
                            <h6>برنامه شماره ۲</h6>
                            <div class="row g-2 mb-2">
                                <div class="col"><input type="number" id="p2_h" class="form-control" placeholder="ساعت (0-23)"></div>
                                <div class="col"><input type="number" id="p2_m" class="form-control" placeholder="دقیقه (0-59)"></div>
                                <div class="col"><input type="number" id="p2_d" class="form-control" placeholder="مدت (دقیقه)"></div>
                            </div>
                            <button class="btn btn-sm btn-outline-success w-100" onclick="saveProg(2)">ذخیره برنامه ۲</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Accordion Section 4: Advanced Logs -->
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center" data-bs-toggle="collapse" data-bs-target="#secLogs">
                <span><i class="fa-solid fa-list-check text-info me-2"></i> آخرین گزارش‌های آبیاری (پیشرفته)</span>
                <i class="fa-solid fa-chevron-down"></i>
            </div>
            <div id="secLogs" class="collapse show card-body" id="logContainer">
                <div class="text-center text-muted py-3">داده‌ای یافت نشد.</div>
            </div>
        </div>

    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Side Menu Logic
        const menuBtn = document.getElementById('menuBtn');
        const sideMenu = document.getElementById('sideMenu');
        const overlay = document.getElementById('overlay');
        const closeMenu = document.getElementById('closeMenu');

        menuBtn.onclick = () => { sideMenu.classList.add('active'); overlay.classList.add('active'); };
        closeMenu.onclick = () => { sideMenu.classList.remove('active'); overlay.classList.remove('active'); };
        overlay.onclick = () => { sideMenu.classList.remove('active'); overlay.classList.remove('active'); };

        function sendCmd(cmd) {
            fetch('/api/send_cmd', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({cmd: cmd})
            }).then(r => r.json()).then(d => alert(d.message));
        }

        function saveProg(num) {
            let h = document.getElementById(`p${num}_h`).value;
            let m = document.getElementById(`p${num}_m`).value;
            let d = document.getElementById(`p${num}_d`).value;
            let cmd = `SET_PROG_${num}_${h}_${m}_${d}`;
            sendCmd(cmd);
        }

        function changePassword() {
            let oldPass = document.getElementById('oldPass').value;
            let newPass = document.getElementById('newPass').value;
            let formData = new FormData();
            formData.append('old_pass', oldPass);
            formData.append('new_pass', newPass);

            fetch('/api/change_password', { method: 'POST', body: formData })
            .then(r => r.json()).then(d => alert(d.message));
        }

        // Live Data Fetching
        setInterval(() => {
            fetch('/api/get_data').then(r => r.json()).then(res => {
                let d = res.data;
                document.getElementById('lblTemp').innerText = d.temp + ' °C';
                document.getElementById('lblHum').innerText = d.hum + ' %';
                document.getElementById('lblSoil').innerText = d.soil + ' %';
                document.getElementById('lblValve').innerText = d.valve;

                // Hardware Progress Bars
                document.getElementById('lblCpu').innerText = (d.cpu_usage || 12) + '%';
                document.getElementById('barCpu').style.width = (d.cpu_usage || 12) + '%';

                document.getElementById('lblRam').innerText = (d.ram_free || 180) + ' KB Free';
                document.getElementById('barRam').style.width = (((320 - (d.ram_free || 180))/320)*100) + '%';

                document.getElementById('lblFlash').innerText = (d.flash_used || 1200) + ' KB Used';
                document.getElementById('barFlash').style.width = (((d.flash_used || 1200)/4096)*100) + '%';

                // Logs Rendering
                let logHtml = '';
                res.logs.forEach(l => {
                    logHtml += `
                        <div class="log-card">
                            <div class="d-flex justify-content-between font-weight-bold">
                                <span>${l.event}</span>
                                <span class="badge bg-success">${l.status}</span>
                            </div>
                            <div class="small text-muted mt-2">
                                دما: ${l.temp}°C | رطوبت هوا: ${l.hum}% | رطوبت خاک: ${l.soil}%
                            </div>
                        </div>
                    `;
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
