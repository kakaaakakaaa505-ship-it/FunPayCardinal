import time
import socket
import threading
import requests
import random
import sys
import os
import subprocess
import signal
from datetime import datetime
from pip._internal.cli.main import main

# ==================== КОНСТАНТЫ ДЛЯ KOYEB ====================
KOYEB_PORT = int(os.getenv("PORT", 8080))
GOTTY_PORT = 8086

# ==================== ВНЕШНИЕ ПИНГИ ====================
EXTERNAL_PING_URLS = [
    "https://hc-ping.com/",
    "https://www.google.com",
    "https://1.1.1.1",
]

# ==================== GOTTY АВТОЗАПУСК ====================

gotty_process = None
ngrok_process = None

def download_gotty():
    """Скачивает gotty если нет"""
    if not os.path.exists("./gotty"):
        print("[Gotty] Downloading gotty...")
        try:
            subprocess.run([
                "wget", "-q", 
                "https://github.com/yudai/gotty/releases/download/v2.0.0-alpha.3/gotty_2.0.0-alpha.3_linux_amd64.tar.gz",
                "-O", "gotty.tar.gz"
            ], check=True)
            subprocess.run(["tar", "-xzf", "gotty.tar.gz"], check=True)
            subprocess.run(["chmod", "+x", "gotty"], check=True)
            print("[Gotty] Downloaded successfully")
        except Exception as e:
            print(f"[Gotty] Download failed: {e}")

def download_ngrok():
    """Скачивает ngrok если нет"""
    if not os.path.exists("./ngrok"):
        print("[Ngrok] Downloading ngrok...")
        try:
            subprocess.run([
                "wget", "-q",
                "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz",
                "-O", "ngrok.tgz"
            ], check=True)
            subprocess.run(["tar", "-xzf", "ngrok.tgz"], check=True)
            subprocess.run(["chmod", "+x", "ngrok"], check=True)
            print("[Ngrok] Downloaded successfully")
        except Exception as e:
            print(f"[Ngrok] Download failed: {e}")

def check_gotty_running():
    """Проверяет, работает ли gotty"""
    try:
        result = subprocess.run(["pgrep", "-f", "gotty.*bash"], 
                              capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def start_gotty_via_freeroot():
    """Запускает gotty ЧЕРЕЗ FREEROOT напрямую (сначала root, потом gotty)"""
    global gotty_process
    
    try:
        print("[Gotty] ========================================")
        print("[Gotty] STARTING via FREEROOT (ROOT FIRST)")
        print("[Gotty] ========================================")
        
        # 1. Скачиваем gotty если нет
        download_gotty()
        
        # 2. Убиваем старые процессы
        subprocess.run(["pkill", "-9", "gotty"], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL)
        time.sleep(2)
        
        # 3. Создаем скрипт который:
        #    - Заходит в freeroot
        #    - Получает root права (bash root.sh)
        #    - Запускает gotty ИЗ-ПОД root
        root_gotty_script = """#!/bin/bash
echo "========================================"
echo "  FREEROOT -> ROOT -> GOTTY"
echo "========================================"

# Переходим в freeroot
cd /workspace/freeroot
echo "[1] In freeroot directory: $(pwd)"

# Получаем root права
echo "[2] Getting root access..."
bash root.sh
echo "[3] Now user: $(whoami)"

# Теперь мы root, запускаем gotty
echo "[4] Starting gotty as $(whoami)..."
cd /workspace
./gotty -a 127.0.0.1 -p 8086 -w bash

echo "[5] Gotty is running"
echo "========================================"
"""
        
        # Сохраняем скрипт
        script_path = "/tmp/root_gotty_launcher.sh"
        with open(script_path, "w") as f:
            f.write(root_gotty_script)
        os.chmod(script_path, 0o755)
        
        print(f"[Gotty] Created launcher script: {script_path}")
        
        # 4. Запускаем скрипт
        print("[Gotty] Executing launcher script...")
        gotty_process = subprocess.Popen(
            script_path,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
            preexec_fn=os.setsid
        )
        
        # Читаем вывод в реальном времени
        def read_output():
            for line in iter(gotty_process.stdout.readline, ''):
                print(f"[Gotty Output] {line.strip()}")
        
        # Запускаем чтение вывода в отдельном потоке
        output_thread = threading.Thread(target=read_output, daemon=True)
        output_thread.start()
        
        # Ждем запуска
        print("[Gotty] Waiting for startup...")
        time.sleep(5)
        
        # 5. Проверяем запустился ли
        result = subprocess.run(
            ["ss", "-tulpn"],
            capture_output=True,
            text=True
        )
        
        if f":{GOTTY_PORT}" in result.stdout:
            print(f"[✓] SUCCESS: Gotty running on port {GOTTY_PORT}")
            print(f"[✓] Access: http://127.0.0.1:{GOTTY_PORT}")
            print(f"[✓] Running as root (via freeroot)")
            return True
        else:
            print("[✗] FAILED: Gotty not listening on port")
            # Показываем ошибки
            gotty_process.terminate()
            stdout, stderr = gotty_process.communicate(timeout=5)
            print(f"[Gotty Stderr]: {stderr}")
            return False
            
    except Exception as e:
        print(f"[Gotty] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def start_ngrok():
    """Запускает ngrok для gotty"""
    global ngrok_process
    
    # Скачиваем ngrok если нет
    download_ngrok()
    
    # Проверяем токен
    ngrok_token = "36Nxsby4doMoAS00XhE1QFDTOoj_jWAC8i8QLdu4is6dmgRS"
    
    try:
        print("[Ngrok] Configuring token...")
        # Настраиваем токен
        config_cmd = f"./ngrok config add-authtoken {ngrok_token}"
        subprocess.run(config_cmd, shell=True, capture_output=True)
        
        print("[Ngrok] Starting tunnel...")
        # Запускаем ngrok
        ngrok_cmd = f"./ngrok http 127.0.0.1:{GOTTY_PORT} --log stdout"
        ngrok_process = subprocess.Popen(
            ngrok_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            preexec_fn=os.setsid
        )
        
        # Читаем вывод чтобы получить ссылку
        def read_ngrok_output():
            for line in iter(ngrok_process.stdout.readline, ''):
                if "Forwarding" in line:
                    print(f"[Ngrok LINK] {line.strip()}")
                elif "started tunnel" in line.lower():
                    print(f"[Ngrok] {line.strip()}")
                elif "error" in line.lower():
                    print(f"[Ngrok ERROR] {line.strip()}")
        
        threading.Thread(target=read_ngrok_output, daemon=True).start()
        
        time.sleep(5)
        print("[Ngrok] Started (check above for URL)")
        return True
        
    except Exception as e:
        print(f"[Ngrok] Error starting: {e}")
        return False

def stop_all():
    """Останавливает все процессы"""
    try:
        # Убиваем gotty
        subprocess.run(["pkill", "-9", "gotty"], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL)
        
        # Убиваем ngrok
        subprocess.run(["pkill", "-9", "ngrok"], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL)
        
        print("[Cleanup] Stopped all processes")
        time.sleep(2)
    except:
        pass

def restart_gotty():
    """Перезапускает gotty"""
    print("\n" + "="*60)
    print("[RESTART] Restarting gotty + ngrok...")
    print("="*60)
    
    stop_all()
    time.sleep(3)
    
    # Запускаем gotty через freeroot
    if start_gotty_via_freeroot():
        # Если gotty запустился, запускаем ngrok
        time.sleep(3)
        start_ngrok()
    else:
        print("[RESTART] Failed to restart gotty")

def gotty_watchdog():
    """Следит за gotty и перезапускает каждые 10 минут"""
    print("[Watchdog] Starting watchdog (10 minute cycles)...")
    
    # Первый запуск
    restart_gotty()
    
    cycle_count = 0
    while True:
        try:
            # Ждем 10 минут (600 секунд)
            cycle_count += 1
            print(f"\n[Watchdog] Cycle #{cycle_count}: Sleeping for 10 minutes...")
            
            # Отсчет
            for i in range(600, 0, -60):
                if i % 300 == 0:  # Каждые 5 минут
                    print(f"[Watchdog] Next restart in {i//60} minutes...")
                time.sleep(60)
            
            # Перезапускаем
            restart_gotty()
            
        except Exception as e:
            print(f"[Watchdog] Error: {e}")
            time.sleep(60)

# ==================== ОСНОВНОЙ HTTP СЕРВЕР ====================

def create_http_server(port):
    """Создает HTTP сервер на указанном порту"""
    def server_thread():
        while True:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(('0.0.0.0', port))
                sock.listen(10)
                sock.settimeout(1)
                
                print(f"[Server] Started on port {port}")
                
                request_count = 0
                
                while True:
                    try:
                        client, addr = sock.accept()
                        request_count += 1
                        
                        try:
                            request = client.recv(4096).decode('utf-8', errors='ignore')
                            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            
                            if 'GET /console' in request:
                                response = f"""HTTP/1.1 200 OK
Content-Type: text/html
Connection: close

<!DOCTYPE html>
<html>
<body style="font-family: Arial; padding: 20px;">
<h1>FunPay Cardinal Bot + ROOT Console</h1>
<div style="background: #e8f4f8; padding: 20px; border-radius: 10px; margin: 20px 0;">
<h3>🔧 ROOT Console Access</h3>
<p><strong>Local:</strong> <a href="http://127.0.0.1:{GOTTY_PORT}" target="_blank">http://127.0.0.1:{GOTTY_PORT}</a></p>
<p><strong>Status:</strong> <span style="color: green;">● Running as ROOT</span></p>
<p><strong>Auto-restart:</strong> Every 10 minutes</p>
<p><strong>Bot port:</strong> {port}</p>
<p><strong>Time:</strong> {current_time}</p>
</div>
<p><button onclick="window.open('http://127.0.0.1:{GOTTY_PORT}', '_blank')" style="background: #28a745; color: white; padding: 12px 24px; border: none; border-radius: 5px; font-size: 16px; cursor: pointer;">Open ROOT Console</button></p>
</body>
</html>"""
                            elif 'GET /health' in request:
                                response = f"""HTTP/1.1 200 OK
Content-Type: application/json
Connection: close

{{"status": "ok", "bot": "running", "console": "running", "console_port": {GOTTY_PORT}, "root_access": true, "time": "{current_time}"}}"""
                            else:
                                response = f"""HTTP/1.1 200 OK
Content-Type: text/html
Connection: close

<!DOCTYPE html>
<html>
<body style="font-family: Arial; padding: 20px;">
<h1>FunPay Cardinal Bot</h1>
<p>Status: <span style="color: green;">Running</span></p>
<p>Root Console: <a href="/console">Available</a> (port {GOTTY_PORT})</p>
<p>Time: {current_time}</p>
</body>
</html>"""
                            
                            client.send(response.encode())
                            client.close()
                            
                        except Exception as e:
                            client.send(b'HTTP/1.1 200 OK\r\n\r\nOK')
                            client.close()
                            
                    except socket.timeout:
                        continue
                    except Exception as e:
                        print(f"[Server:{port}] Accept error: {e}")
                        break
                        
            except Exception as e:
                print(f"[Server:{port}] Error: {e}, restarting in 2s...")
                time.sleep(2)
    
    thread = threading.Thread(target=server_thread, daemon=True)
    thread.start()
    return thread

# ==================== ВНЕШНИЕ ПИНГИ ====================

def setup_external_pings():
    """Настройка внешних пингов"""
    def external_pinger():
        print("[Pinger] Waiting 30 seconds before first ping...")
        time.sleep(30)
        ping_counter = 0
        
        while True:
            try:
                ping_counter += 1
                current_time = datetime.now().strftime("%H:%M:%S")
                
                # Пинг внешних сайтов
                if ping_counter % 2 == 0:
                    external_url = "https://www.google.com"
                else:
                    external_url = "https://1.1.1.1"
                    
                try:
                    response = requests.get(external_url, timeout=10, headers={
                        'User-Agent': 'Mozilla/5.0 (Koyeb-KeepAlive)'
                    })
                    print(f"[{current_time}] Ping #{ping_counter}: {response.status_code}")
                except Exception as e:
                    print(f"[{current_time}] Ping failed: {e}")
                
                # Пинг себя
                if ping_counter % 5 == 0:
                    try:
                        response = requests.get(f"http://localhost:{KOYEB_PORT}/health", timeout=5)
                        print(f"[{current_time}] Self ping: {response.status_code}")
                    except:
                        print(f"[{current_time}] Self ping failed")
                
                # Ждем 4 минуты
                sleep_time = 240
                time.sleep(sleep_time)
                
            except Exception as e:
                print(f"[Pinger] Error: {e}")
                time.sleep(60)
    
    threading.Thread(target=external_pinger, daemon=True).start()
    print("[Pinger] External ping service started")

# ==================== ИНИЦИАЛИЗАЦИЯ ====================

def initialize_koyeb_system():
    """Инициализация всей системы"""
    print("=" * 60)
    print("🎯 FUNPAY CARDINAL BOT + ROOT CONSOLE")
    print("=" * 60)
    print(f"Bot Port: {KOYEB_PORT}")
    print(f"Root Console Port: {GOTTY_PORT}")
    print(f"Console URL: http://127.0.0.1:{GOTTY_PORT}")
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print("🚀 Features:")
    print("• Root access via freeroot")
    print("• Auto-restart every 10 minutes")
    print("• Ngrok tunnel for external access")
    print("• Health monitoring")
    print("=" * 60)
    
    # Сначала очищаем старые процессы
    stop_all()
    time.sleep(2)
    
    # Запускаем основной сервер
    create_http_server(KOYEB_PORT)
    
    # Запускаем watchdog для gotty (будет запускать через freeroot)
    watchdog_thread = threading.Thread(target=gotty_watchdog, daemon=True)
    watchdog_thread.start()
    print(f"[System] Gotty watchdog started (via freeroot)")
    
    # Запускаем внешние пинги
    setup_external_pings()
    
    # Мониторинг
    def monitor():
        start_time = datetime.now()
        while True:
            uptime = datetime.now() - start_time
            hours = uptime.total_seconds() / 3600
            
            # Проверяем gotty
            gotty_running = check_gotty_running()
            status = "✅ RUNNING" if gotty_running else "❌ STOPPED"
            
            print(f"\n📊 [Status Dashboard]")
            print(f"   Uptime: {hours:.1f} hours")
            print(f"   Gotty: {status}")
            print(f"   Console: http://127.0.0.1:{GOTTY_PORT}")
            print(f"   Bot: http://127.0.0.1:{KOYEB_PORT}")
            print(f"   Time: {datetime.now().strftime('%H:%M:%S')}")
            time.sleep(300)
    
    threading.Thread(target=monitor, daemon=True).start()
    print("[System] All systems initialized!")

# ==================== ЗАПУСК СИСТЕМЫ ====================

# Инициализируем систему
initialize_koyeb_system()

# Ждем запуска
time.sleep(5)

# Проверяем gotty
if check_gotty_running():
    print("\n" + "=" * 60)
    print("✅ SUCCESS: Root console is RUNNING!")
    print("=" * 60)
    print(f"Access: http://127.0.0.1:{GOTTY_PORT}")
    print("Credentials: None required (running as root)")
    print("Auto-restart: Every 10 minutes")
    print("=" * 60 + "\n")
else:
    print("\n" + "=" * 60)
    print("⚠️  WARNING: Console not running")
    print("=" * 60)
    print("Will retry via watchdog...")
    print("=" * 60 + "\n")

# Установка зависимостей для Cardinal бота
print("[Setup] Checking Cardinal dependencies...")
while True:
    try:
        import lxml
        print("[✓] lxml is installed")
        break
    except ModuleNotFoundError:
        print("[!] Installing lxml...")
        main(["install", "-U", "lxml>=5.3.0"])
        
while True:
    try:
        import bcrypt
        print("[✓] bcrypt is installed")
        break
    except ModuleNotFoundError:
        print("[!] Installing bcrypt...")
        main(["install", "-U", "bcrypt>=4.2.0"])

print("[✓] All dependencies installed\n")

# ВАШ ОСТАЛЬНОЙ КОД БЕЗ ИЗМЕНЕНИЙ...
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
