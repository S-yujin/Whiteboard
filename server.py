import socket
import threading
import json

class WhiteboardServer:
    def __init__(self, host='127.0.0.1', port=5000):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((host, port))
        self.server.listen(5)
        self.clients = []
        print(f"서버 시작: {host}:{port}")

    def broadcast(self, message, sender_socket):
        for client in self.clients:
            try:
                client.send(message.encode('utf-8'))
            except:
                self.remove_client(client)

    def remove_client(self, client):
        if client in self.clients:
            self.clients.remove(client)
            print("클라이언트 연결 종료")

    def handle_client(self, client_socket):
        while True:
            try:
                data = client_socket.recv(4096).decode('utf-8')
                if not data: break
                # 모든 클라이언트에게 데이터 전달
                self.broadcast(data, client_socket)
            except:
                break
        self.remove_client(client_socket)

    def run(self):
        try:
            while True:
                client_sock, addr = self.server.accept()
                print(f"연결됨: {addr}")
                self.clients.append(client_sock)
                threading.Thread(target=self.handle_client, args=(client_sock,), daemon=True).start()
        except KeyboardInterrupt:
            print("서버 종료")

if __name__ == "__main__":
    WhiteboardServer().run()