"""
Bind five RFID white cards to CAR_001 ... CAR_005.

Run after uploading parking.ino and opening the correct serial port:
    python enroll_rfid_cards.py COM15
"""

import sys
import time

import database

try:
    import serial
except ImportError:
    serial = None


DEFAULT_PORT = "COM15"
BAUDRATE = 115200
CAR_IDS = ["CAR_001", "CAR_002", "CAR_003", "CAR_004", "CAR_005"]


def wait_for_uid(ser):
    while True:
        raw_line = ser.readline().decode("utf-8", errors="ignore").strip()
        if raw_line:
            print(f"[ARDUINO] {raw_line}")
        if raw_line.startswith("RFID:EXIT:"):
            return raw_line.split(":", 2)[2]


def main():
    if serial is None:
        raise RuntimeError("pyserial is not installed. Install it with: pip install pyserial")

    port = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PORT
    database.init_db()

    with serial.Serial(port, BAUDRATE, timeout=0.2) as ser:
        time.sleep(2)
        print(f"[INFO] Connected to Arduino on {port}.")
        for car_id in CAR_IDS:
            input(f"\nPlace the white card for {car_id} on the EXIT RFID reader, then press Enter...")
            uid = database.normalize_rfid_uid(wait_for_uid(ser))
            database.link_rfid_to_car(car_id, uid)
            print(f"[OK] {car_id} bound to RFID UID {uid}")

    print("\n[DONE] All cards have been enrolled.")


if __name__ == "__main__":
    main()
