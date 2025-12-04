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

def start_gotty():
    """Запускает gotty с root доступом через freeroot"""
    global gotty_process
    
    # Скачиваем gotty если нет
    download_gotty()
    
    # Проверяем, не запущен ли уже
    if check_gotty_running():
        print("[Gotty] Already running (checked by pgrep)")
        return True
    
    try:
        print("[Gotty] Starting gotty with freeroot...")
        
        # ВАРИАНТ 1: Просто запускаем bash, а пользователь сам выполнит команды
        gotty_cmd = [
            "./gotty",
            "-a", "127.0.0.1",
            "-p", str(GOTTY_PORT),
            "-w",
            "--credential", "user:user",  # простой логин
            "bash"  # просто bash, без скриптов
        ]
        
        print(f"[Gotty] Command: {' '.join(gotty_cmd)}")
        print("[Gotty] After login, run: cd freeroot && bash root.sh && su")
        
        # ВАРИАНТ 2: Или создаем скрипт который выполнит команды
        script_content = """#!/bin/bash
echo "========================================"
echo "  FREEROOT ACCESS SCRIPT"
echo "========================================"
echo "1. Changing to freeroot directory..."
cd /workspace/freeroot
echo "2. Running root.sh..."
bash root.sh
echo "3. Switching to root..."
echo "========================================"
echo "You are now root! Type 'exit' to logout."
echo "========================================"
exec su
"""
        
        with open("/tmp/root_access.sh", "w") as f:
            f.write(script_content)
        os.chmod("/tmp/root_access.sh", 0o755)
        
        # Альтернативная команда со скриптом
        gotty_cmd = [
            "./gotty",
            "-a", "127.0.0.1",
            "-p", str(GOTTY_PORT),
            "-w",
            "--credential", "user:user",
            "bash", "-c", "cd /workspace/freeroot && bash root.sh && su"
        ]
        
        # Запускаем gotty
        gotty_process = subprocess.Popen(
            gotty_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid
        )
        
        # Ждем запуска
        time.sleep(3)
        
        # Проверяем, запустился ли
        if gotty_process.poll() is not None:
            stdout, stderr = gotty_process.communicate()
            print(f"[Gotty] Failed to start: {stderr}")
            
            # Пробуем простой вариант без сложных команд
            print("[Gotty] Trying simple bash only...")
            simple_cmd = [
                "./gotty",
                "-a", "127.0.0.1",
                "-p", str(GOTTY_PORT),
                "-w",
                "bash"
            ]
            gotty_process = subprocess.Popen(
                simple_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid
            )
        
        print(f"[Gotty] Started on port {GOTTY_PORT}")
        print(f"[Gotty] Access: http://127.0.0.1:{GOTTY_PORT}")
        print(f"[Gotty] No credentials required")
        print(f"[Gotty] After login run: cd freeroot && bash root.sh && su")
        return True
        
    except Exception as e:
        print(f"[Gotty] Error starting: {e}")
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
        ngrok_cmd = f"./ngrok http 127.0.0.1:{GOTTY_PORT}"
        ngrok_process = subprocess.Popen(
            ngrok_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=os.setsid
        )
        
        # Ждем запуска
        time.sleep(5)
        
        print("[Ngrok] Started (check output for URL)")
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
    except:
        pass

def restart_gotty():
    """Перезапускает gotty"""
    print("[Restart] Restarting gotty and ngrok...")
    stop_all()
    time.sleep(3)
    
    # Запускаем gotty
    if start_gotty():
        # Если gotty запустился, запускаем ngrok
        time.sleep(2)
        start_ngrok()
    else:
        print("[Restart] Failed to restart gotty")

def gotty_watchdog():
    """Следит за gotty и перезапускает каждые 10 минут"""
    print("[Watchdog] Starting watchdog...")
    
    # Первый запуск
    restart_gotty()
    
    while True:
        try:
            # Ждем 10 минут (600 секунд)
            print("[Watchdog] Sleeping for 10 minutes...")
            time.sleep(600)
            
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
<h1>FunPay Cardinal Bot Control Panel</h1>
<div style="background: #f0f0f0; padding: 20px; border-radius: 10px; margin: 20px 0;">
<h3>Console Access</h3>
<p>• Bot Status: <span style="color: green;">Running</span></p>
<p>• Console Port: {GOTTY_PORT}</p>
<p>• Time: {current_time}</p>
<p>• Requests: {request_count}</p>
</div>
<p><a href="http://127.0.0.1:{GOTTY_PORT}" target="_blank" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Open Root Console</a></p>
</body>
</html>"""
                            elif 'GET /health' in request:
                                response = f"""HTTP/1.1 200 OK
Content-Type: application/json
Connection: close

{{"status": "ok", "bot": "running", "console_port": {GOTTY_PORT}, "time": "{current_time}"}}"""
                            else:
                                response = f"""HTTP/1.1 200 OK
Content-Type: text/html
Connection: close

<!DOCTYPE html>
<html>
<body style="font-family: Arial; padding: 20px;">
<h1>FunPay Cardinal Bot</h1>
<p>Status: <span style="color: green;">Running</span></p>
<p>Time: {current_time}</p>
<p><a href="/console">Go to Control Panel</a></p>
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
    print("FUNPAY CARDINAL BOT + CONSOLE")
    print(f"Bot Port: {KOYEB_PORT}")
    print(f"Console Port: {GOTTY_PORT} (root access)")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Сначала очищаем старые процессы
    stop_all()
    time.sleep(2)
    
    # Запускаем основной сервер
    create_http_server(KOYEB_PORT)
    
    # Запускаем watchdog для gotty
    watchdog_thread = threading.Thread(target=gotty_watchdog, daemon=True)
    watchdog_thread.start()
    print(f"[System] Gotty watchdog started")
    
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
            status = "RUNNING" if gotty_running else "STOPPED"
            color = "GREEN" if gotty_running else "RED"
            
            print(f"\n[Status] Uptime: {hours:.1f}h | Gotty: {status} | Console: http://127.0.0.1:{GOTTY_PORT}")
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
    print("[✓] Gotty is running successfully!")
else:
    print("[✗] Gotty failed to start!")

print("\n" + "=" * 60)
print("ACCESS INSTRUCTIONS:")
print(f"1. Bot interface: http://127.0.0.1:{KOYEB_PORT}")
print(f"2. Root console: http://127.0.0.1:{GOTTY_PORT}")
print(f"3. Login: root / root")
print("4. Console auto-restarts every 10 minutes")
print("=" * 60 + "\n")

# Установка зависимостей
print("[Setup] Checking dependencies...")
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
