# AI Parking System

An intelligent car park management system for the Automation and Mechatronics coursework.

The system uses Arduino for the physical devices and Python for camera recognition, database management, payment logic, and the dashboard.

## Hardware

- Arduino Uno with V5 expansion board
- 2 USB cameras: entry and exit
- 5 parking spot sensors
- 2 servo motors: entry gate and exit gate
- LCD1602 I2C display
- I2C RC522 RFID reader at the exit
- 5 RFID white cards, one card per car

## Software Environment

Tested with:

- Windows
- Python 3.9.13
- Arduino IDE

Install Python dependencies:

```powershell
cd "D:\Sussex Course materials\Automation and Mechatronics\Code\Python_code"
python -m pip install -r requirements.txt
```

The required Python packages are:

```text
opencv-python
numpy
pyserial
```

## Project Structure

```text
Code/
├─ Arduino_code/
│  ├─ i2c_scanner/i2c_scanner.ino
│  └─ parking/parking.ino
└─ Python_code/
   ├─ main.py
   ├─ database.py
   ├─ enroll_rfid_cards.py
   ├─ set_initial_balance.py
   ├─ test_camera_indices.py
   ├─ test_rfid_topup.py
   └─ parking.db
```

## Setup Steps

### 1. Check I2C Addresses

Upload this Arduino sketch first:

```text
Code/Arduino_code/i2c_scanner/i2c_scanner.ino
```

Open the Arduino Serial Monitor at `115200` baud.

The LCD is usually `0x27`, and the RFID reader is usually `0x28`.

If the addresses are different, update them in:

```text
Code/Arduino_code/parking/parking.ino
```

### 2. Upload Arduino Main Code

Upload:

```text
Code/Arduino_code/parking/parking.ino
```

### 3. Enrol RFID Cards

Close the Arduino Serial Monitor before running Python scripts.

```powershell
cd "D:\Sussex Course materials\Automation and Mechatronics\Code\Python_code"
python enroll_rfid_cards.py COM15
```

Follow the prompts and scan one white card for each car:

- CAR_001
- CAR_002
- CAR_003
- CAR_004
- CAR_005

### 4. Set Initial Balance

Example:

```powershell
python set_initial_balance.py CAR_001 50
python set_initial_balance.py CAR_002 50
python set_initial_balance.py CAR_003 50
python set_initial_balance.py CAR_004 50
python set_initial_balance.py CAR_005 50
```

### 5. Check Camera Indexes

```powershell
python test_camera_indices.py
```

If needed, update these values in `main.py`:

```python
ENTRY_CAMERA_INDEX = 0
EXIT_CAMERA_INDEX = 2
```

### 6. Run the System

```powershell
python main.py
```

Press `Q` to quit the dashboard.

## Useful Test Commands

Test RFID top-up only:

```powershell
python test_rfid_topup.py COM15
```

Set one car balance:

```powershell
python set_initial_balance.py CAR_001 0
```

Run the main system:

```powershell
python main.py
```

## Main Logic

- Entry camera scans the car QR code.
- If parking spaces are available, the entry gate opens.
- Parking time is stored in the SQLite database.
- Exit camera scans the car QR code.
- If the balance is enough, the parking fee is deducted and the exit gate opens.
- If the balance is not enough, the yellow warning light turns on.
- The user scans the RFID card at the exit to top up 20 yuan.
- After top-up, the system waits 3 seconds, retries payment, and opens the exit gate if payment succeeds.
- When all spaces are occupied, the red warning light stays on.

## Important Parameters

In `Python_code/main.py`:

```python
SERIAL_PORT = "COM15"
RECHARGE_AMOUNT = 20.0
EXIT_RETRY_DELAY = 3.0
ENTRY_CAMERA_INDEX = 0
EXIT_CAMERA_INDEX = 2
```

In `Arduino_code/parking/parking.ino`:

```cpp
const byte LCD_ADDRESS = 0x27;
const byte RFID_ADDRESS = 0x28;
```

## Notes

- Do not run `main.py` and `test_rfid_topup.py` at the same time because both need the same Arduino serial port.
- Close the Arduino Serial Monitor before running Python scripts.
- If the Arduino port is not `COM15`, replace `COM15` with the correct port.
- The SQLite database file is `Python_code/parking.db`.
