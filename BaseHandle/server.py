from Logging import Logger
from PyQt5.QtCore import QObject, pyqtSignal
import time
import socket
import threading
from base_connect_server import AbstractServer


class Server(AbstractServer):
    def __init__(self):
        super().__init__()
        self.server_logger = Logger('Server')  # Dùng instance logger

    def start_server(self, ip='127.0.0.1', port=8000):
        try:
            self.ip = ip
            self.port = port
            self.server_logger.info('Khởi động Server')
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.ip, self.port))
            self.server_socket.listen()
            self.is_connected = True
            threading.Thread(target=self.accept_client, daemon=True).start()
        except Exception as e:
            self.is_connected = False
            self.server_logger.error(e)

    def accept_client(self):
        while self.is_connected:
            try:
                self.client_socket, self.client_address = self.server_socket.accept()
                if not self.is_connected:
                    break
                else:
                    threading.Thread(target=self.loop_recv_client, args=(self.client_socket,), daemon=True).start()
                self.server_logger.info(f'{self.client_address} connected')
            except Exception as e:
                if self.is_connected:
                    self.server_logger.error(e)
                break

    def stop_server(self):
        try:
            self.is_connected = False
            if self.server_socket:
                self.server_socket.close()
                self.server_logger.info('Đã ngắt kết nối')
        except Exception as e:
            self.server_logger.error(e)

    def loop_recv_client(self, conn: socket.socket):
        msg = conn.recv(1024).decode().strip()
        if msg == "check":
            self.triggerOn.emit()
            time.sleep(0.01)
        conn.close()