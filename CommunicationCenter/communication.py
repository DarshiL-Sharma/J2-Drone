from ConstantsCenter.constants import (
    CAMERA_TILT_ANGLE,
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


def draw_fire_smoke_boxes(annotated, fire_results, conf_threshold):
    is_fire = False
    is_smoke = False
    try:
        boxes = fire_results[0].boxes
        names = fire_results[0].names
        if boxes is None:
            return is_fire, is_smoke
        for box in boxes:
            conf = float(box.conf[0])
            if conf < conf_threshold:
                continue
            cls_id = int(box.cls[0])
            label = names.get(cls_id, str(cls_id)).lower()
            if label == "fire":
                is_fire = True
                color = (0, 0, 255)
            elif label == "smoke":
                is_smoke = True
                color = (0, 165, 255)
            else:
                color = (0, 255, 255)
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            cv2.putText(annotated, f"{label} {conf:.2f}", (x1, max(0, y1 - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA)
    except Exception:
        pass
    return is_fire, is_smoke


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


def list_fire_captures(limit=None):
    try:
        files = [
            os.path.join(FIRE_DIR, f) for f in os.listdir(FIRE_DIR)
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