import os

import cv2


base_path = os.path.dirname(os.path.abspath(__file__))
model_dir = os.path.join(base_path, "WeChatQRCode")


class QRScanner:
    def __init__(self):
        self.use_wechat = hasattr(cv2, "wechat_qrcode_WeChatQRCode")
        if self.use_wechat:
            self.detector = cv2.wechat_qrcode_WeChatQRCode(
                os.path.join(model_dir, "detect.prototxt"),
                os.path.join(model_dir, "detect.caffemodel"),
                os.path.join(model_dir, "sr.prototxt"),
                os.path.join(model_dir, "sr.caffemodel"),
            )
        else:
            self.detector = cv2.QRCodeDetector()
            print("[QR] WeChat QRCode is unavailable. Falling back to cv2.QRCodeDetector.")

    def scan_and_annotate(self, frame):
        if self.use_wechat:
            return self._scan_wechat(frame)
        return self._scan_opencv(frame)

    def _scan_wechat(self, frame):
        res, pts = self.detector.detectAndDecode(frame)
        valid_ids = []
        if res:
            for i, car_id in enumerate(res):
                if "CAR_" in car_id:
                    valid_ids.append(car_id)
                    if len(pts) > i:
                        self._draw_box(frame, pts[i].astype(int), car_id)
        return valid_ids

    def _scan_opencv(self, frame):
        valid_ids = []
        if hasattr(self.detector, "detectAndDecodeMulti"):
            ok, decoded_info, points, _ = self.detector.detectAndDecodeMulti(frame)
            if ok and decoded_info:
                for i, car_id in enumerate(decoded_info):
                    if "CAR_" in car_id:
                        valid_ids.append(car_id)
                        if points is not None and len(points) > i:
                            self._draw_box(frame, points[i].astype(int), car_id)
                return valid_ids

        car_id, points, _ = self.detector.detectAndDecode(frame)
        if car_id and "CAR_" in car_id:
            valid_ids.append(car_id)
            if points is not None:
                self._draw_box(frame, points[0].astype(int), car_id)
        return valid_ids

    @staticmethod
    def _draw_box(frame, points, label):
        for j in range(4):
            cv2.line(frame, tuple(points[j]), tuple(points[(j + 1) % 4]), (0, 255, 0), 3)
        cv2.putText(frame, label, tuple(points[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
