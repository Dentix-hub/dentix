import os
import sys
import threading
import time
import webview
import uvicorn
import socket
import logging

# ==========================================
# 0. Global Setup & Encoding Fix
# ==========================================
os.environ["PYTHONIOENCODING"] = "utf-8"

APP_DATA_DIR = os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "DentixOffline")
os.makedirs(APP_DATA_DIR, exist_ok=True)
LOG_FILE = os.path.join(APP_DATA_DIR, "app_debug.log")

# Redirect ALL stdout/stderr to the log file with UTF-8 encoding
# This captures uvicorn logs, print statements, and crashes.
sys.stdout = open(LOG_FILE, 'a', encoding='utf-8', buffering=1)
sys.stderr = open(LOG_FILE, 'a', encoding='utf-8', buffering=1)

def log(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    sys.stdout.write(f"{timestamp} - INFO - {msg}\n")
    sys.stdout.flush()

log("--- Starting DENTIX Desktop App (Redirected Stream Mode) ---")

# ==========================================
# 1. License Check Setup
# ==========================================
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backend.core.license import is_license_valid, save_license, get_machine_id

# ==========================================
# 2. Environment Override
# ==========================================
LOCAL_DB_URL = f"sqlite:///{os.path.join(APP_DATA_DIR, 'dentix_local.db')}"
os.environ["DATABASE_URL"] = LOCAL_DB_URL
os.environ["DEPLOYMENT_MODE"] = "offline"
os.environ["ENVIRONMENT"] = "desktop"
os.environ.setdefault("SECRET_KEY", "desktop_offline_secret_key_v1_secure_dentix")

# ==========================================
# 3. Simple Offline-Only UI
# ==========================================
LICENSE_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>تفعيل DENTIX</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #f0f2f5; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; color: #333; }
        .container { background: white; width: 420px; padding: 30px; border-radius: 16px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); text-align: center; }
        .logo { font-size: 28px; font-weight: 800; color: #2563eb; margin-bottom: 10px; letter-spacing: 1px; }
        h2 { font-size: 20px; margin: 10px 0; color: #1e293b; }
        p { font-size: 14px; color: #64748b; line-height: 1.6; margin-bottom: 25px; }
        .hwid-box { background: #f8fafc; border: 2px dashed #cbd5e1; padding: 15px; border-radius: 10px; font-family: monospace; font-size: 15px; color: #334155; cursor: pointer; position: relative; transition: all 0.2s; margin-bottom: 20px; word-break: break-all; }
        .hwid-box:hover { border-color: #3b82f6; background: #eff6ff; }
        .hwid-box::after { content: 'اضغط للنسخ'; position: absolute; bottom: -20px; left: 50%; transform: translateX(-50%); font-size: 11px; color: #94a3b8; font-family: 'Segoe UI'; }
        input { width: 100%; box-sizing: border-box; padding: 14px; border: 2px solid #e2e8f0; border-radius: 10px; font-size: 16px; text-align: center; margin-top: 10px; transition: border-color 0.2s; outline: none; }
        input:focus { border-color: #3b82f6; }
        button { background: #2563eb; color: white; border: none; width: 100%; padding: 14px; border-radius: 10px; font-size: 16px; font-weight: 600; cursor: pointer; margin-top: 20px; transition: all 0.2s; }
        button:hover { background: #1d4ed8; transform: translateY(-1px); }
        button:disabled { background: #94a3b8; cursor: not-allowed; transform: none; }
        .error { color: #dc2626; font-size: 13px; font-weight: 600; margin-top: 12px; display: none; }
        .success { color: #059669; font-size: 13px; font-weight: 600; margin-top: 12px; display: none; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">DENTIX</div>
        <h2>تفعيل النسخة الأوفلاين</h2>
        <p>يرجى نسخ رمز الجهاز أدناه وإرساله للمطور للحصول على مفتاح التفعيل الخاص بك.</p>
        <div class="hwid-box" id="hwidBox" onclick="copyHwid()">{{HWID}}</div>
        <input type="text" id="keyInput" placeholder="أدخل مفتاح التفعيل هنا..." spellcheck="false">
        <button id="submitBtn" onclick="handleActivate()">تفعيل البرنامج</button>
        <div id="errorMsg" class="error">مفتاح التفعيل غير صحيح، يرجى التأكد منه.</div>
        <div id="successMsg" class="success">تم التفعيل بنجاح! سيفتح البرنامج الآن...</div>
    </div>
    <script>
        function copyHwid() {
            const el = document.getElementById('hwidBox');
            const text = el.innerText;
            const textArea = document.createElement("textarea");
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            const originalText = text;
            el.innerText = 'تم النسخ!';
            setTimeout(() => { el.innerText = originalText; }, 1000);
        }
        async function handleActivate() {
            const key = document.getElementById('keyInput').value.trim();
            const btn = document.getElementById('submitBtn');
            const error = document.getElementById('errorMsg');
            const success = document.getElementById('successMsg');
            if (!key) return;
            btn.disabled = true;
            btn.innerText = 'جاري التحقق...';
            error.style.display = 'none';
            try {
                if (!window.pywebview || !window.pywebview.api) { await new Promise(r => setTimeout(r, 500)); }
                const result = await window.pywebview.api.activate(key);
                if (result === true) {
                    success.style.display = 'block';
                    btn.innerText = 'تم التفعيل';
                } else if (result === false) {
                    error.style.display = 'block';
                    btn.disabled = false;
                    btn.innerText = 'تفعيل البرنامج';
                } else {
                    alert('خطأ: ' + result);
                    btn.disabled = false;
                    btn.innerText = 'تفعيل البرنامج';
                }
            } catch (e) {
                alert('فشل التفعيل: ' + e);
                btn.disabled = false;
                btn.innerText = 'تفعيل البرنامج';
            }
        }
    </script>
</body>
</html>
"""

class LicenseApi:
    def __init__(self):
        self.window = None
    def activate(self, key):
        log(f"API CALL: activate")
        try:
            is_ok = save_license(key)
            if is_ok:
                log("Success! Closing window.")
                threading.Timer(1.5, self.window.destroy).start()
                return True
            return False
        except Exception as e:
            log(f"API ERROR: {str(e)}")
            return str(e)

# ==========================================
# 4. Server Management
# ==========================================
PORT = 8000
HOST = "127.0.0.1"

def get_free_port(default_port=8000):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((HOST, default_port))
            return default_port
        except OSError:
            s.bind((HOST, 0))
            return s.getsockname()[1]

def run_server(port):
    log(f"Server Thread: Starting on port {port}")
    try:
        from backend.main import app
        uvicorn.run(app, host=HOST, port=port, log_level="info", access_log=True)
    except Exception as e:
        import traceback
        log(f"CRITICAL: Server crashed: {str(e)}")
        log(f"TRACEBACK:\n{traceback.format_exc()}")

def main():
    try:
        if not is_license_valid():
            log("State: License required")
            api = LicenseApi()
            hwid = get_machine_id()
            html = LICENSE_HTML.replace("{{HWID}}", hwid)
            window = webview.create_window("تفعيل DENTIX Offline", html=html, width=500, height=600, resizable=False, js_api=api)
            api.window = window
            webview.start(private_mode=False)
            if not is_license_valid():
                log("State: Not activated, exiting.")
                sys.exit(0)

        log("State: License verified. Initializing...")
        port = get_free_port(PORT)
        url = f"http://{HOST}:{port}"
        
        threading.Thread(target=run_server, args=(port,), daemon=True).start()
        
        # Increased wait time to ensure uvicorn is fully up
        log("Waiting for server to stabilize...")
        time.sleep(5) 

        log(f"Opening main window: {url}")
        webview.create_window("DENTIX Smart Clinic", url, width=1280, height=800, min_size=(1024, 768))
        webview.start(private_mode=False)
    except Exception as e:
        log(f"FATAL SYSTEM ERROR: {str(e)}")

if __name__ == "__main__":
    main()
