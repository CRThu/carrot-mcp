# /// script
# requires-python = ">=3.10"
# dependencies = ["pyserial"]
# ///

import serial
import time

PORT = "COM18"
BAUD = 115200

def main():
    ser = serial.Serial(PORT, BAUD, timeout=1)
    print(f"Opened {PORT} @ {BAUD}")
    try:
        while True:
            raw = ser.read(1)
            if not raw:
                continue
            # Check if more bytes follow (short read timeout)
            time.sleep(0.05)
            raw += ser.read(ser.in_waiting)
            print(f"RX: {raw.hex(' ').upper()}")

            # Single byte 0x55 -> reply 0xAA
            if raw == b'\x55':
                ser.write(b'\xaa')
                print("TX: AA")
            # "Hello" -> "World"
            elif raw == b'Hello':
                ser.write(b'World')
                print("TX: World")
            # "FF XX" pattern -> reply XX
            elif len(raw) == 2 and raw[0] == 0xFF:
                ser.write(bytes([raw[1], 0x01]))
                print(f"TX.A: {hex(raw[1])}")
                time.sleep(1)
                ser.write(bytes([raw[1], 0x02]))
                print(f"TX.B: {hex(raw[1])}")
                time.sleep(1)
                ser.write(bytes([raw[1], 0x03]))
                print(f"TX.C: {hex(raw[1])}")
                time.sleep(1)
                ser.write(bytes([raw[1], 0x04]))
                print(f"TX.D: {hex(raw[1])}")
                time.sleep(1)
                ser.write(bytes([raw[1], 0x05]))
                print(f"TX.E: {hex(raw[1])}")
            else:
                print("RX not matched, skip")
    except KeyboardInterrupt:
        print("\nStopped")
    finally:
        ser.close()

if __name__ == "__main__":
    main()
