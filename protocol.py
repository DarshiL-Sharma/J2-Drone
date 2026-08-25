"""Low-level, stateless packet and frame-processing helpers"""

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

from config import (
    CAMERA_TILT_ANGLE,
    CENTER,
    CMD_IDLE,
    FIRE_LOWER_HSV,
    FIRE_PIXEL_THRESHOLD,
    FIRE_UPPER_HSV,
)


def fix_tilt(frame, angle=CAMERA_TILT_ANGLE):
    """Rotate a frame around its center to correct camera-mount tilt."""
    if cv2 is None:
        raise ImportError("OpenCV is required for frame processing.")
    if not angle:
        return frame
    h, w = frame.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(frame, matrix, (w, h))


def detect_fire(frame_bgr):
    """Detect fire using the original HSV threshold heuristic."""
    if cv2 is None or np is None:
        raise ImportError("OpenCV and NumPy are required for fire detection.")
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    lower = np.array(FIRE_LOWER_HSV)
    upper = np.array(FIRE_UPPER_HSV)
    mask = cv2.inRange(hsv, lower, upper)
    fire_pixel_count = cv2.countNonZero(mask)
    is_fire = fire_pixel_count > FIRE_PIXEL_THRESHOLD
    return is_fire, mask


def checksum(b2, b3, b4, b5, cmd):
    return b2 ^ b3 ^ b4 ^ b5 ^ cmd


def build_frame(b2=CENTER, b3=CENTER, b4=CENTER, b5=CENTER, cmd=CMD_IDLE):
    b2, b3, b4, b5, cmd = (
        max(0, min(0xFF, int(v))) for v in (b2, b3, b4, b5, cmd)
    )
    chk = checksum(b2, b3, b4, b5, cmd)
    return bytes([0x03, 0x66, b2, b3, b4, b5, cmd, chk, 0x99])
