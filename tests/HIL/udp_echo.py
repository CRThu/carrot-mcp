# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

import socket

HOST = "127.0.0.1"
PORT = 9998

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as srv:
        srv.bind((HOST, PORT))
        print(f"UDP echo listening on {HOST}:{PORT}")
        while True:
            data, addr = srv.recvfrom(1024)
            print(f"RX from {addr}: {data.hex(' ').upper()}")
            srv.sendto(data, addr)
            print(f"TX to {addr}: {data.hex(' ').upper()} (echo)")

if __name__ == "__main__":
    main()
