"""
qr_scanner.py - 二维码识别模块
依赖: pip install opencv-python pyzbar
Linux还需要: sudo apt install libzbar0
"""

import cv2
from pyzbar.pyzbar import decode
import time


def scan_qr(camera_index: int = 0, timeout_sec: float = 8.0) -> str | None:
    """
    持续扫描摄像头画面，直到识别到二维码或超时。
    
    参数:
        camera_index: 摄像头编号（0=第一个，1=第二个）
        timeout_sec: 最多等待秒数
    返回:
        二维码内容字符串，或 None（超时/失败）
    """
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"[QR] 无法打开摄像头 {camera_index}")
        return None

    # 设置分辨率（提高二维码识别率）
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    start = time.time()
    result = None

    print(f"[QR] 摄像头{camera_index} 开始扫描...")
    while time.time() - start < timeout_sec:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            continue

        # 转灰度图提高识别率
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        decoded_list = decode(gray)

        for d in decoded_list:
            text = d.data.decode("utf-8").strip()
            if text.startswith("CAR_"):
                result = text
                print(f"[QR] 识别成功: {result}")
                break

        if result:
            break

        time.sleep(0.1)

    cap.release()
    if not result:
        print(f"[QR] 扫描超时（{timeout_sec}秒）")
    return result


def test_camera(camera_index: int = 0, duration: float = 5.0):
    """
    测试摄像头是否正常工作，会弹出预览窗口（调试用）
    """
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"摄像头 {camera_index} 无法打开")
        return
    
    start = time.time()
    print(f"摄像头{camera_index}预览中，按Q退出...")
    while time.time() - start < duration:
        ret, frame = cap.read()
        if ret:
            # 在画面上显示识别到的二维码
            decoded_list = decode(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
            for d in decoded_list:
                text = d.data.decode("utf-8")
                pts = d.polygon
                if len(pts) == 4:
                    cv2.polylines(frame, [
                        __import__("numpy").array(pts, dtype="int32").reshape((-1,1,2))
                    ], True, (0,255,0), 2)
                cv2.putText(frame, text, (pts[0].x, pts[0].y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
            cv2.imshow(f"Camera {camera_index}", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    # 运行此文件可测试摄像头
    import sys
    idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    test_camera(idx, duration=30)
