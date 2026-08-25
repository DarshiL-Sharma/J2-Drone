#Configuration and protocol constants for the drone controller

import os


DRONE_IP = "192.168.1.1"
DRONE_PORT = 7099

RTSP_URL = 0  # "rtsp://192.168.1.1:7070/webcam"
YOLO_MODEL_PATH = "software/yolov8n.pt"
VIDEO_DISPLAY_SIZE = (480, 360)
VIDEO_REFRESH_MS = 50

#Camera tilt correction
#Positive angle = rotate counter-clockwise
CAMERA_TILT_ANGLE = 0  #7.5 #because the drone's cam is slightly tilted (hardware assemble issue) 

#Fire detection (color/HSV heuristic - currently the model isn't trained)
FIRE_LOWER_HSV = (0, 120, 200)
FIRE_UPPER_HSV = (35, 255, 255)
FIRE_PIXEL_THRESHOLD = 3000
FIRE_SAVE_COOLDOWN_SECONDS = 5.0

CENTER = 0x80
MAX_DEV = 0x28
STICK_MAX = CENTER + MAX_DEV
STICK_MIN = CENTER - MAX_DEV

CMD_IDLE = 0x00
CMD_TAKEOFF = 0x01
CMD_KILL = 0x04

CAMERA_FORWARD_FRAME = bytes.fromhex("0601")
CAMERA_DOWN_FRAME = bytes.fromhex("0602")

SEND_INTERVAL_MS = 50
KEY_RELEASE_DEBOUNCE_MS = 60
LAND_FAILSAFE_SECONDS = 10.0

#Capture / gallery
SAVE_DIR = "output"

VICTIM_DIR = os.path.join(SAVE_DIR, "victims")
VICTIM_SAVE_COOLDOWN_SECONDS = 5.0
GALLERY_THUMB_SIZE = (110, 80)
GALLERY_MAX_STRIP_THUMBS = 5
GALLERY_REFRESH_MS = 2000
FULL_VIEW_MAX_SIZE = (900, 700)

FIRE_DIR = os.path.join(SAVE_DIR, "fire")

#key -> (axis, value_when_held, on-screen button label, confirmed-by-packet-capture?)
KEY_MAP = {
    "w": ("b3", STICK_MAX, "Forward", True),
    "s": ("b3", STICK_MIN, "Backward", False),
    "a": ("b2", STICK_MIN, "Roll 1  [dir. unconfirmed]", False),
    "d": ("b2", STICK_MAX, "Roll 2  [dir. unconfirmed]", False),
    "left": ("b5", 0x01, "Camera pan A", False),
    "right": ("b5", 0xFF, "Camera pan B", False),
}

# Throttle (b4) is incremental/ramped while held.
THROTTLE_STEP = 4
