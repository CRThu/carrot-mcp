# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

import socket
import threading

HOST = "127.0.0.1"
PORT = 9999

def handle_client(conn, addr):
    print(f"Connected: {addr}")
    with conn:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            print(f"RX: {data.hex(' ').upper()}")
            conn.sendall(data)
            print(f"TX: {data.hex(' ').upper()}")
    print(f"Disconnected: {addr}")

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PORT))
        srv.listen(5)
        print(f"TCP echo listening on {HOST}:{PORT}")
        while True:
            conn, addr = srv.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()
