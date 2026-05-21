"""
Test RFID top-up without opening cameras.

Usage:
    python test_rfid_topup.py COM15

Keep parking.ino running on the Arduino. Each bound white card scan adds
RECHARGE_AMOUNT yuan to the linked car and prints the new balance.
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
RECHARGE_AMOUNT = 20.0


def print_balances():
    print("\nCurrent balances:")
    for car_id in ["CAR_001", "CAR_002", "CAR_003", "CAR_004", "CAR_005"]:
        print(f"  {car_id}: {database.get_balance(car_id):.2f}")


def main():
    if serial is None:
        raise RuntimeError("pyserial is not installed. Install it with: python -m pip install pyserial")

    port = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PORT
    database.init_db()
    print_balances()

    with serial.Serial(port, BAUDRATE, timeout=0.2) as ser:
        time.sleep(2)
        print(f"\n[INFO] Connected to Arduino on {port}.")
        print("[INFO] Scan a bound white card on the EXIT RFID reader. Press Ctrl+C to stop.\n")

        while True:
            raw_line = ser.readline().decode("utf-8", errors="ignore").strip()
            if not raw_line:
                continue

            if raw_line.startswith("RFID:EXIT:"):
                uid = raw_line.split(":", 2)[2]
                ok, car_id, new_balance = database.top_up(uid, RECHARGE_AMOUNT)
                if ok:
                    print(f"[OK] {car_id} +{RECHARGE_AMOUNT:.2f}, new balance: {new_balance:.2f}")
                else:
                    print(f"[WARN] Unknown card UID {uid}. Run enroll_rfid_cards.py first.")
            elif raw_line.startswith("SYSTEM:") or raw_line.startswith("SPOTS:"):
                continue
            else:
                print(f"[ARDUINO] {raw_line}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[STOP] RFID top-up test stopped.")
