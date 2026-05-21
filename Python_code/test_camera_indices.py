"""
Preview camera indexes to find the correct entry and exit USB cameras.

Usage:
    python test_camera_indices.py

Press Q in any preview window to stop. If two windows show the same physical
camera, update ENTRY_CAMERA_INDEX and EXIT_CAMERA_INDEX in main.py.
"""

import cv2


def main():
    cameras = []
    for index in range(6):
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_FPS, 15)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            cameras.append((index, cap))
            print(f"[OK] Camera index {index} opened")
        else:
            cap.release()

    if not cameras:
        print("[ERROR] No cameras opened")
        return

    while True:
        for index, cap in cameras:
            ret, frame = cap.read()
            if not ret:
                continue
            cv2.putText(frame, f"Camera index {index}", (24, 44),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
            cv2.imshow(f"Camera {index}", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    for _, cap in cameras:
        cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
