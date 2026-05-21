import time

import cv2
import numpy as np

try:
    import serial
except ImportError:
    serial = None

import database
from vision_module import QRScanner


SERIAL_PORT = "COM15"
BAUDRATE = 115200
COOLDOWN_PERIOD = 10
RECHARGE_AMOUNT = 20.0
EXIT_RETRY_DELAY = 3.0
WINDOW_NAME = "AI Parking Dashboard"
ENTRY_CAMERA_INDEX = 0
EXIT_CAMERA_INDEX = 2
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 15
QR_SCAN_INTERVAL = 0.45


database.init_db()
entry_scanner = QRScanner()
exit_scanner = QRScanner()

try:
    if serial is None:
        raise RuntimeError("pyserial is not installed")
    ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=0.1)
    print(f"[INFO] Serial {SERIAL_PORT} connected.")
except Exception as error:
    print(f"[WARN] Serial Error: {error}. Running in simulation mode.")
    ser = None


def init_camera(index):
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(f"[ERROR] Camera {index} is not available.")
        return None
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def create_placeholder(title, message, accent_color):
    frame = np.full((315, 560, 3), (28, 30, 36), dtype=np.uint8)
    cv2.rectangle(frame, (0, 0), (559, 314), accent_color, 2)
    cv2.putText(frame, title, (24, 46), cv2.FONT_HERSHEY_SIMPLEX, 0.95, (245, 245, 245), 2)
    cv2.putText(frame, message, (24, 164), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (180, 180, 180), 2)
    cv2.putText(frame, "Check camera connection", (24, 198),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (120, 120, 120), 1)
    return frame


def send_serial(command):
    if ser:
        ser.write(f"{command}\n".encode("utf-8"))


def set_lcd(line1, line2=""):
    send_serial(f"LCD:{line1[:16]}|{line2[:16]}")


def draw_panel(canvas, pos, title, status, frame, color):
    x, y = pos
    panel = canvas[y:y+460, x:x+600]
    frame_resized = cv2.resize(frame, (560, 315)) if frame is not None else np.zeros((315, 560, 3), dtype=np.uint8)
    panel[104:419, 15:575] = frame_resized
    cv2.putText(panel, title, (20, 45), cv2.FONT_HERSHEY_DUPLEX, 1.2, (255, 255, 255), 2)
    cv2.putText(panel, status, (20, 90), cv2.FONT_HERSHEY_DUPLEX, 0.7, color, 1)


def build_dashboard(entry_frame, exit_frame, entry_status, exit_status, system_status):
    canvas = np.full((760, 1280, 3), (18, 20, 26), dtype=np.uint8)

    cv2.rectangle(canvas, (0, 0), (1279, 88), (24, 27, 34), -1)
    cv2.putText(canvas, "AI Parking Control Center", (36, 52),
                cv2.FONT_HERSHEY_SIMPLEX, 1.1, (245, 245, 245), 3)
    cv2.putText(canvas, time.strftime("%Y-%m-%d %H:%M:%S"), (930, 52),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (180, 180, 180), 2)

    draw_panel(canvas, (36, 118), "Entry Camera", entry_status, entry_frame, (72, 201, 176))
    draw_panel(canvas, (654, 118), "Exit Camera", exit_status, exit_frame, (255, 166, 77))

    cv2.rectangle(canvas, (36, 545), (1244, 705), (28, 32, 40), -1)
    cv2.rectangle(canvas, (36, 545), (1244, 705), (55, 60, 72), 2)
    cv2.putText(canvas, "System Status", (58, 590), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (245, 245, 245), 2)
    cv2.putText(canvas, f"Available Spots: {database.get_available_spots()}", (58, 640),
                cv2.FONT_HERSHEY_SIMPLEX, 0.85, (72, 201, 176), 2)
    cv2.putText(canvas, f"Gate State: {system_status}", (58, 680),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (220, 220, 220), 2)
    cv2.putText(canvas, "Press Q to quit", (1010, 680),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (150, 150, 150), 2)

    return canvas


def try_exit_payment(car_id, now):
    global exit_timer, lcd_lock_until, yellow_led_off_time, exit_status, system_status, pending_exit_car

    if not database.is_car_parked(car_id):
        exit_status = f"IGNORED: {car_id} NOT IN"
        set_lcd(car_id, "Not parked")
        lcd_lock_until = now + 4
        return False

    current_fee = database.calculate_current_fee(car_id)
    if database.deduct_fee(car_id, current_fee):
        database.complete_exit(car_id, current_fee)
        send_serial("B")
        set_lcd(car_id, f"Fee:{current_fee} Paid")
        send_serial("y")
        exit_timer = now + 4
        yellow_led_off_time = 0
        lcd_lock_until = now + 4
        pending_exit_car = None
        exit_status = f"EXIT: {car_id} Paid {current_fee}"
        system_status = f"{car_id} exit paid"
        print(f"[EXIT] {car_id} 扣费成功: {current_fee}元，放行。")
        return True

    pending_exit_car = car_id
    send_serial("Y")
    set_lcd(car_id, "Low Bal: Tap")
    yellow_led_off_time = now + 30
    lcd_lock_until = now + 5
    exit_status = f"FAILED: {car_id} NEED RFID"
    system_status = f"{car_id} needs top-up"
    print(f"[EXIT REJECTED] {car_id} 余额不足，费用: {current_fee}。请在出口刷白卡充值。")
    return False


def handle_exit_rfid(uid, now):
    global exit_status, system_status, lcd_lock_until, pending_exit_car, scheduled_exit_retry

    ok, card_car_id, new_balance = database.top_up(uid, RECHARGE_AMOUNT)
    if not ok:
        send_serial("Y")
        set_lcd("Unknown RFID", "Bind card first")
        lcd_lock_until = now + 5
        exit_status = "RFID UNKNOWN"
        system_status = "RFID card not bound"
        print(f"[RFID] 未绑定白卡: {uid}")
        return

    print(f"[RFID] {card_car_id} 充值 {RECHARGE_AMOUNT} 元，新余额 {new_balance:.2f} 元。")

    if pending_exit_car and card_car_id != pending_exit_car:
        send_serial("Y")
        set_lcd(card_car_id, "Wrong card")
        lcd_lock_until = now + 5
        exit_status = f"RFID WRONG: {card_car_id}"
        system_status = f"Waiting for {pending_exit_car} card"
        return

    set_lcd(card_car_id, f"Bal:{new_balance:.2f}")
    lcd_lock_until = now + 3
    exit_status = f"TOPUP: {card_car_id} {new_balance:.2f}"
    system_status = f"{card_car_id} topped up"

    if pending_exit_car == card_car_id:
        scheduled_exit_retry = now + EXIT_RETRY_DELAY
        set_lcd(card_car_id, "Wait 3 sec")
        exit_status = f"TOPUP OK: {card_car_id}"
        system_status = f"{card_car_id} retry in 3s"


def handle_serial_line(raw_line, now):
    global last_spot_states, lcd_lock_until, system_status

    if raw_line.startswith("SPOTS:"):
        current_states = raw_line.split(":", 1)[1].split(",")
        if current_states != last_spot_states:
            for i, state in enumerate(current_states):
                database.update_spot(i + 1, int(state))
            last_spot_states = current_states

        available = database.get_available_spots()
        if available <= 0:
            send_serial("R")
        else:
            send_serial("r")

        if now > lcd_lock_until:
            system_status = f"Spots: {available}"
            msg = "Parking Full!" if available <= 0 else f"Available: {available}"
            sub_msg = "No Vacancy" if available <= 0 else "Spots Free"
            set_lcd(msg, sub_msg)
        return

    if raw_line.startswith("RFID:EXIT:"):
        uid = raw_line.split(":", 2)[2]
        handle_exit_rfid(uid, now)


cap_entry = init_camera(ENTRY_CAMERA_INDEX)
cap_exit = init_camera(EXIT_CAMERA_INDEX)

entry_display = create_placeholder("Entry Camera", "No camera signal", (72, 201, 176))
exit_display = create_placeholder("Exit Camera", "No camera signal", (255, 166, 77))

entry_timer = 0
exit_timer = 0
lcd_lock_until = 0
red_led_off_time = 0
yellow_led_off_time = 0
pending_exit_car = None
scheduled_exit_retry = 0
cooldowns = {}
last_spot_states = ["0", "0", "0", "0", "0"]
last_entry_scan_time = 0
last_exit_scan_time = 0

entry_status = "Scanning..."
exit_status = "Scanning..."
system_status = "System Running"

print("[SYSTEM] Parking system running. Exit RFID top-up logic active.")

while True:
    now = time.time()

    if ser:
        try:
            while ser.in_waiting > 0:
                line = ser.readline().decode("utf-8", errors="ignore").strip()
                if line:
                    handle_serial_line(line, now)
        except Exception as e:
            print(f"Serial Read Error: {e}")

    # 入口逻辑：识别车辆二维码，有空位就开入口闸；按用户要求不做重复入场拦截。
    if cap_entry:
        ret_en, frame_en = cap_entry.read()
        if ret_en:
            if now - last_entry_scan_time >= QR_SCAN_INTERVAL:
                last_entry_scan_time = now
                found_cars_en = entry_scanner.scan_and_annotate(frame_en)
                for car_id in found_cars_en:
                    if car_id not in cooldowns or (now - cooldowns[car_id] > COOLDOWN_PERIOD):
                        available_spots = database.get_available_spots()

                        if available_spots > 0:
                            send_serial("A")
                            database.start_session(car_id)
                            entry_timer = now + 4
                            entry_status = f"ENTER: {car_id}"
                            print(f"[SYSTEM] {car_id} 已进入，计费开始。")
                        else:
                            send_serial("R")
                            set_lcd(car_id, "Full: No Entry")
                        lcd_lock_until = now + 4
                        entry_status = "DENIED: FULL"
                        cooldowns[car_id] = now
            entry_display = cv2.resize(frame_en, (560, 315))

    # 出口逻辑独立于入口摄像头，入口摄像头坏了也不影响出口处理。
    if cap_exit:
        ret_ex, frame_ex = cap_exit.read()
        if ret_ex:
            if now - last_exit_scan_time >= QR_SCAN_INTERVAL:
                last_exit_scan_time = now
                found_cars_ex = exit_scanner.scan_and_annotate(frame_ex)
                for car_id in found_cars_ex:
                    if car_id not in cooldowns or (now - cooldowns[car_id] > COOLDOWN_PERIOD):
                        try_exit_payment(car_id, now)
                        cooldowns[car_id] = now
            exit_display = cv2.resize(frame_ex, (560, 315))

    if entry_timer > 0 and now > entry_timer:
        send_serial("a")
        entry_timer = 0
        entry_status = "Waiting..."
    if exit_timer > 0 and now > exit_timer:
        send_serial("b")
        exit_timer = 0
        exit_status = "Waiting..."

    if scheduled_exit_retry > 0 and now >= scheduled_exit_retry:
        retry_car = pending_exit_car
        scheduled_exit_retry = 0
        if retry_car:
            try_exit_payment(retry_car, now)

    if red_led_off_time > 0 and now > red_led_off_time and database.get_available_spots() > 0:
        send_serial("r")
        red_led_off_time = 0
    if yellow_led_off_time > 0 and now > yellow_led_off_time and pending_exit_car is None:
        send_serial("y")
        yellow_led_off_time = 0

    dashboard = build_dashboard(entry_display, exit_display, entry_status, exit_status, system_status)
    cv2.imshow(WINDOW_NAME, dashboard)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

if cap_entry:
    cap_entry.release()
if cap_exit:
    cap_exit.release()
cv2.destroyAllWindows()
