import time
import socket
import threading
import requests
import sys
import os
import subprocess
from datetime import datetime

# ==================== КОНСТАНТЫ ====================
KOYEB_PORT = int(os.getenv("PORT", 8080))
DESKTOP_PORT = 6080
RESTART_HOURS = 2
RESTART_SECONDS = 7200  # 2 часа

# ==================== ЗАПУСК DOCKER DESKTOP ====================

def check_docker():
    """Проверяет установлен ли Docker"""
    try:
        result = subprocess.run(["docker", "--version"], 
                              capture_output=True, 
                              text=True)
        if result.returncode == 0:
            print("[✓] Docker установлен")
            return True
        else:
            print("[✗] Docker не установлен")
            return False
    except:
        print("[✗] Docker не установлен")
        return False

def install_docker():
    """Устанавливает Docker"""
    try:
        print("[Docker] Устанавливаю Docker...")
        
        # Установка Docker
        subprocess.run([
            "apt-get", "update", "-y"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        subprocess.run([
            "apt-get", "install", "-y",
            "docker.io",
            "docker-compose"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Запускаем Docker службу
        subprocess.run([
            "systemctl", "start", "docker"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        subprocess.run([
            "systemctl", "enable", "docker"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Добавляем текущего пользователя в группу docker
        subprocess.run([
            "usermod", "-aG", "docker", os.getlogin()
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        time.sleep(3)
        
        if check_docker():
            print("[✓] Docker успешно установлен")
            return True
        else:
            print("[✗] Ошибка установки Docker")
            return False
            
    except Exception as e:
        print(f"[Docker] Ошибка установки: {e}")
        return False

def start_docker_desktop():
    """Запускает Docker контейнер с Ubuntu Desktop"""
    try:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Запуск Ubuntu Desktop в Docker...")
        
        # Останавливаем старые контейнеры
        subprocess.run([
            "docker", "stop", "ubuntu-desktop"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        subprocess.run([
            "docker", "rm", "ubuntu-desktop"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        time.sleep(2)
        
        # Скачиваем образ
        print("[Docker] Скачиваю образ Ubuntu Desktop...")
        subprocess.run([
            "docker", "pull", "akarita/docker-ubuntu-desktop"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Запускаем контейнер
        print("[Docker] Запускаю контейнер...")
        docker_cmd = [
            "docker", "run", "-d",
            "--name", "ubuntu-desktop",
            "--platform", "linux/amd64",
            "-p", f"{DESKTOP_PORT}:6080",
            "-v", "/dev/shm:/dev/shm",
            "--shm-size=2g",
            "-e", "RESOLUTION=1280x720",
            "-e", "USER=ubuntu",
            "-e", "PASSWORD=ubuntu123",
            "-e", "VNC_PASSWORD=vnc123",
            "akarita/docker-ubuntu-desktop"
        ]
        
        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"[Docker] Ошибка запуска: {result.stderr}")
            return False
        
        # Ждем запуска
        time.sleep(10)
        
        # Проверяем запуск
        result = subprocess.run([
            "docker", "ps"
        ], capture_output=True, text=True)
        
        if "ubuntu-desktop" in result.stdout:
            print(f"[✓] Ubuntu Desktop запущен на порту {DESKTOP_PORT}")
            print(f"[✓] Веб-доступ: http://127.0.0.1:{DESKTOP_PORT}")
            print(f"[✓] Логин: ubuntu")
            print(f"[✓] Пароль: ubuntu123")
            print(f"[✓] VNC пароль: vnc123")
            return True
        else:
            print("[✗] Контейнер не запустился")
            return False
            
    except Exception as e:
        print(f"[Docker] Ошибка: {e}")
        return False

def start_ngrok():
    """Запускает ngrok для веб-доступа"""
    try:
        # Проверяем есть ли ngrok
        if not os.path.exists("./ngrok"):
            print("[!] Скачиваю ngrok...")
            subprocess.run([
                "wget", "-q",
                "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz",
                "-O", "ngrok.tgz"
            ], check=True)
            subprocess.run(["tar", "-xzf", "ngrok.tgz"], check=True)
            subprocess.run(["chmod", "+x", "ngrok"], check=True)
        
        # Останавливаем старый ngrok
        subprocess.run(["pkill", "-9", "ngrok"], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL)
        time.sleep(3)
        
        # Настраиваем токен
        ngrok_token = "36Nxsby4doMoAS00XhE1QFDTOoj_jWAC8i8QLdu4is6dmgRS"
        subprocess.run(
            f"./ngrok config add-authtoken {ngrok_token}",
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Запускаем туннель
        print("[Ngrok] Запуск туннеля для Ubuntu Desktop...")
        ngrok_cmd = f"./ngrok http {DESKTOP_PORT} --pooling-enabled"
        
        process = subprocess.Popen(
            ngrok_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            preexec_fn=os.setsid
        )
        
        # Читаем вывод для получения ссылки
        def read_output():
            ngrok_url = None
            for line in iter(process.stdout.readline, ''):
                print(f"[Ngrok] {line.strip()}")
                if "url=" in line and "ngrok-free.app" in line:
                    ngrok_url = line.split("url=")[1].strip()
                    print(f"\n{'='*60}")
                    print(f"🔥 Ubuntu Desktop доступен по ссылке:")
                    print(f"🌐 {ngrok_url}")
                    print(f"👤 Логин: ubuntu")
                    print(f"🔑 Пароль: ubuntu123")
                    print(f"{'='*60}\n")
                elif "Forwarding" in line:
                    parts = line.strip().split("->")
                    if len(parts) >= 2:
                        ngrok_url = parts[1].strip()
                        print(f"\n{'='*60}")
                        print(f"🔥 Ubuntu Desktop доступен по ссылке:")
                        print(f"🌐 {ngrok_url}")
                        print(f"👤 Логин: ubuntu")
                        print(f"🔑 Пароль: ubuntu123")
                        print(f"{'='*60}\n")
        
        threading.Thread(target=read_output, daemon=True).start()
        
        time.sleep(5)
        print("[✓] Ngrok запущен")
        return True
        
    except Exception as e:
        print(f"[Ngrok] Ошибка: {e}")
        return False

def setup_cardinal_in_docker():
    """Устанавливает Cardinal Bot внутри Docker контейнера"""
    try:
        print("[Cardinal] Устанавливаю Cardinal Bot в контейнер...")
        
        # Копируем файлы Cardinal в контейнер
        cardinal_cmds = [
            # Устанавливаем Python и зависимости
            "docker exec -it ubuntu-desktop bash -c 'apt-get update && apt-get install -y python3 python3-pip git curl wget'",
            
            # Создаем директорию
            "docker exec -it ubuntu-desktop bash -c 'mkdir -p /home/ubuntu/cardinal'",
            
            # Копируем файлы (если они есть локально)
            f"docker cp . ubuntu-desktop:/home/ubuntu/cardinal/ 2>/dev/null || true",
            
            # Создаем ярлык на рабочем столе
            """docker exec -it ubuntu-desktop bash -c 'echo "[Desktop Entry]
Name=Cardinal Bot
Comment=FunPay Cardinal Bot
Exec=/usr/bin/gnome-terminal -- python3 /home/ubuntu/cardinal/cardinal.py
Icon=application-x-executable
Terminal=true
Type=Application" > /home/ubuntu/Desktop/Cardinal_Bot.desktop'""",
            
            # Даем права
            "docker exec -it ubuntu-desktop bash -c 'chmod +x /home/ubuntu/Desktop/*.desktop'"
        ]
        
        for cmd in cardinal_cmds:
            subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        print("[✓] Cardinal Bot установлен в контейнер")
        return True
        
    except Exception as e:
        print(f"[Cardinal] Ошибка установки: {e}")
        return False

def restart_services():
    """Перезапускает сервисы"""
    current_time = datetime.now().strftime("%H:%M:%S")
    print(f"\n[{current_time}] Перезапуск сервисов...")
    
    # Останавливаем всё
    subprocess.run([
        "docker", "stop", "ubuntu-desktop"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    subprocess.run(["pkill", "-9", "ngrok"], 
                  stdout=subprocess.DEVNULL, 
                  stderr=subprocess.DEVNULL)
    
    time.sleep(3)
    
    # Запускаем
    if start_docker_desktop():
        time.sleep(5)
        setup_cardinal_in_docker()
        time.sleep(2)
        start_ngrok()

def watchdog():
    """Перезапускает каждые 2 часа"""
    print(f"[Watchdog] Запущен (перезапуск каждые {RESTART_HOURS} часа)")
    
    # Первый запуск
    restart_services()
    
    while True:
        # Ждем 2 часа
        print(f"[Watchdog] Следующий перезапуск через {RESTART_HOURS} часа...")
        time.sleep(RESTART_SECONDS)
        
        # Перезапускаем
        restart_services()

# ==================== HTTP СЕРВЕР ====================

def create_http_server(port):
    """Создает HTTP сервер с информацией"""
    def server_thread():
        while True:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(('0.0.0.0', port))
                sock.listen(10)
                sock.settimeout(1)
                
                print(f"[Server] Запущен на порту {port}")
                
                while True:
                    try:
                        client, addr = sock.accept()
                        request = client.recv(1024).decode()
                        
                        # Простой парсинг запроса
                        if "GET / " in request or "GET /index" in request:
                            # Получаем ngrok URL
                            ngrok_url = "Обновляется..."
                            try:
                                result = subprocess.run([
                                    "curl", "-s", "http://127.0.0.1:4040/api/tunnels"
                                ], capture_output=True, text=True)
                                if result.returncode == 0:
                                    import json
                                    data = json.loads(result.stdout)
                                    if data['tunnels']:
                                        ngrok_url = data['tunnels'][0]['public_url']
                            except:
                                pass
                            
                            response = f"""HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8

<!DOCTYPE html>
<html>
<head>
    <title>FunPay Cardinal Bot - Ubuntu Desktop</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: rgba(255, 255, 255, 0.95);
            padding: 30px;
            border-radius: 15px 15px 0 0;
            text-align: center;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }}
        .content {{
            background: rgba(255, 255, 255, 0.9);
            padding: 40px;
            border-radius: 0 0 15px 15px;
            margin-top: 20px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #764ba2;
            margin: 0;
            font-size: 2.5em;
        }}
        h2 {{
            color: #667eea;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        .card {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            margin: 20px 0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-left: 5px solid #667eea;
        }}
        .btn {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 30px;
            text-decoration: none;
            border-radius: 50px;
            font-weight: bold;
            margin: 10px 5px;
            transition: transform 0.3s, box-shadow 0.3s;
            border: none;
            cursor: pointer;
            font-size: 16px;
        }}
        .btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        }}
        .url-box {{
            background: #f8f9fa;
            border: 2px dashed #667eea;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            word-break: break-all;
            font-family: monospace;
            font-size: 18px;
            text-align: center;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .info-item {{
            background: #f0f4ff;
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid #764ba2;
        }}
        .status {{
            padding: 10px 20px;
            border-radius: 20px;
            display: inline-block;
            font-weight: bold;
            margin: 5px;
        }}
        .status-online {{
            background: #d4edda;
            color: #155724;
        }}
        .instructions {{
            background: #e7f3ff;
            padding: 25px;
            border-radius: 10px;
            margin: 25px 0;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            color: white;
            opacity: 0.8;
            font-size: 14px;
        }}
        .desktop-preview {{
            text-align: center;
            margin: 30px 0;
        }}
        .desktop-preview img {{
            max-width: 100%;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 FunPay Cardinal Bot</h1>
            <p style="color: #666; font-size: 1.2em;">Удаленный Ubuntu Desktop с Cardinal Bot</p>
            <div style="margin: 20px 0;">
                <span class="status status-online">● ОНЛАЙН</span>
                <span style="color: #666;"> | Время: {datetime.now().strftime('%H:%M:%S')}</span>
            </div>
        </div>
        
        <div class="content">
            <h2>🌐 Веб-доступ к Ubuntu Desktop</h2>
            
            <div class="card">
                <h3>Ссылка для входа:</h3>
                <div class="url-box">
                    <strong id="ngrokUrl">{ngrok_url if ngrok_url != "Обновляется..." else "Загрузка..."}</strong>
                </div>
                
                <div style="text-align: center; margin: 25px 0;">
                    <button class="btn" onclick="window.open('{ngrok_url}', '_blank')" id="openBtn" {'disabled' if ngrok_url == 'Обновляется...' else ''}>
                        🔗 Открыть Ubuntu Desktop
                    </button>
                    <button class="btn" onclick="copyUrl()" style="background: #28a745;">
                        📋 Копировать ссылку
                    </button>
                </div>
                
                <p style="text-align: center; color: #666;">
                    ⚡ Автоперезапуск каждые {RESTART_HOURS} часа
                </p>
            </div>
            
            <div class="info-grid">
                <div class="info-item">
                    <h3>👤 Данные для входа</h3>
                    <p><strong>Логин:</strong> <code>ubuntu</code></p>
                    <p><strong>Пароль:</strong> <code>ubuntu123</code></p>
                    <p><strong>VNC пароль:</strong> <code>vnc123</code></p>
                </div>
                
                <div class="info-item">
                    <h3>🖥️ Система</h3>
                    <p><strong>ОС:</strong> Ubuntu Desktop</p>
                    <p><strong>Интерфейс:</strong> XFCE</p>
                    <p><strong>Порт:</strong> {DESKTOP_PORT}</p>
                </div>
                
                <div class="info-item">
                    <h3>🤖 Cardinal Bot</h3>
                    <p><strong>Статус:</strong> Установлен</p>
                    <p><strong>Расположение:</strong> /home/ubuntu/cardinal</p>
                    <p><strong>Запуск:</strong> Ярлык на рабочем столе</p>
                </div>
            </div>
            
            <div class="instructions">
                <h3>📋 Инструкция по использованию:</h3>
                <ol>
                    <li>Нажмите "Открыть Ubuntu Desktop" или перейдите по ссылке выше</li>
                    <li>Введите логин <code>ubuntu</code> и пароль <code>ubuntu123</code></li>
                    <li>На рабочем столе найдите ярлык "Cardinal Bot"</li>
                    <li>Запустите Cardinal Bot двойным кликом по ярлыку</li>
                    <li>Работайте с ботом прямо в браузере!</li>
                </ol>
            </div>
            
            <div class="desktop-preview">
                <h3>🖼️ Предпросмотр рабочего стола:</h3>
                <div style="background: #2c3e50; color: white; padding: 40px; border-radius: 10px; font-family: monospace;">
                    <div style="text-align: left; max-width: 600px; margin: 0 auto;">
                        <div style="background: #34495e; padding: 10px; border-radius: 5px;">
                            <span style="color: #e74c3c;">●</span>
                            <span style="color: #f1c40f;">●</span>
                            <span style="color: #2ecc71;">●</span>
                            <span style="float: right;">Ubuntu Desktop</span>
                        </div>
                        <div style="padding: 20px;">
                            <p>> Cardinal Bot Desktop Environment</p>
                            <p>> Status: <span style="color: #2ecc71;">ONLINE</span></p>
                            <p>> Web Access: {ngrok_url}</p>
                            <p>> Auto-restart: every {RESTART_HOURS} hours</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>© 2024 FunPay Cardinal Bot | Ubuntu Desktop Web Interface</p>
            <p>System v1.0 | Auto-refresh: 60s</p>
        </div>
    </div>
    
    <script>
        function copyUrl() {{
            const url = document.getElementById('ngrokUrl').textContent;
            navigator.clipboard.writeText(url).then(() => {{
                alert('Ссылка скопирована в буфер обмена!');
            }});
        }}
        
        // Автообновление страницы каждую минуту
        setTimeout(() => {{
            location.reload();
        }}, 60000);
        
        // Попытка получить ссылку если еще не загружена
        if (document.getElementById('ngrokUrl').textContent === 'Загрузка...') {{
            setTimeout(() => {{
                fetch('/status')
                    .then(r => r.json())
                    .then(data => {{
                        if (data.url) {{
                            document.getElementById('ngrokUrl').textContent = data.url;
                            document.getElementById('openBtn').onclick = () => window.open(data.url, '_blank');
                            document.getElementById('openBtn').disabled = false;
                        }}
                    }});
            }}, 3000);
        }}
    </script>
</body>
</html>"""
                        elif "GET /status" in request:
                            # API для получения статуса
                            ngrok_url = None
                            try:
                                result = subprocess.run([
                                    "curl", "-s", "http://127.0.0.1:4040/api/tunnels"
                                ], capture_output=True, text=True)
                                if result.returncode == 0:
                                    import json
                                    data = json.loads(result.stdout)
                                    if data['tunnels']:
                                        ngrok_url = data['tunnels'][0]['public_url']
                            except:
                                pass
                            
                            response = f"""HTTP/1.1 200 OK
Content-Type: application/json

{{"status": "online", "url": "{ngrok_url if ngrok_url else ''}", "time": "{datetime.now().strftime('%H:%M:%S')}"}}"""
                        else:
                            response = "HTTP/1.1 404 Not Found\n\nNot Found"
                        
                        client.send(response.encode())
                        client.close()
                        
                    except socket.timeout:
                        continue
                    except Exception as e:
                        print(f"[Server] Ошибка обработки: {e}")
                        break
                        
            except Exception as e:
                print(f"[Server] Ошибка: {e}")
                time.sleep(2)
    
    thread = threading.Thread(target=server_thread, daemon=True)
    thread.start()

def setup_pings():
    """Пинги для поддержания активности"""
    def pinger():
        time.sleep(30)
        counter = 0
        
        while True:
            try:
                counter += 1
                current_time = datetime.now().strftime("%H:%M:%S")
                
                try:
                    requests.get("https://www.google.com", timeout=10)
                    if counter % 10 == 0:
                        print(f"[{current_time}] Пинг #{counter}: OK")
                except:
                    if counter % 10 == 0:
                        print(f"[{current_time}] Пинг #{counter}: Ошибка")
                
                time.sleep(240)
                
            except Exception as e:
                print(f"[Pinger] Ошибка: {e}")
                time.sleep(60)
    
    threading.Thread(target=pinger, daemon=True).start()
    print("[Pinger] Запущен")

# ==================== ИНИЦИАЛИЗАЦИЯ ====================

def initialize():
    """Инициализация системы"""
    print("=" * 60)
    print("🚀 FunPay Cardinal Bot - Ubuntu Desktop Web Interface")
    print("=" * 60)
    print(f"📊 Бот порт: {KOYEB_PORT}")
    print(f"🖥️  Desktop порт: {DESKTOP_PORT}")
    print(f"🔄 Перезапуск: каждые {RESTART_HOURS} часа")
    print(f"⏰ Время запуска: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)
    
    # Проверяем Docker
    if not check_docker():
        if not install_docker():
            print("[!] Критическая ошибка: Docker не установлен")
            return
    
    # Запускаем сервер
    create_http_server(KOYEB_PORT)
    
    # Запускаем пинги
    setup_pings()
    
    # Запускаем watchdog
    threading.Thread(target=watchdog, daemon=True).start()
    
    print("[System] Система запущена")

# ==================== ЗАПУСК СИСТЕМЫ ====================

# Инициализируем
initialize()
time.sleep(3)

print(f"\n{'='*60}")
print("✅ СИСТЕМА ЗАПУЩЕНА!")
print(f"{'='*60}")
print(f"🌐 Веб-интерфейс доступен по порту: {KOYEB_PORT}")
print(f"🖥️  Ubuntu Desktop будет доступен по ссылке ngrok")
print(f"👤 Логин: ubuntu | Пароль: ubuntu123")
print(f"🤖 Cardinal Bot установлен в контейнер")
print(f"🔄 Автоперезапуск каждые {RESTART_HOURS} часа")
print(f"{'='*60}")
print("📢 Ссылка ngrok появится выше в логах")
print(f"{'='*60}")

# ==================== ОРИГИНАЛЬНЫЙ КОД CARDINAL ====================
# Оригинальный код Cardinal будет работать на отдельном порту
# или внутри Docker контейнера

import Utils.cardinal_tools
import Utils.config_loader as cfg_loader
from first_setup import first_setup
from colorama import Fore, Style
from Utils.logger import LOGGER_CONFIG
import logging.config
import colorama
import sys
import os
from cardinal import Cardinal
import Utils.exceptions as excs
from locales.localizer import Localizer

VERSION = "0.1.16.9"

Utils.cardinal_tools.set_console_title(f"FunPay Cardinal v{VERSION}")

if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))
else:
    os.chdir(os.path.dirname(__file__))

folders = ["configs", "logs", "storage", "storage/cache", "storage/plugins", "storage/products", "plugins"]
for i in folders:
    if not os.path.exists(i):
        os.makedirs(i)

files = ["configs/auto_delivery.cfg", "configs/auto_response.cfg"]
for i in files:
    if not os.path.exists(i):
        with open(i, "w", encoding="utf-8") as f:
            ...

colorama.init()

logging.config.dictConfig(LOGGER_CONFIG)
logging.raiseExceptions = False
logger = logging.getLogger("main")
logger.debug("------------------------------------------------------------------")

print(f"{Fore.RED}{Style.BRIGHT}v{VERSION}{Style.RESET_ALL}\n")
print(f"{Fore.MAGENTA}{Style.BRIGHT}By {Fore.BLUE}{Style.BRIGHT}Woopertail, @sidor0912{Style.RESET_ALL}")
print(f"{Fore.MAGENTA}{Style.BRIGHT} * GitHub: {Fore.BLUE}{Style.BRIGHT}github.com/sidor0912/FunPayCardinal{Style.RESET_ALL}")
print(f"{Fore.MAGENTA}{Style.BRIGHT} * Telegram: {Fore.BLUE}{Style.BRIGHT}t.me/sidor0912")
print(f"{Fore.MAGENTA}{Style.BRIGHT} * Новости о обновлениях: {Fore.BLUE}{Style.BRIGHT}t.me/fpc_updates")
print(f"{Fore.MAGENTA}{Style.BRIGHT} * Плагины: {Fore.BLUE}{Style.BRIGHT}t.me/fpc_plugins")
print(f"{Fore.MAGENTA}{Style.BRIGHT} * Донат: {Fore.BLUE}{Style.BRIGHT}t.me/sidor_donate")
print(f"{Fore.MAGENTA}{Style.BRIGHT} * Telegram-чат: {Fore.BLUE}{Style.BRIGHT}t.me/funpay_cardinal")

if not os.path.exists("configs/_main.cfg"):
    first_setup()
    sys.exit()

if sys.platform == "linux" and os.getenv('FPC_IS_RUNNIG_AS_SERVICE', '0') == '1':
    import getpass

    pid = str(os.getpid())
    pidFile = open(f"/run/FunPayCardinal/{getpass.getuser()}/FunPayCardinal.pid", "w")
    pidFile.write(pid)
    pidFile.close()

    logger.info(f"$GREENPID файл создан, PID процесса: {pid}")

directory = 'plugins'
for filename in os.listdir(directory):
    if filename.endswith(".py"):
        filepath = os.path.join(directory, filename)
        with open(filepath, 'r', encoding='utf-8') as file:
            data = file.read()
        if '"<i>Разработчик:</i> " + CREDITS' in data or " lot.stars " in data or " lot.seller " in data:
            data = data.replace('"<i>Разработчик:</i> " + CREDITS', '"sidor0912"') \
                .replace(" lot.stars ", " lot.seller.stars ") \
                .replace(" lot.seller ", " lot.seller.username ")
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(data)

try:
    logger.info("$MAGENTAЗагружаю конфиг _main.cfg...")
    MAIN_CFG = cfg_loader.load_main_config("configs/_main.cfg")
    localizer = Localizer(MAIN_CFG["Other"]["language"])
    _ = localizer.translate

    logger.info("$MAGENTAЗагружаю конфиг auto_response.cfg...")
    AR_CFG = cfg_loader.load_auto_response_config("configs/auto_response.cfg")
    RAW_AR_CFG = cfg_loader.load_raw_auto_response_config("configs/auto_response.cfg")

    logger.info("$MAGENTAЗагружаю конфиг auto_delivery.cfg...")
    AD_CFG = cfg_loader.load_auto_delivery_config("configs/auto_delivery.cfg")
except excs.ConfigParseError as e:
    logger.error(e)
    logger.error("Завершаю программу...")
    time.sleep(5)
    sys.exit()
except UnicodeDecodeError:
    logger.error("Произошла ошибка при расшифровке UTF-8. Убедитесь, что кодировка файла = UTF-8, "
                 "а формат конца строк = LF.")
    logger.error("Завершаю программу...")
    time.sleep(5)
    sys.exit()
except:
    logger.critical("Произошла непредвиденная ошибка.")
    logger.warning("TRACEBACK", exc_info=True)
    logger.error("Завершаю программу...")
    time.sleep(5)
    sys.exit()

localizer = Localizer(MAIN_CFG["Other"]["language"])

try:
    Cardinal(MAIN_CFG, AD_CFG, AR_CFG, RAW_AR_CFG, VERSION).init().run()
except KeyboardInterrupt:
    logger.info("Завершаю программу...")
    sys.exit()
except:
    logger.critical("При работе Кардинала произошла необработанная ошибка.")
    logger.warning("TRACEBACK", exc_info=True)
    logger.critical("Завершаю программу...")
    time.sleep(5)
    sys.exit()
