from ConstantsCenter.constants import (
    CAMERA_TILT_ANGLE,
    FIRE_LOWER_HSV,
    FIRE_UPPER_HSV,
    FIRE_PIXEL_THRESHOLD,
    CENTER,
    CMD_IDLE,
)
from ConstantsCenter.constants import SAVE_DIR,VICTIM_DIR,FIRE_DIR
import cv2
import numpy as np
import os

def fix_tilt(frame, angle=CAMERA_TILT_ANGLE):
    if not angle:
        return frame
    h, w = frame.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(frame, matrix, (w, h))


def detect_fire(frame_bgr):
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    lower = np.array(FIRE_LOWER_HSV)
    upper = np.array(FIRE_UPPER_HSV)
    mask = cv2.inRange(hsv, lower, upper)
    fire_pixel_count = cv2.countNonZero(mask)
    is_fire = fire_pixel_count > FIRE_PIXEL_THRESHOLD
    return is_fire, mask


def list_victim_captures(limit=None):
    try:
        files = [
            os.path.join(VICTIM_DIR, f) for f in os.listdir(VICTIM_DIR)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]
    except FileNotFoundError:
        return []
    files.sort(key=os.path.getmtime, reverse=True)
    return files[:limit] if limit else files


def checksum(b2, b3, b4, b5, cmd):
    return b2 ^ b3 ^ b4 ^ b5 ^ cmd


def build_frame(b2=CENTER, b3=CENTER, b4=CENTER, b5=CENTER, cmd=CMD_IDLE):
    b2, b3, b4, b5, cmd = (max(0, min(0xFF, int(v))) for v in (b2, b3, b4, b5, cmd))
    chk = checksum(b2, b3, b4, b5, cmd)
    return bytes([0x03, 0x66, b2, b3, b4, b5, cmd, chk, 0x99])

