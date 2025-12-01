# render_fix.py
import socket
import threading
import time

print("Starting Render fix...")

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(('0.0.0.0', 8080))
sock.listen(1)
print("Socket created on port 8080")

def handle():
    while True:
        conn, addr = sock.accept()
        conn.send(b'HTTP/1.1 200 OK\r\n\r\nOK')
        conn.close()

threading.Thread(target=handle, daemon=True).start()
time.sleep(3)
print("Render fix applied successfully")
