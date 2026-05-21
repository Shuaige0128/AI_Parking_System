"""
database.py - 停车场数据库管理模块
使用 SQLite（无需安装额外数据库软件）
"""

import sqlite3
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "parking.db")

# ============================================================
# 初始化数据库
# ============================================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.executescript("""
        -- 车辆信息表
        CREATE TABLE IF NOT EXISTS vehicles (
            car_id     TEXT PRIMARY KEY,   -- e.g. CAR_001
            rfid_uid   TEXT,               -- 绑定的RFID卡UID
            balance    REAL DEFAULT 0.0,   -- 账户余额(元)
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        -- 停车记录表
        CREATE TABLE IF NOT EXISTS sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            car_id     TEXT NOT NULL,
            entry_time TEXT NOT NULL,
            exit_time  TEXT,
            fee        REAL DEFAULT 0.0,
            paid_at    TEXT,
            status     TEXT DEFAULT 'parked',  -- parked / exited
            FOREIGN KEY (car_id) REFERENCES vehicles(car_id)
        );

        -- 车位状态表
        CREATE TABLE IF NOT EXISTS spots (
            spot_id     INTEGER PRIMARY KEY,
            is_occupied INTEGER DEFAULT 0,
            car_id      TEXT
        );

        -- 初始化5个车位（已存在则忽略）
        INSERT OR IGNORE INTO spots (spot_id) VALUES (1),(2),(3),(4),(5);
    """)


    # 预注册你的 5 辆二维码车，并给每辆车充点初始资金
    cars = [('CAR_001',), ('CAR_002',), ('CAR_003',), ('CAR_004',), ('CAR_005',)]
    c.executemany("INSERT OR IGNORE INTO vehicles (car_id, balance) VALUES (?, 50.0)", cars)
    conn.commit()
    conn.close()
    print("[DB] 数据库初始化完成:", DB_PATH)



# ============================================================
# 车辆管理
# ============================================================
def register_vehicle(car_id: str) -> bool:
    """注册新车辆（已存在则忽略）"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO vehicles (car_id) VALUES (?)", (car_id,))
    is_new = c.rowcount > 0
    conn.commit()
    conn.close()
    return is_new


def link_rfid_to_car(car_id: str, rfid_uid: str):
    """将RFID卡绑定到车辆"""
    rfid_uid = normalize_rfid_uid(rfid_uid)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE vehicles SET rfid_uid=NULL WHERE rfid_uid=? AND car_id<>?", (rfid_uid, car_id))
    c.execute("UPDATE vehicles SET rfid_uid=? WHERE car_id=?", (rfid_uid, car_id))
    conn.commit()
    conn.close()


def get_vehicle_by_rfid(rfid_uid: str):
    """通过RFID UID查找车辆，返回 (car_id, balance) 或 None"""
    rfid_uid = normalize_rfid_uid(rfid_uid)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT car_id, balance FROM vehicles WHERE rfid_uid=?", (rfid_uid,))
    row = c.fetchone()
    conn.close()
    return row


def get_balance(car_id: str) -> float:
    """获取账户余额"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT balance FROM vehicles WHERE car_id=?", (car_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0.0


def normalize_rfid_uid(rfid_uid: str) -> str:
    """统一RFID UID格式，便于Arduino串口输出和数据库匹配。"""
    return rfid_uid.replace(" ", "").replace(":", "").replace("-", "").upper()


def set_balance(car_id: str, balance: float):
    """直接设置车辆余额，便于课堂演示前准备初始余额。"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE vehicles SET balance=? WHERE car_id=?", (balance, car_id))
    conn.commit()
    conn.close()


def top_up(rfid_uid: str, amount: float = 20.0) -> tuple:
    """
    通过RFID充值，返回 (success: bool, car_id: str, new_balance: float)
    """
    rfid_uid = normalize_rfid_uid(rfid_uid)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE vehicles SET balance = balance + ? WHERE rfid_uid=?",
              (amount, rfid_uid))
    if c.rowcount == 0:
        conn.close()
        return False, None, 0.0
    c.execute("SELECT car_id, balance FROM vehicles WHERE rfid_uid=?", (rfid_uid,))
    car_id, new_balance = c.fetchone()
    conn.commit()
    conn.close()
    return True, car_id, new_balance


def deduct_fee(car_id: str, fee: float) -> bool:
    """扣除停车费，余额不足时返回 False"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE vehicles SET balance = balance - ?
        WHERE car_id=? AND balance >= ?
    """, (fee, car_id, fee))
    success = c.rowcount > 0
    conn.commit()
    conn.close()
    return success


# ============================================================
# 停车记录管理
# ============================================================
def start_session(car_id: str) -> int:
    """记录车辆入场，返回 session_id"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    entry_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO sessions (car_id, entry_time) VALUES (?,?)",
              (car_id, entry_time))
    session_id = c.lastrowid
    conn.commit()
    conn.close()
    return session_id


def calculate_current_fee(car_id: str) -> float:
    """
    计算停车费用。

    Demo规则：前10秒免费，之后每秒0.1元，便于课堂演示快速看到扣费效果。
    最终提交/报告中可以说明这是演示压缩费率，或替换为正式停车场费率。
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # 查找该车状态为 'parked' 的入场时间
    c.execute("""
        SELECT entry_time FROM sessions 
        WHERE car_id=? AND status='parked' 
        ORDER BY session_id DESC LIMIT 1
    """, (car_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return 0.0

    # 计算时间差（秒）
    entry_dt = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
    duration_seconds = (datetime.now() - entry_dt).total_seconds()

    # 逻辑：前10秒免费
    if duration_seconds <= 10:
        return 0.0

    # 超过10秒的部分，每秒0.1元
    # 比如停了15秒，费用 = (15 - 10) * 0.1 = 0.5元
    fee = (duration_seconds - 10) * 0.1
    return round(fee, 2)


def complete_exit(car_id: str, fee: float):
    """支付完成后，正式结束停车记录"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("""
        UPDATE sessions
        SET exit_time=?, fee=?, paid_at=?, status='exited'
        WHERE car_id=? AND status='parked'
    """, (now_str, fee, now_str, car_id))
    conn.commit()
    conn.close()


def is_car_parked(car_id: str) -> bool:
    """检查车辆是否在场内"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT 1 FROM sessions WHERE car_id=? AND status='parked'", (car_id,))
    result = c.fetchone() is not None
    conn.close()
    return result


# ============================================================
# 车位管理
# ============================================================
def get_available_spots() -> int:
    """返回空闲车位数量"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM spots WHERE is_occupied=0")
    count = c.fetchone()[0]
    conn.close()
    return count


def update_spot(spot_id: int, is_occupied: int, car_id: str = None):
    """更新车位状态（由Arduino传感器触发）"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE spots SET is_occupied=?, car_id=? WHERE spot_id=?",
              (is_occupied, car_id, spot_id))
    conn.commit()
    conn.close()
