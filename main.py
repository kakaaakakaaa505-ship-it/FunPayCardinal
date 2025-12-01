import time
import socket
import threading
import requests
from pip._internal.cli.main import main
import sys
import os

def render_port_fix():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', 8080))
        sock.listen(5)
        
        def handle():
            while True:
                try:
                    client, addr = sock.accept()
                    # Простой HTTP ответ
                    response = b'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nOK'
                    client.send(response)
                    client.close()
                except:
                    continue
        
        threading.Thread(target=handle, daemon=True).start()
        print("Render port fix: HTTP server on port 8080")
    except Exception as e:
        print(f"Render port fix failed (non-critical): {e}")

# НОВЫЙ КОД ДЛЯ ПРЕДОТВРАЩЕНИЯ ЗАВИСАНИЯ НА RENDER
def keep_alive_server():
    """
    Запускает дополнительный HTTP-сервер для health checks
    """
    try:
        # Сервер на порту 8081 для health checks
        health_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        health_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        health_sock.bind(('0.0.0.0', 8081))
        health_sock.listen(5)
        
        def health_handler():
            while True:
                try:
                    client, addr = health_sock.accept()
                    # Читаем запрос
                    request = client.recv(1024).decode('utf-8', errors='ignore')
                    
                    # Формируем ответ
                    response_body = "ALIVE"
                    response = f"""HTTP/1.1 200 OK
Content-Type: text/plain
Content-Length: {len(response_body)}
Connection: close

{response_body}"""
                    
                    client.send(response.encode())
                    client.close()
                    print(f"[Keep-Alive] Health check from {addr[0]}")
                except Exception as e:
                    print(f"[Keep-Alive] Error: {e}")
                    continue
        
        threading.Thread(target=health_handler, daemon=True).start()
        print("Keep-Alive server started on port 8081")
    except Exception as e:
        print(f"Keep-Alive server failed: {e}")

def self_ping_service():
    """
    Фоновая служба для самопинга (если это основной инстанс)
    """
    def self_ping():
        # Ждем 10 минут перед первым пингом
        time.sleep(600)
        
        while True:
            try:
                # Пытаемся пингнуть себя через несколько портов
                ports = [8080, 8081]
                for port in ports:
                    try:
                        response = requests.get(f"http://localhost:{port}", timeout=5)
                        if response.status_code == 200:
                            print(f"[Self-Ping] Successfully pinged port {port}")
                    except:
                        pass
                
                # Ждем 8 минут до следующего пинга
                time.sleep(480)
            except Exception as e:
                print(f"[Self-Ping] Error: {e}")
                time.sleep(60)
    
    # Запускаем самопинг в фоне только если это основной процесс
    threading.Thread(target=self_ping, daemon=True).start()
    print("Self-ping service started")

def start_health_endpoint():
    """
    Запускает простой Flask/FastAPI-like endpoint для внешних мониторингов
    """
    try:
        from http.server import HTTPServer, BaseHTTPRequestHandler
        
        class HealthHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path in ['/', '/health', '/ping', '/status']:
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b'OK')
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def log_message(self, format, *args):
                # Отключаем стандартное логирование
                pass
        
        def run_health_server():
            server = HTTPServer(('0.0.0.0', 5000), HealthHandler)
            print(f"Health endpoint server started on port 5000")
            server.serve_forever()
        
        # Запускаем в отдельном потоке
        health_thread = threading.Thread(target=run_health_server, daemon=True)
        health_thread.start()
        
    except ImportError:
        print("HTTP server not available, using simple socket server")
        # Альтернатива если нет http.server
        try:
            health_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            health_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            health_sock.bind(('0.0.0.0', 5000))
            health_sock.listen(5)
            
            def simple_handler():
                while True:
                    try:
                        client, addr = health_sock.accept()
                        # Простой HTTP ответ для любого запроса
                        response = b'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nOK'
                        client.send(response)
                        client.close()
                    except:
                        continue
            
            threading.Thread(target=simple_handler, daemon=True).start()
            print("Simple health endpoint on port 5000")
        except:
            pass

def setup_render_anti_sleep():
    """
    Настраивает все системы против сна на Render
    """
    print("=" * 50)
    print("Setting up Render Anti-Sleep System")
    print("=" * 50)
    
    # 1. Запускаем основной порт фикс
    render_port_fix()
    
    # 2. Запускаем keep-alive сервер
    keep_alive_server()
    
    # 3. Запускаем health endpoint для внешних мониторингов
    start_health_endpoint()
    
    # 4. Запускаем самопинг (осторожно - может нарушать ToS)
    # Раскомментируйте если готовы к риску
    # self_ping_service()
    
    print("Render Anti-Sleep System initialized!")
    print("External monitoring endpoints:")
    print("  - http://localhost:8080 (main)")
    print("  - http://localhost:8081 (health)")
    print("  - http://localhost:5000 (health endpoint)")
    print("=" * 50)

# ЗАПУСКАЕМ СИСТЕМУ ПРОТИВ СНА
setup_render_anti_sleep()

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

# Остальной ваш код продолжается...
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

logo = """..."""  # Ваш логотип

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

print(f"{Style.RESET_ALL}{logo}")
print(f"{Fore.RED}{Style.BRIGHT}v{VERSION}{Style.RESET_ALL}\n")  # locale
print(f"{Fore.MAGENTA}{Style.BRIGHT}By {Fore.BLUE}{Style.BRIGHT}Woopertail, @sidor0912{Style.RESET_ALL}")
print(
    f"{Fore.MAGENTA}{Style.BRIGHT} * GitHub: {Fore.BLUE}{Style.BRIGHT}github.com/sidor0912/FunPayCardinal{Style.RESET_ALL}")
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

    logger.info(f"$GREENPID файл создан, PID процесса: {pid}")  # locale

directory = 'plugins'
for filename in os.listdir(directory):
    if filename.endswith(".py"):  # Проверяем, что файл имеет расширение .py
        filepath = os.path.join(directory, filename)  # Получаем полный путь к файлу
        with open(filepath, 'r', encoding='utf-8') as file:
            data = file.read()  # Читаем содержимое файла
        # Заменяем подстроку
        if '"<i>Разработчик:</i> " + CREDITS' in data or " lot.stars " in data or " lot.seller " in data:
            data = data.replace('"<i>Разработчик:</i> " + CREDITS', '"sidor0912"') \
                .replace(" lot.stars ", " lot.seller.stars ") \
                .replace(" lot.seller ", " lot.seller.username ")
            # Сохраняем изменения обратно в файл
            with open(filepath, 'w', encoding='utf-8') as file:
                file.write(data)

try:
    logger.info("$MAGENTAЗагружаю конфиг _main.cfg...")  # locale
    MAIN_CFG = cfg_loader.load_main_config("configs/_main.cfg")
    localizer = Localizer(MAIN_CFG["Other"]["language"])
    _ = localizer.translate

    logger.info("$MAGENTAЗагружаю конфиг auto_response.cfg...")  # locale
    AR_CFG = cfg_loader.load_auto_response_config("configs/auto_response.cfg")
    RAW_AR_CFG = cfg_loader.load_raw_auto_response_config("configs/auto_response.cfg")

    logger.info("$MAGENTAЗагружаю конфиг auto_delivery.cfg...")  # locale
    AD_CFG = cfg_loader.load_auto_delivery_config("configs/auto_delivery.cfg")
except excs.ConfigParseError as e:
    logger.error(e)
    logger.error("Завершаю программу...")  # locale
    time.sleep(5)
    sys.exit()
except UnicodeDecodeError:
    logger.error("Произошла ошибка при расшифровке UTF-8. Убедитесь, что кодировка файла = UTF-8, "
                 "а формат конца строк = LF.")  # locale
    logger.error("Завершаю программу...")  # locale
    time.sleep(5)
    sys.exit()
except:
    logger.critical("Произошла непредвиденная ошибка.")  # locale
    logger.warning("TRACEBACK", exc_info=True)
    logger.error("Завершаю программу...")  # locale
    time.sleep(5)
    sys.exit()

localizer = Localizer(MAIN_CFG["Other"]["language"])

try:
    Cardinal(MAIN_CFG, AD_CFG, AR_CFG, RAW_AR_CFG, VERSION).init().run()
except KeyboardInterrupt:
    logger.info("Завершаю программу...")  # locale
    sys.exit()
except:
    logger.critical("При работе Кардинала произошла необработанная ошибка.")  # locale
    logger.warning("TRACEBACK", exc_info=True)
    logger.critical("Завершаю программу...")  # locale
    time.sleep(5)
    sys.exit()
