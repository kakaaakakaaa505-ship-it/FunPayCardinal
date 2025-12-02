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
KOYEB_PORT = int(os.getenv("PORT", 8080))  # Koyeb использует порт 8080

# ==================== ВНЕШНИЕ СЕРВИСЫ ДЛЯ ПИНГА ====================
EXTERNAL_URLS = [
    "https://www.google.com",
    "https://www.cloudflare.com",
    "https://1.1.1.1",
    "https://www.github.com",
    "https://www.microsoft.com",
]

# ==================== ОСНОВНОЙ HTTP СЕРВЕР НА ПОРТУ 8080 ====================

def start_koyeb_server(port=8080):
    """Запускает основной HTTP сервер для Koyeb"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', port))
        sock.listen(10)
        
        def handle_connections():
            while True:
                try:
                    client, addr = sock.accept()
                    
                    # Читаем запрос
                    try:
                        request = client.recv(4096).decode('utf-8', errors='ignore')
                        
                        # Определяем путь
                        path = "/"
                        if request.startswith('GET'):
                            lines = request.split('\n')
                            if lines:
                                parts = lines[0].split(' ')
                                if len(parts) > 1:
                                    path = parts[1]
                    except:
                        request = ""
                        path = "/"
                    
                    # Формируем ответ в зависимости от пути
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    if path == "/health" or path == "/ping":
                        response_body = f"""HTTP/1.1 200 OK
Content-Type: application/json
Access-Control-Allow-Origin: *

{{"status": "ok", "time": "{current_time}", "service": "funpay-cardinal", "port": {port}}}"""
                    
                    elif path == "/status":
                        response_body = f"""HTTP/1.1 200 OK
Content-Type: application/json
Access-Control-Allow-Origin: *

{{"status": "running", "platform": "koyeb", "port": {port}, "timestamp": "{current_time}"}}"""
                    
                    elif path == "/":
                        response_body = f"""HTTP/1.1 200 OK
Content-Type: text/html
Access-Control-Allow-Origin: *

<!DOCTYPE html>
<html>
<head><title>FunPay Cardinal</title></head>
<body>
<h1>FunPay Cardinal Active</h1>
<p>Status: <strong style="color: green;">RUNNING</strong></p>
<p>Port: {port}</p>
<p>Time: {current_time}</p>
<p>Platform: Koyeb</p>
</body>
</html>"""
                    
                    else:
                        response_body = f"""HTTP/1.1 200 OK
Content-Type: text/plain
Access-Control-Allow-Origin: *

FunPay Cardinal Active
Port: {port}
Time: {current_time}"""
                    
                    client.send(response_body.encode())
                    client.close()
                    
                    # Логируем запрос (но не слишком часто)
                    if random.random() < 0.1:  # 10% шанс логирования
                        print(f"[Koyeb:{port}] Request from {addr[0]}:{addr[1]} to {path}")
                        
                except Exception as e:
                    continue
        
        # Запускаем обработчик соединений
        threading.Thread(target=handle_connections, daemon=True).start()
        print(f"[Koyeb] Main server started on port {port}")
        return True
        
    except Exception as e:
        print(f"[Koyeb] Failed to start server on port {port}: {e}")
        return False

# ==================== СИСТЕМА ВНЕШНИХ ПИНГОВ ДЛЯ KOYEB ====================

def start_external_ping_service():
    """
    Делает внешние пинги каждые 4 минуты, чтобы Koyeb не засыпал
    Koyeb засыпает после 5 минут без трафика, поэтому пинги каждые 4 минуты
    """
    
    def ping_cycle():
        ping_count = 0
        last_successful_ping = time.time()
        
        while True:
            try:
                ping_count += 1
                current_time = datetime.now().strftime("%H:%M:%S")
                
                # 1. Пытаемся пингнуть себя через публичный URL
                # Получаем имя приложения из переменных окружения
                app_name = os.getenv("KOYEB_APP_NAME")
                if app_name:
                    try:
                        url = f"https://{app_name}.koyeb.app/health"
                        response = requests.get(url, timeout=10, headers={
                            'User-Agent': 'Koyeb-KeepAlive/1.0'
                        })
                        if response.status_code == 200:
                            print(f"[{current_time}] External ping #{ping_count}: SUCCESS (status: {response.status_code})")
                            last_successful_ping = time.time()
                            # Ждем 4 минуты до следующего пинга
                            time.sleep(240)
                            continue
                    except:
                        pass
                
                # 2. Если не получилось, пингуем localhost
                try:
                    response = requests.get(f"http://localhost:{KOYEB_PORT}/health", timeout=5)
                    if response.status_code == 200:
                        print(f"[{current_time}] Local ping #{ping_count}: SUCCESS")
                        last_successful_ping = time.time()
                except:
                    print(f"[{current_time}] Local ping #{ping_count}: FAILED")
                
                # 3. Делаем внешний запрос для интернет-активности
                try:
                    url = EXTERNAL_URLS[ping_count % len(EXTERNAL_URLS)]
                    response = requests.get(url, timeout=10)
                    print(f"[{current_time}] Internet ping #{ping_count}: {url} - {response.status_code}")
                except Exception as e:
                    print(f"[{current_time}] Internet ping #{ping_count}: FAILED - {e}")
                
                # Проверяем, не было ли успешных пингов слишком давно
                time_since_success = time.time() - last_successful_ping
                if time_since_success > 600:  # 10 минут без успешных пингов
                    print(f"[WARNING] No successful pings for {time_since_success:.0f} seconds!")
                
                # Ждем 4 минуты (240 секунд) до следующего пинга
                # Koyeb спит после 5 минут, поэтому 4 минуты безопасно
                time.sleep(240)
                
            except Exception as e:
                print(f"[PingService] Error: {e}")
                time.sleep(60)  # Ждем минуту при ошибке
    
    # Запускаем сервис пингов
    threading.Thread(target=ping_cycle, daemon=True).start()
    print(f"[Koyeb] External ping service started (interval: 4 minutes)")
    return True

# ==================== ДОПОЛНИТЕЛЬНЫЕ ПОРТЫ ДЛЯ НАДЕЖНОСТИ ====================

def start_backup_servers():
    """Запускает дополнительные серверы на других портах"""
    backup_ports = [8081, 8082, 8083]
    
    for port in backup_ports:
        threading.Thread(
            target=lambda p=port: start_koyeb_server(p),
            daemon=True
        ).start()
        time.sleep(0.5)  # Небольшая задержка между запусками
    
    print(f"[Koyeb] Backup servers started on ports: {backup_ports}")

# ==================== ИНИЦИАЛИЗАЦИЯ KOYEB СИСТЕМЫ ====================

def setup_koyeb_system():
    """
    Настраивает все системы для работы на Koyeb
    """
    print("=" * 60)
    print("KOYEB ANTI-SLEEP SYSTEM")
    print(f"Port: {KOYEB_PORT}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. Запускаем основной сервер на порту 8080
    if not start_koyeb_server(KOYEB_PORT):
        print("[ERROR] Failed to start main server!")
        return False
    
    # 2. Запускаем дополнительные серверы
    start_backup_servers()
    
    # 3. Запускаем сервис внешних пингов
    start_external_ping_service()
    
    # 4. Запускаем мониторинг
    def monitor():
        start_time = datetime.now()
        while True:
            uptime = datetime.now() - start_time
            hours = uptime.total_seconds() / 3600
            
            print("\n" + "=" * 50)
            print(f"KOYEB STATUS - Uptime: {hours:.1f} hours")
            print(f"Port: {KOYEB_PORT}")
            print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
            print("=" * 50 + "\n")
            
            time.sleep(300)  # Каждые 5 минут
    
    threading.Thread(target=monitor, daemon=True).start()
    
    print("[Koyeb] System initialized successfully!")
    print("[Koyeb] Endpoints available:")
    print(f"  - http://localhost:{KOYEB_PORT}/")
    print(f"  - http://localhost:{KOYEB_PORT}/health")
    print(f"  - http://localhost:{KOYEB_PORT}/status")
    print(f"  - http://localhost:{KOYEB_PORT}/ping")
    print("[Koyeb] External pings every 4 minutes")
    print("=" * 60)
    
    return True

# ==================== ЗАПУСК СИСТЕМЫ ====================

# Настраиваем систему Koyeb
setup_koyeb_system()

# Ждем немного для запуска всех серверов
time.sleep(2)

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

# ВАШ ОСТАЛЬНОЙ КОД БЕЗ ИЗМЕНЕНИЙ
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
