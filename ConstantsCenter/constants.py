import os
DRONE_IP = "192.168.1.1"
DRONE_PORT = 7099

RTSP_URL = "rtsp://192.168.1.1:7070/webcam"
# RTSP_URL = 0                # local webcam index. A string gets treated as a filename/URL
               # and silently fails to open. Swap back to the rtsp:// string
               # above once you're testing against the drone again.
YOLO_MODEL_PATH = "software/yolov8n.pt"
VIDEO_DISPLAY_SIZE = (480, 360)
VIDEO_REFRESH_MS = 50
SAVE_DIR = "output"
VICTIM_DIR = os.path.join(SAVE_DIR, "victims")
FIRE_DIR = os.path.join(SAVE_DIR, "fire")
CAMERA_TILT_ANGLE = 7.5

#Fire/smoke detection via trained YOLO model
FIRE_SMOKE_MODEL_PATH = "software/best.pt"
FIRE_SMOKE_CONF_THRESHOLD = 0.60
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
LAND_FAILSAFE_SECONDS = 3.0

#Victim capture & autosave to gallery
VICTIM_SAVE_COOLDOWN_SECONDS = 5.0
GALLERY_THUMB_SIZE = (110, 80)
GALLERY_MAX_STRIP_THUMBS = 5
GALLERY_REFRESH_MS = 2000
FULL_VIEW_MAX_SIZE = (900, 700)

# Dead Reckoning System
SPEED=3.5

# --- SOS cloud + dispatch ---
FIREBASE_CREDENTIALS_PATH = "CloudCenter/firebase-key.json"
CLIMB_THROTTLE = 0xA8            # stick value held during the 2m climb
PERSON_CONF_THRESHOLD = 0.60   # min confidence to count/draw a person box

# --- SOS panel (Display) ---
SOS_COLOR_IDLE = "#7CFC00"       # green — nothing happening
SOS_COLOR_ENROUTE = "#ffb347"    # amber — flying to target
SOS_COLOR_LANDED = "#7CFC00"     # green — dispatch finished
SOS_COLOR_ERROR = "#ff5555"      # red — dispatch failed


# --- SOS dispatch ---
BASE_LAT = 22.6777            # CHANGE to real base/takeoff GPS latitude
BASE_LNG = 75.8468             # CHANGE to real base/takeoff GPS longitude
# FIREBASE_CREDENTIALS_PATH = "CloudCenter/firebase-key.json"

#  Zoom control Map
MAP_DEFAULT_ZOOM = 15


# --- SOS Alerts panel (historical list, sos_store polling) ---
SOS_REFRESH_MS = 2000        # how often the SOS Alerts card re-polls sos_store
SOS_THUMB_SIZE = (110, 80)   # front/back image thumbnail size inside each SOS card
SOS_DIR = os.path.join(SAVE_DIR, "sos")
SOS_DB_PATH = os.path.join(SAVE_DIR, "sos_reports.db")

