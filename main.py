import time
import socket
import threading
import requests
import random
import sys
import os
import subprocess
from datetime import datetime
from pip._internal.cli.main import main

# ==================== КОНСТАНТЫ ====================
KOYEB_PORT = int(os.getenv("PORT", 8080))
GOTTY_PORT = 8086
RESTART_HOURS = 2
RESTART_SECONDS = 600

# ==================== ПРОСТОЙ GOTTY ====================

def start_gotty():
    """Простой запуск gotty"""
    try:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Запуск gotty...")
        
        subprocess.run(["pkill", "-9", "gotty"], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL)
        time.sleep(2)
        
        if not os.path.exists("./gotty"):
            print("[!] Скачиваю gotty...")
            subprocess.run([
                "wget", "-q",
                "https://github.com/yudai/gotty/releases/download/v2.0.0-alpha.3/gotty_2.0.0-alpha.3_linux_amd64.tar.gz",
                "-O", "gotty.tar.gz"
            ], check=True)
            subprocess.run(["tar", "-xzf", "gotty.tar.gz"], check=True)
            subprocess.run(["chmod", "+x", "gotty"], check=True)
        
        gotty_cmd = [
            "./gotty",
            "-a", "127.0.0.1",
            "-p", str(GOTTY_PORT),
            "-w",
            "bash"
        ]
        
        process = subprocess.Popen(
            gotty_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid
        )
        
        time.sleep(3)
        
        result = subprocess.run(
            ["ss", "-tulpn"],
            capture_output=True,
            text=True
        )
        
        if f":{GOTTY_PORT}" in result.stdout:
            print(f"[✓] Gotty запущен на порту {GOTTY_PORT}")
            print(f"[✓] Консоль: http://127.0.0.1:{GOTTY_PORT}")
            return True
        else:
            print("[✗] Gotty не запустился")
            return False
            
    except Exception as e:
        print(f"[Gotty] Ошибка: {e}")
        return False

def start_ngrok():
    """Запускает ngrok"""
    try:
        if not os.path.exists("./ngrok"):
            print("[!] Скачиваю ngrok...")
            subprocess.run([
                "wget", "-q",
                "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz",
                "-O", "ngrok.tgz"
            ], check=True)
            subprocess.run(["tar", "-xzf", "ngrok.tgz"], check=True)
            subprocess.run(["chmod", "+x", "ngrok"], check=True)
        
        subprocess.run(["pkill", "-9", "ngrok"], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL)
        time.sleep(3)
        
        ngrok_token = "36Nxsby4doMoAS00XhE1QFDTOoj_jWAC8i8QLdu4is6dmgRS"
        subprocess.run(
            f"./ngrok config add-authtoken {ngrok_token}",
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        print("[Ngrok] Запуск туннеля...")
        ngrok_cmd = f"./ngrok http 127.0.0.1:{GOTTY_PORT} --pooling-enabled"
        
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
        
        def read_output():
            for line in iter(process.stdout.readline, ''):
                if "Forwarding" in line:
                    print(f"[Ngrok] Ссылка: {line.strip()}")
        
        threading.Thread(target=read_output, daemon=True).start()
        
        time.sleep(5)
        print("[✓] Ngrok запущен")
        return True
        
    except Exception as e:
        print(f"[Ngrok] Ошибка: {e}")
        return False

def restart_services():
    """Перезапускает gotty и ngrok"""
    current_time = datetime.now().strftime("%H:%M:%S")
    print(f"\n[{current_time}] Перезапуск сервисов...")
    
    subprocess.run(["pkill", "-9", "gotty"], 
                  stdout=subprocess.DEVNULL, 
                  stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-9", "ngrok"], 
                  stdout=subprocess.DEVNULL, 
                  stderr=subprocess.DEVNULL)
    time.sleep(3)
    
    if start_gotty():
        time.sleep(2)
        start_ngrok()

def watchdog():
    """Перезапускает каждые 2 часа"""
    print(f"[Watchdog] Запущен (перезапуск каждые {RESTART_HOURS} часа)")
    
    restart_services()
    
    while True:
        print(f"[Watchdog] Следующий перезапуск через {RESTART_HOURS} часа...")
        time.sleep(RESTART_SECONDS)
        restart_services()

# ==================== HTTP СЕРВЕР ====================

def create_http_server(port):
    """Создает HTTP сервер"""
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
                        client.recv(1024)
                        
                        response = f"""HTTP/1.1 200 OK
Content-Type: text/html

<html>
<body style="font-family: Arial; padding: 20px;">
<h1>FunPay Cardinal Bot</h1>
<p>Консоль доступна на порту: {GOTTY_PORT}</p>
<p>Время: {datetime.now().strftime('%H:%M:%S')}</p>
</body>
</html>"""
                        
                        client.send(response.encode())
                        client.close()
                        
                    except socket.timeout:
                        continue
                    except:
                        break
                        
            except Exception as e:
                print(f"[Server] Ошибка: {e}")
                time.sleep(2)
    
    thread = threading.Thread(target=server_thread, daemon=True)
    thread.start()

# ==================== ПИНГИ ДЛЯ KOYEB ====================

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
    print("=" * 50)
    print("FunPay Cardinal Bot")
    print("=" * 50)
    print(f"Бот порт: {KOYEB_PORT}")
    print(f"Консоль порт: {GOTTY_PORT}")
    print(f"Перезапуск: каждые {RESTART_HOURS} часа")
    print(f"Время запуска: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 50)
    
    create_http_server(KOYEB_PORT)
    setup_pings()
    threading.Thread(target=watchdog, daemon=True).start()
    print("[System] Система запущена")

# ==================== ЗАПУСК СИСТЕМЫ ====================

initialize()
time.sleep(3)

print(f"\n✅ ГОТОВО!")
print(f"Консоль: http://127.0.0.1:{GOTTY_PORT}")
print(f"Для root доступа в консоли выполните:")
print(f"cd freeroot && bash root.sh && su")
print(f"\nАвтоперезапуск каждые {RESTART_HOURS} часа")
print(f"Ngrok ссылка появится выше в логах")

# ==================== ОРИГИНАЛЬНЫЙ КОД CARDINAL ====================

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
