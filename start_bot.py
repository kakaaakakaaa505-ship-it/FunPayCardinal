#!/usr/bin/env python3
import socket
import threading
import time
import subprocess
import sys

print("=== Starting FunPay Cardinal Bot ===")

# 1. Запускаем фиктивный HTTP сервер для Render
def start_dummy_server():
    """Создаёт фиктивный HTTP сервер на порту 8080"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', 8080))
        sock.listen(5)
        print("✓ Dummy HTTP server started on port 8080")
        
        def handle_connections():
            while True:
                client, addr = sock.accept()
                client.send(b'HTTP/1.1 200 OK\r\n\r\nBot is running')
                client.close()
        
        threading.Thread(target=handle_connections, daemon=True).start()
        return True
    except Exception as e:
        print(f"✗ Failed to start dummy server: {e}")
        return False

# 2. Запускаем фиктивный сервер
if start_dummy_server():
    print("✓ Render port fix applied")
    
    # 3. Даём время Render проверить порт
    time.sleep(3)
    
    # 4. Запускаем основного бота
    print("✓ Starting main bot...")
    print("=" * 50)
    
    # Импортируем и запускаем cardinal.py
    try:
        import cardinal
        print("✓ Bot imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import bot: {e}")
        sys.exit(1)
else:
    print("✗ Port fix failed, but trying to start bot anyway...")
