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

def start_gotty():
    """Запускает gotty с root доступом"""
    global gotty_process
    try:
        # Проверяем, не запущен ли уже gotty
        check = subprocess.run(["pgrep", "-f", "gotty.*bash"], capture_output=True)
        if check.returncode == 0:
            print(f"[Gotty] Already running")
            return
        
        # Запускаем gotty с root доступом через freeroot
        gotty_cmd = f"./gotty -a 127.0.0.1 -p {GOTTY_PORT} -w --credential root:root bash -c 'cd /workspace/freeroot && bash root.sh && su'"
        
        gotty_process = subprocess.Popen(
            gotty_cmd,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid
        )
        print(f"[Gotty] Started on port {GOTTY_PORT} with root access")
        
        # Также запускаем ngrok для доступа извне
        time.sleep(3)
        start_ngrok()
        
    except Exception as e:
        print(f"[Gotty] Error: {e}")

def start_ngrok():
    """Запускает ngrok для gotty"""
    try:
        ngrok_cmd = f"./ngrok http 127.0.0.1:{GOTTY_PORT}"
        subprocess.Popen(
            ngrok_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        print(f"[Ngrok] Started tunnel to gotty")
    except Exception as e:
        print(f"[Ngrok] Error: {e}")

def stop_gotty():
    """Останавливает gotty и ngrok"""
    global gotty_process
    try:
        # Убиваем gotty
        subprocess.run(["pkill", "-9", "-f", "gotty"], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL)
        
        # Убиваем ngrok
        subprocess.run(["pkill", "-9", "ngrok"], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL)
        
        print(f"[Gotty] Stopped")
    except:
        pass
    gotty_process = None

def restart_gotty():
    """Перезапускает gotty каждые 10 минут"""
    print(f"[Gotty] Restarting...")
    stop_gotty()
    time.sleep(2)
    start_gotty()

def gotty_watchdog():
    """Следит за gotty и перезапускает каждые 10 минут"""
    # Первый запуск
    start_gotty()
    
    while True:
        try:
            # Ждем 10 минут (600 секунд)
            time.sleep(600)
            
            # Перезапускаем
            restart_gotty()
            
        except Exception as e:
            print(f"[Gotty Watchdog] Error: {e}")
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
                                # Показываем ссылку на консоль
                                response = f"""HTTP/1.1 200 OK
Content-Type: text/html

<!DOCTYPE html>
<html>
<body>
<h1>Cardinal Bot + Console</h1>
<p>Bot running on port: {KOYEB_PORT}</p>
<p>Console (root access): http://127.0.0.1:{GOTTY_PORT}</p>
<p>Time: {current_time}</p>
<p><a href="http://127.0.0.1:{GOTTY_PORT}" target="_blank">Open Console</a></p>
</body>
</html>"""
                            elif 'GET /health' in request:
                                response = f"""HTTP/1.1 200 OK
Content-Type: application/json

{{"status": "ok", "bot": "running", "console": "running", "time": "{current_time}"}}"""
                            else:
                                response = f"""HTTP/1.1 200 OK
Content-Type: text/html

<!DOCTYPE html>
<html>
<body>
<h1>FunPay Cardinal Bot</h1>
<p>Status: Running</p>
<p>Time: {current_time}</p>
<p><a href="/console">Console Access</a></p>
</body>
</html>"""
                            
                            client.send(response.encode())
                            client.close()
                            
                        except:
                            client.send(b'HTTP/1.1 200 OK\r\n\r\nOK')
                            client.close()
                            
                    except socket.timeout:
                        continue
                    except Exception as e:
                        break
                        
            except Exception as e:
                print(f"[Server:{port}] Error: {e}, restarting...")
                time.sleep(2)
    
    thread = threading.Thread(target=server_thread, daemon=True)
    thread.start()
    return thread

# ==================== ВНЕШНИЕ ПИНГИ ====================

def setup_external_pings():
    """Настройка внешних пингов"""
    def external_pinger():
        time.sleep(30)
        ping_counter = 0
        
        while True:
            try:
                ping_counter += 1
                current_time = datetime.now().strftime("%H:%M:%S")
                
                # Пинг внешних сайтов
                external_url = random.choice(EXTERNAL_PING_URLS[1:])
                try:
                    response = requests.get(external_url, timeout=10)
                    print(f"[{current_time}] Ping #{ping_counter}: {response.status_code}")
                except Exception as e:
                    print(f"[{current_time}] Ping failed: {e}")
                
                # Пинг себя
                try:
                    response = requests.get(f"http://localhost:{KOYEB_PORT}/health", timeout=5)
                except:
                    pass
                
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
    
    # Запускаем основной сервер
    create_http_server(KOYEB_PORT)
    
    # Запускаем gotty watchdog (будет перезапускать каждые 10 минут)
    threading.Thread(target=gotty_watchdog, daemon=True).start()
    
    # Запускаем внешние пинги
    setup_external_pings()
    
    # Мониторинг
    def monitor():
        start_time = datetime.now()
        while True:
            uptime = datetime.now() - start_time
            hours = uptime.total_seconds() / 3600
            print(f"\n[Status] Uptime: {hours:.1f}h | Console: http://127.0.0.1:{GOTTY_PORT}")
            time.sleep(300)
    
    threading.Thread(target=monitor, daemon=True).start()
    print("[System] All systems initialized!")

# ==================== ЗАПУСК СИСТЕМЫ ====================

# Инициализируем систему
initialize_koyeb_system()

# Ждем запуска
time.sleep(3)

# Установка зависимостей
while True:
    try:
        import lxml
        break
    except ModuleNotFoundError:
        main(["install", "-U", "lxml>=5.3.0"])
        
while True:
    try:
        import bcrypt
        break
    except ModuleNotFoundError:
        main(["install", "-U", "bcrypt>=4.2.0"])

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
