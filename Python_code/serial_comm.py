"""
serial_comm.py - Arduino串口通信模块
依赖: pip install pyserial
"""

import threading
import queue
import time

try:
    import serial
except ImportError:
    serial = None


class Arduino:
    """
    封装与Arduino的串口通信。
    后台线程持续监听Arduino消息，存入队列。
    主线程调用 get_message() 取出消息处理。
    """

    def __init__(self, port: str = "COM3", baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self._ser = None
        self._queue = queue.Queue()
        self._running = False
        self._lock = threading.Lock()

    def connect(self) -> bool:
        if serial is None:
            print("[串口] 连接失败: 未安装 pyserial，请先运行 pip install pyserial")
            return False
        try:
            self._ser = serial.Serial(self.port, self.baudrate, timeout=1)
            time.sleep(2)  # 等待Arduino重启完成
            self._running = True
            threading.Thread(target=self._listener, daemon=True).start()
            print(f"[串口] 已连接 Arduino @ {self.port}")
            return True
        except serial.SerialException as e:
            print(f"[串口] 连接失败: {e}")
            print("  → 请检查：")
            print("     1. Arduino是否插好USB")
            print("     2. 端口号是否正确（Windows:设备管理器，Mac/Linux: ls /dev/tty*）")
            return False

    def _listener(self):
        """后台线程：持续读取串口数据"""
        while self._running:
            try:
                if self._ser and self._ser.in_waiting:
                    raw = self._ser.readline()
                    line = raw.decode("utf-8", errors="ignore").strip()
                    if line:
                        self._queue.put(line)
                        # print(f"[Arduino→] {line}")  # 调试时取消注释
            except Exception as e:
                if self._running:
                    print(f"[串口] 读取错误: {e}")
            time.sleep(0.05)

    def send(self, command: str):
        """发送命令给Arduino"""
        with self._lock:
            if self._ser and self._ser.is_open:
                self._ser.write((command + "\n").encode("utf-8"))
                # print(f"[→Arduino] {command}")  # 调试时取消注释

    def get_message(self, block: bool = False, timeout: float = 0.05) -> str | None:
        """从队列取一条Arduino消息（非阻塞）"""
        try:
            return self._queue.get(block=block, timeout=timeout)
        except queue.Empty:
            return None

    def wait_for(self, prefix: str, timeout: float = 5.0) -> str | None:
        """等待特定前缀的消息，超时返回None"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            msg = self.get_message(block=True, timeout=0.2)
            if msg and msg.startswith(prefix):
                return msg
        return None

    def disconnect(self):
        self._running = False
        if self._ser:
            self._ser.close()

    # ---- 高级封装命令 ----

    def open_gate(self, gate: str):
        """gate: 'entry' 或 'exit'"""
        self.send("A" if gate == "entry" else "B")

    def close_gate(self, gate: str):
        self.send("a" if gate == "entry" else "b")

    def set_led(self, color: str, on: bool):
        """color: 'red' 或 'yellow'"""
        if color == "red":
            self.send("R" if on else "r")
        elif color == "yellow":
            self.send("Y" if on else "y")

    def lcd(self, line1: str, line2: str = ""):
        """更新LCD显示（每行最多16字符）"""
        self.send(f"LCD:{line1[:16]}|{line2[:16]}")

    def update_spots_display(self, count: int):
        """更新LCD上的剩余车位数"""
        self.send(f"SPOTS:{count}")
