"""
Set a car balance before the classroom demonstration.

Usage:
    python set_initial_balance.py CAR_001 50
"""

import sys

import database


def main():
    if len(sys.argv) != 3:
        print("Usage: python set_initial_balance.py CAR_001 50")
        return

    car_id = sys.argv[1]
    balance = float(sys.argv[2])
    database.init_db()
    database.set_balance(car_id, balance)
    print(f"[OK] {car_id} balance set to {balance:.2f}")


if __name__ == "__main__":
    main()
