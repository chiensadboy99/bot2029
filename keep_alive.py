from flask import Flask
from threading import Thread
import time

app = Flask('')

@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Bot MD5 Tool - Đang hoạt động</title>
        <meta charset="UTF-8">
        <style>
            body {
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 50px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .container {
                background: rgba(255,255,255,0.1);
                border-radius: 20px;
                padding: 30px;
                backdrop-filter: blur(10px);
            }
            h1 { font-size: 3em; margin-bottom: 20px; }
            .status { color: #4ade80; font-weight: bold; }
            .time { font-size: 1.2em; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 MD5 Tool Bot</h1>
            <p>Trạng thái: <span class="status">✅ ĐANG HOẠT ĐỘNG</span></p>
            <p>Bot Telegram đang chạy và sẵn sàng phục vụ!</p>
            <div class="time">
                📅 Thời gian hiện tại: <span id="datetime"></span>
            </div>
            <hr>
            <small>Powered by NguyenTung2029 | Railway</small>
        </div>
        <script>
            function updateDateTime() {
                const now = new Date();
                document.getElementById('datetime').innerHTML = now.toLocaleString('vi-VN');
            }
            updateDateTime();
            setInterval(updateDateTime, 1000);
        </script>
    </body>
    </html>
    """

@app.route('/health')
def health():
    return {"status": "healthy", "timestamp": time.time()}

def run():
    """Chạy Flask server trên port 8080"""
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)

def keep_alive():
    """Khởi chạy Flask server trong một thread riêng"""
    t = Thread(target=run)
    t.daemon = True  # Thread sẽ tắt khi main program tắt
    t.start()
    print("✅ Flask server đã khởi động trên port 8080")