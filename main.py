import time
import socket
import threading
import requests
import random
import sys
import os
from datetime import datetime
from pip._internal.cli.main import main

# ==================== КОНСТАНТЫ ДЛЯ KOYEB ====================
KOYEB_PORT = int(os.getenv("PORT", 8080))

# ==================== ВНЕШНИЕ ПИНГИ ====================
EXTERNAL_PING_URLS = [
    # Бесплатные сервисы для пинга
    "https://hc-ping.com/",  # Healthchecks.io - БЕСПЛАТНО!
    "https://api.uptimerobot.com/v2/getMonitors",  # UptimeRobot API
    "https://www.google.com",
    "https://www.cloudflare.com",
    "https://1.1.1.1",
    "https://api.github.com",
]

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
                            # Читаем запрос
                            request = client.recv(4096).decode('utf-8', errors='ignore')
                            
                            # Формируем ответ
                            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            
                            if 'GET /health' in request or 'GET /ping' in request:
                                response = f"""HTTP/1.1 200 OK
Content-Type: application/json
Access-Control-Allow-Origin: *

{{"status": "ok", "port": {port}, "time": "{current_time}", "requests": {request_count}}}"""
                            elif 'GET /' in request:
                                response = f"""HTTP/1.1 200 OK
Content-Type: text/html

<!DOCTYPE html>
<html>
<body>
<h1>Koyeb Anti-Sleep</h1>
<p>Port: {port}</p>
<p>Time: {current_time}</p>
<p>Requests: {request_count}</p>
</body>
</html>"""
                            else:
                                response = f"""HTTP/1.1 200 OK
Content-Type: text/plain

OK - {current_time}"""
                            
                            client.send(response.encode())
                            client.close()
                            
                            # Логируем только каждое 10-е обращение
                            if request_count % 10 == 0:
                                print(f"[Server:{port}] Request #{request_count} from {addr[0]}")
                                
                        except:
                            client.send(b'HTTP/1.1 200 OK\r\n\r\nOK')
                            client.close()
                            
                    except socket.timeout:
                        # Таймаут - это нормально
                        continue
                    except Exception as e:
                        break
                        
            except Exception as e:
                print(f"[Server:{port}] Error: {e}, restarting in 2s...")
                time.sleep(2)
    
    thread = threading.Thread(target=server_thread, daemon=True)
    thread.start()
    return thread

# ==================== ВНЕШНИЕ ПИНГИ ДЛЯ KOYEB ====================

def setup_external_pings():
    """
    Настройка ВНЕШНИХ пингов - это КРИТИЧЕСКИ ВАЖНО!
    Koyeb видит только ВНЕШНИЙ трафик, локальные пинги не считаются!
    """
    
    def external_pinger():
        """Делает пинги на внешние сервисы"""
        ping_counter = 0
        
        # Ждем 30 секунд перед первым пингом
        time.sleep(30)
        
        while True:
            try:
                ping_counter += 1
                current_time = datetime.now().strftime("%H:%M:%S")
                
                # Шаг 1: Пингуем ВНЕШНИЕ сайты (это создает исходящий трафик)
                external_url = random.choice(EXTERNAL_PING_URLS[2:])  # Берем не-API урлы
                try:
                    response = requests.get(external_url, timeout=10, headers={
                        'User-Agent': 'Mozilla/5.0 (Koyeb-KeepAlive)'
                    })
                    print(f"[{current_time}] External ping #{ping_counter}: {external_url} - {response.status_code}")
                except Exception as e:
                    print(f"[{current_time}] External ping #{ping_counter}: Failed - {e}")
                
                # Шаг 2: Пингуем СЕБЯ через публичный URL (если знаем его)
                # Попробуем получить URL приложения из переменных окружения
                app_name = os.getenv("KOYEB_APP_NAME")
                if app_name:
                    try:
                        public_url = f"https://{app_name}.koyeb.app"
                        response = requests.get(f"{public_url}/health", timeout=10)
                        print(f"[{current_time}] Self-public ping #{ping_counter}: {response.status_code}")
                    except:
                        # Если не знаем публичный URL, пингуем локально
                        try:
                            response = requests.get(f"http://localhost:{KOYEB_PORT}/health", timeout=5)
                            print(f"[{current_time}] Self-local ping #{ping_counter}: {response.status_code}")
                        except:
                            print(f"[{current_time}] Self ping #{ping_counter}: Failed")
                
                # Шаг 3: Используем Healthchecks.io (БЕСПЛАТНО!)
                # Зарегистрируйтесь на https://healthchecks.io и получите свой UUID
                healthchecks_uuid = os.getenv("HEALTHCHECKS_UUID")
                if healthchecks_uuid and ping_counter % 3 == 0:  # Каждые 3 пинга
                    try:
                        hc_url = f"https://hc-ping.com/{healthchecks_uuid}"
                        response = requests.get(hc_url, timeout=5)
                        print(f"[{current_time}] Healthchecks.io ping")
                    except:
                        pass
                
                # Шаг 4: Критически важная часть - ждем МЕНЬШЕ 5 минут!
                # Koyeb засыпает через 300 секунд (5 минут)
                # Поэтому пингуем каждые 240 секунд (4 минуты)
                sleep_time = 240  # 4 минуты
                print(f"[{current_time}] Next ping in {sleep_time} seconds...")
                time.sleep(sleep_time)
                
            except Exception as e:
                print(f"[Pinger] Error: {e}")
                time.sleep(60)
    
    # Запускаем внешние пинги
    threading.Thread(target=external_pinger, daemon=True).start()
    print("[Pinger] External ping service started (every 4 minutes)")

# ==================== ИНИЦИАЛИЗАЦИЯ ====================

def initialize_koyeb_system():
    """Инициализация всей системы"""
    print("=" * 60)
    print("KOYEB ANTI-SLEEP SYSTEM v2.0")
    print(f"Port: {KOYEB_PORT}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Запускаем основной сервер
    create_http_server(KOYEB_PORT)
    
    # Запускаем дополнительные серверы для надежности
    for port in [8081, 8082, 8083]:
        create_http_server(port)
        time.sleep(0.5)
    
    # Запускаем ВНЕШНИЕ пинги (это самое важное!)
    setup_external_pings()
    
    # Запускаем мониторинг
    def monitor():
        start_time = datetime.now()
        while True:
            uptime = datetime.now() - start_time
            hours = uptime.total_seconds() / 3600
            
            # Критически важное сообщение
            print("\n" + "=" * 60)
            print("ВАЖНО: Koyeb видит только ВНЕШНИЙ трафик!")
            print("Локальные пинги НЕ предотвращают сон!")
            print(f"Uptime: {hours:.1f} hours")
            print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
            print("=" * 60 + "\n")
            
            time.sleep(180)  # Каждые 3 минуты
    
    threading.Thread(target=monitor, daemon=True).start()
    
    print("[System] All systems initialized!")
    print("[System] Make sure to setup EXTERNAL monitoring:")
    print("  1. Register at https://healthchecks.io (FREE)")
    print("  2. Add HEALTHCHECKS_UUID to environment variables")
    print("  3. Or use UptimeRobot/FreshPing for external pings")
    print("=" * 60)

# ==================== ЗАПУСК СИСТЕМЫ ====================

# Инициализируем систему
initialize_koyeb_system()

# Ждем запуска серверов
time.sleep(3)

# todo убрать когда-то
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
