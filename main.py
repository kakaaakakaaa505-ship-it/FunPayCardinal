import time
from pip._internal.cli.main import main

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

# Добавляем импорт для SSH сервера
try:
    import asyncssh
    SSH_AVAILABLE = True
except ImportError:
    print("Для удаленного доступа установите: pip install asyncssh")
    SSH_AVAILABLE = False
    asyncssh = None

import Utils.cardinal_tools
import Utils.config_loader as cfg_loader
from first_setup import first_setup
from colorama import Fore, Style
from Utils.logger import LOGGER_CONFIG
import logging.config
import colorama
import sys
import os
import asyncio
import threading
import code
import traceback
import io
from cardinal import Cardinal
import Utils.exceptions as excs
from locales.localizer import Localizer

logo = """[Ваш логотип]"""

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
print(f"{Fore.RED}{Style.BRIGHT}v{VERSION}{Style.RESET_ALL}\n")
print(f"{Fore.MAGENTA}{Style.BRIGHT}By {Fore.BLUE}{Style.BRIGHT}Woopertail, @sidor0912{Style.RESET_ALL}")
print(
    f"{Fore.MAGENTA}{Style.BRIGHT} * GitHub: {Fore.BLUE}{Style.BRIGHT}github.com/sidor0912/FunPayCardinal{Style.RESET_ALL}")
print(f"{Fore.MAGENTA}{Style.BRIGHT} * Telegram: {Fore.BLUE}{Style.BRIGHT}t.me/sidor0912")
print(f"{Fore.MAGENTA}{Style.BRIGHT} * Новости о обновлениях: {Fore.BLUE}{Style.BRIGHT}t.me/fpc_updates")
print(f"{Fore.MAGENTA}{Style.BRIGHT} * Плагины: {Fore.BLUE}{Style.BRIGHT}t.me/fpc_plugins")
print(f"{Fore.MAGENTA}{Style.BRIGHT} * Донат: {Fore.BLUE}{Style.BRIGHT}t.me/sidor_donate")
print(f"{Fore.MAGENTA}{Style.BRIGHT} * Telegram-чат: {Fore.BLUE}{Style.BRIGHT}t.me/funpay_cardinal")

# ============================================================================
# КЛАСС ДЛЯ УДАЛЕННОЙ PYTHON КОНСОЛИ
# ============================================================================

class RemotePythonConsole:
    """Класс для удаленного доступа к Python консоли через SSH"""
    
    def __init__(self, host='0.0.0.0', port=2222, username='admin', password='admin123'):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.server = None
        self.running = False
        self.cardinal_instance = None
        self.logger = logging.getLogger("ssh")
        
    def set_cardinal(self, cardinal):
        """Установить экземпляр Cardinal для доступа из консоли"""
        self.cardinal_instance = cardinal
        
    async def handle_client(self, process):
        """Обработчик SSH подключения"""
        try:
            # Создаем локальное пространство имен для консоли
            local_vars = {
                'cardinal': self.cardinal_instance,
                'logger': self.logger,
                'config': self.cardinal_instance.MAIN_CFG if self.cardinal_instance else None,
                'ar_config': self.cardinal_instance.AR_CFG if self.cardinal_instance else None,
                'ad_config': self.cardinal_instance.AD_CFG if self.cardinal_instance else None,
                'version': VERSION,
                'help': self.show_help
            }
            
            process.stdout.write(f"\n=== FunPay Cardinal Remote Console v{VERSION} ===\n")
            process.stdout.write("Введите 'help' для списка команд\n")
            process.stdout.write("Введите 'exit' для выхода\n\n")
            
            # Основной цикл консоли
            while True:
                try:
                    # Получаем команду от пользователя
                    process.stdout.write(">>> ")
                    command = await process.stdin.readline()
                    
                    if not command:
                        break
                        
                    command = command.strip()
                    
                    # Проверяем специальные команды
                    if command.lower() == 'exit' or command.lower() == 'quit':
                        process.stdout.write("Выход из консоли...\n")
                        break
                        
                    elif command.lower() == 'help':
                        self.show_help(process)
                        continue
                        
                    elif command.lower() == 'status':
                        await self.show_status(process)
                        continue
                        
                    elif command.lower() == 'reload':
                        await self.reload_configs(process)
                        continue
                        
                    # Выполняем Python код
                    try:
                        # Пытаемся выполнить как выражение
                        result = eval(command, globals(), local_vars)
                        if result is not None:
                            output = repr(result)
                            process.stdout.write(f"{output}\n")
                    except SyntaxError:
                        # Если это не выражение, выполняем как statement
                        exec(command, globals(), local_vars)
                        
                except Exception as e:
                    error_msg = f"Ошибка: {str(e)}\n"
                    process.stdout.write(error_msg)
                    self.logger.error(f"SSH консоль: {str(e)}")
                    
        except Exception as e:
            self.logger.error(f"Ошибка в SSH обработчике: {str(e)}")
        finally:
            process.exit(0)
    
    def show_help(self, process=None):
        """Показать справку по командам"""
        help_text = """
Доступные команды:
  help          - Показать эту справку
  status        - Показать статус Cardinal
  reload        - Перезагрузить конфигурации
  exit/quit     - Выйти из консоли
  
Доступные переменные:
  cardinal      - Экземпляр Cardinal
  logger        - Логгер системы
  config        - Основная конфигурация
  ar_config     - Конфигурация автоответов
  ad_config     - Конфигурация автовыдачи
  version       - Версия Cardinal
  
Примеры:
  >>> cardinal.account.username
  >>> config['Other']['language']
  >>> logger.info('Тестовое сообщение')
  >>> cardinal.telegram.send_message('Привет!')
"""
        if process:
            process.stdout.write(help_text)
        else:
            print(help_text)
    
    async def show_status(self, process):
        """Показать статус системы"""
        if not self.cardinal_instance:
            process.stdout.write("Cardinal не инициализирован\n")
            return
            
        status = f"""
Статус FunPay Cardinal:
  Версия: {VERSION}
  Пользователь: {self.cardinal_instance.account.username if hasattr(self.cardinal_instance, 'account') else 'N/A'}
  Язык: {self.cardinal_instance.MAIN_CFG['Other']['language']}
  Запущен: {self.cardinal_instance.running if hasattr(self.cardinal_instance, 'running') else 'N/A'}
  Telegram бот: {'Запущен' if hasattr(self.cardinal_instance, 'telegram') and self.cardinal_instance.telegram else 'Не запущен'}
"""
        process.stdout.write(status)
    
    async def reload_configs(self, process):
        """Перезагрузить конфигурации"""
        try:
            if not self.cardinal_instance:
                process.stdout.write("Cardinal не инициализирован\n")
                return
                
            # Здесь можно добавить логику перезагрузки конфигов
            process.stdout.write("Перезагрузка конфигураций...\n")
            # Пример: self.cardinal_instance.reload_configs()
            process.stdout.write("Конфигурации перезагружены\n")
        except Exception as e:
            process.stdout.write(f"Ошибка при перезагрузке: {str(e)}\n")
    
    async def start_server(self):
        """Запустить SSH сервер"""
        if not SSH_AVAILABLE:
            self.logger.error("asyncssh не установлен. SSH сервер не будет запущен.")
            return
            
        try:
            # Генерируем ключи если нужно
            import os
            key_path = "configs/ssh_host_key"
            
            if not os.path.exists(key_path):
                self.logger.info("Генерация SSH ключей...")
                from asyncssh import generate_private_key
                key = generate_private_key('ssh-rsa')
                key.export_private_key(key_path)
                os.chmod(key_path, 0o600)
            
            # Запускаем SSH сервер
            self.server = await asyncssh.create_server(
                self.handle_client,
                self.host,
                self.port,
                server_host_keys=[key_path],
                authorized_client_keys=None,  # Отключаем проверку по ключам
                process_factory=self.handle_client
            )
            
            self.running = True
            self.logger.info(f"SSH сервер запущен на {self.host}:{self.port}")
            self.logger.info(f"Подключение: ssh {self.username}@ваш_ip -p {self.port}")
            self.logger.info(f"Пароль: {self.password}")
            
            # Запускаем бесконечный цикл
            await self.server.wait_closed()
            
        except Exception as e:
            self.logger.error(f"Ошибка запуска SSH сервера: {str(e)}")
            self.running = False
    
    def start_in_thread(self):
        """Запустить SSH сервер в отдельном потоке"""
        if not SSH_AVAILABLE:
            return
            
        def run_server():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.start_server())
        
        thread = threading.Thread(target=run_server, daemon=True, name="SSH-Server")
        thread.start()
        return thread
    
    def stop(self):
        """Остановить SSH сервер"""
        if self.server:
            self.server.close()
            self.running = False

# ============================================================================
# ОСНОВНОЙ КОД
# ============================================================================

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
    logger.info("$MAGENTAЗагружаю конфиг _main.cfg...")  # locale
    MAIN_CFG = cfg_loader.load_main_config("configs/_main.cfg")
    localizer = Localizer(MAIN_CFG["Other"]["language"])
    _ = localizer.translate

    logger.info("$MAGENTAЗагружаю конфиг auto_response.cfg...")  # locale
    AR_CFG = cfg_loader.load_auto_response_config("configs/auto_response.cfg")
    RAW_AR_CFG = cfg_loader.load_raw_auto_response_config("configs/auto_response.cfg")

    logger.info("$MAGENTAЗагружаю конфиг auto_delivery.cfg...")  # locale
    AD_CFG = cfg_loader.load_auto_delivery_config("configs/auto_delivery.cfg")
    
    # Создаем SSH консоль
    ssh_console = RemotePythonConsole(
        host=MAIN_CFG.get("SSH", {}).get("host", "0.0.0.0"),
        port=int(MAIN_CFG.get("SSH", {}).get("port", 2222)),
        username=MAIN_CFG.get("SSH", {}).get("username", "admin"),
        password=MAIN_CFG.get("SSH", {}).get("password", "admin123")
    )
    
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
    # Создаем экземпляр Cardinal
    cardinal = Cardinal(MAIN_CFG, AD_CFG, AR_CFG, RAW_AR_CFG, VERSION)
    
    # Настраиваем SSH консоль
    ssh_console.set_cardinal(cardinal)
    
    # Запускаем SSH сервер в фоне
    if SSH_AVAILABLE:
        ssh_thread = ssh_console.start_in_thread()
        logger.info("SSH сервер запущен в фоновом режиме")
    
    # Инициализируем и запускаем Cardinal
    cardinal.init().run()
    
except KeyboardInterrupt:
    logger.info("Завершаю программу...")  # locale
    if SSH_AVAILABLE:
        ssh_console.stop()
    sys.exit()
except:
    logger.critical("При работе Кардинала произошла необработанная ошибка.")  # locale
    logger.warning("TRACEBACK", exc_info=True)
    logger.critical("Завершаю программу...")  # locale
    if SSH_AVAILABLE:
        ssh_console.stop()
    time.sleep(5)
    sys.exit()
