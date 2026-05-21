"""
test_system.py - 系统测试脚本
在正式运行前，用于独立测试各个模块

运行方式: python test_system.py
"""

import sys
import time


def test_database():
    """测试数据库模块"""
    print("\n===== 测试数据库 =====")
    from database import (
        init_db, register_vehicle, get_balance, top_up,
        start_session, calculate_current_fee, complete_exit,
        is_car_parked, get_available_spots
    )
    
    init_db()
    
    # 注册车辆
    register_vehicle("CAR_001")
    register_vehicle("CAR_002")
    print("✓ 注册车辆 CAR_001, CAR_002")
    
    # 充值
    from database import link_rfid_to_car
    link_rfid_to_car("CAR_001", "TESTUID001")
    ok, car, bal = top_up("TESTUID001", 20.0)
    print(f"✓ 充值: {car} 余额 {bal:.2f}")
    
    # 入场
    sid = start_session("CAR_001")
    print(f"✓ 入场记录 session_id={sid}")
    
    # 检查
    print(f"✓ 余额: {get_balance('CAR_001'):.2f}")
    print(f"✓ 在场: {is_car_parked('CAR_001')}")
    print(f"✓ 剩余车位: {get_available_spots()}")
    
    time.sleep(1)  # 模拟停车1秒
    fee = calculate_current_fee("CAR_001")
    print(f"✓ 当前费用: {fee:.2f} (停30分钟内应为0)")
    
    complete_exit("CAR_001", fee)
    print(f"✓ 出场记录完成")
    print(f"✓ 在场状态: {is_car_parked('CAR_001')} (应为False)")
    
    print("数据库测试通过 ✓")


def test_camera(index=0):
    """测试摄像头"""
    print(f"\n===== 测试摄像头 {index} =====")
    from qr_scanner import test_camera
    print(f"摄像头{index}预览，把QR码对准镜头，按Q退出")
    test_camera(index, duration=30)


def test_arduino(port="COM3"):
    """测试Arduino串口通信"""
    print(f"\n===== 测试Arduino @ {port} =====")
    from serial_comm import Arduino
    
    ard = Arduino(port)
    if not ard.connect():
        print("连接失败")
        return
    
    print("测试LED...")
    ard.set_led("red", True)
    time.sleep(1)
    ard.set_led("red", False)
    ard.set_led("yellow", True)
    time.sleep(1)
    ard.set_led("yellow", False)
    
    print("测试LCD...")
    ard.lcd("Hello World!", "Testing...")
    time.sleep(2)
    
    print("测试入口闸杆...")
    ard.open_gate("entry")
    time.sleep(2)
    ard.close_gate("entry")
    
    print("测试出口闸杆...")
    ard.open_gate("exit")
    time.sleep(2)
    ard.close_gate("exit")
    
    ard.lcd("Test Done!", "All OK")
    print("Arduino测试完成 ✓")
    ard.disconnect()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  python test_system.py db           # 测试数据库")
        print("  python test_system.py cam 0        # 测试0号摄像头")
        print("  python test_system.py cam 1        # 测试1号摄像头")
        print("  python test_system.py arduino COM3 # 测试Arduino")
        sys.exit()
    
    cmd = sys.argv[1]
    if cmd == "db":
        test_database()
    elif cmd == "cam":
        idx = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        test_camera(idx)
    elif cmd == "arduino":
        port = sys.argv[2] if len(sys.argv) > 2 else "COM3"
        test_arduino(port)
