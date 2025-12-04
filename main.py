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

# ==================== ПРОСТОЙ GOTTY ====================

def start_gotty():
    """Простой запуск gotty - пользователь сам получит root"""
    try:
        print("[Gotty] Starting simple gotty...")
        
        # Убиваем старые процессы
        subprocess.run(["pkill", "-9", "gotty"], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL)
        time.sleep(2)
        
        # Проверяем есть ли gotty
        if not os.path.exists("./gotty"):
            print("[Gotty] Downloading gotty...")
            subprocess.run([
                "wget", "-q",
                "https://github.com/yudai/gotty/releases/download/v2.0.0-alpha.3/gotty_2.0.0-alpha.3_linux_amd64.tar.gz",
                "-O", "gotty.tar.gz"
            ], check=True)
            subprocess.run(["tar", "-xzf", "gotty.tar.gz"], check=True)
            subprocess.run(["chmod", "+x", "gotty"], check=True)
        
        # Запускаем gotty с простым bash
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
        
        # Проверяем
        result = subprocess.run(
            ["ss", "-tulpn"],
            capture_output=True,
            text=True
        )
        
        if f":{GOTTY_PORT}" in result.stdout:
            print(f"[✓] Gotty запущен на порту {GOTTY_PORT}")
            print(f"[✓] Откройте: http://127.0.0.1:{GOTTY_PORT}")
            print(f"[✓] В терминале выполните: cd freeroot && bash root.sh && su")
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
        # Проверяем есть ли ngrok
        if not os.path.exists("./ngrok"):
            print("[Ngrok] Downloading ngrok...")
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
        
        # Запускаем с pooling
        print("[Ngrok] Starting with pooling...")
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
        
        # Читаем вывод
        def read_output():
            for line in iter(process.stdout.readline, ''):
                if "Forwarding" in line:
                    print(f"[Ngrok LINK] {line.strip()}")
        
        threading.Thread(target=read_output, daemon=True).start()
        
        time.sleep(5)
        print("[Ngrok] Запущен")
        return True
        
    except Exception as e:
        print(f"[Ngrok] Ошибка: {e}")
        return False

def restart_services():
    """Перезапускает gotty и ngrok"""
    print("\n[Restart] Перезапуск сервисов...")
    
    # Убиваем всё
    subprocess.run(["pkill", "-9", "gotty"], 
                  stdout=subprocess.DEVNULL, 
                  stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-9", "ngrok"], 
                  stdout=subprocess.DEVNULL, 
                  stderr=subprocess.DEVNULL)
    time.sleep(3)
    
    # Запускаем
    start_gotty()
    time.sleep(2)
    start_ngrok()

def watchdog():
    """Следит и перезапускает каждые 10 минут"""
    print("[Watchdog] Запущен (перезапуск каждые 10 минут)")
    
    # Первый запуск
    restart_services()
    
    while True:
        time.sleep(600)  # 10 минут
        print("\n[Watchdog] Перезапуск по расписанию...")
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
                        client.recv(1024)  # Читаем запрос
                        
                        response = f"""HTTP/1.1 200 OK
Content-Type: text/html

<html><body>
<h1>FunPay Cardinal Bot</h1>
<p>Консоль: <a href="http://127.0.0.1:{GOTTY_PORT}">http://127.0.0.1:{GOTTY_PORT}</a></p>
</body></html>"""
                        
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

# ==================== ИНИЦИАЛИЗАЦИЯ ====================

def initialize():
    """Инициализация"""
    print("=" * 50)
    print("FunPay Cardinal Bot + Console")
    print(f"Bot порт: {KOYEB_PORT}")
    print(f"Console порт: {GOTTY_PORT}")
    print("=" * 50)
    
    # Запускаем сервер
    create_http_server(KOYEB_PORT)
    
    # Запускаем watchdog
    threading.Thread(target=watchdog, daemon=True).start()
    
    print("[System] Система запущена")

# ==================== ЗАПУСК ====================

# Инициализируем
initialize()
time.sleep(3)

print(f"\n📌 ИНСТРУКЦИЯ:")
print(f"1. Откройте: http://127.0.0.1:{GOTTY_PORT}")
print(f"2. В терминале выполните: cd freeroot && bash root.sh && su")
print(f"3. Консоль перезапускается каждые 10 минут")
print(f"4. Ссылка ngrok появится выше (ищите 'Forwarding')")

# Установка зависимостей для Cardinal
print("\n[Setup] Проверка зависимостей...")
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

print("[✓] Зависимости установлены\n")

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
