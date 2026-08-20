"""
Drone Control - STABLE / FOLLOW version.

Adds camera-based position hold: click-drag a box around an object (ball,
box, marker, etc.) directly below the drone in the downward-camera feed,
then toggle Follow Mode (F). While Follow Mode is on, the code keeps
comparing where that object is in each new frame vs. the center of the
frame, and nudges the drone forward/backward/left/right to keep the object
centered underneath it - a simple version of what "position hold" does on
fancier drones.

No altitude / throttle control in this file - throttle just stays at
center (hover level) once airborne, same as drone_control_basic.py.
This file is standalone and does not import from the other versions.

Requires:
    pip install opencv-python pillow
(tkinter is standard library, no install needed)

CONTROLS (window must be focused - click on it once before flying):
    T           - takeoff
    L           - land (throttle ramped smoothly to zero)
    F           - toggle Follow Mode ON/OFF (only works after you've
                  click-dragged a box around an object in the video)

    W / S       - forward / backward   (manual - overrides Follow Mode
                                         corrections while held)
    A / D       - left / right         (same - manual override)

    K + I  (hold BOTH together)  - EMERGENCY STOP
    Q + I  (hold BOTH together)  - quit the program (sends kill first)

HOW TO SELECT AN OBJECT TO FOLLOW:
    1. Make sure the downward camera feed is showing (bottom-left panel).
    2. Click and hold on the object in the video, drag to draw a small box
       around it, then release the mouse button.
    3. Press F to turn Follow Mode on. The status line will confirm.
    4. Press F again any time to hand control back to your own keys.

Protocol basis (from packet captures):
    03 66 [B2] [B3] [B4] [B5] [CMD] [CHK] 99
           Roll Pitch Throttle Yaw   Cmd   Checksum = B2^B3^B4^B5^CMD
    CMD 0x00 = idle, CMD 0x01 = takeoff, CMD 0x04 = kill.
    Axes range ~0x58 (min) to 0xA8 (max) around center 0x80.
"""

import socket
import time
import threading
import queue
import tkinter as tk
from tkinter import font as tkfont

try:
    import cv2
    from PIL import Image, ImageTk
    VIDEO_AVAILABLE = True
except ImportError:
    VIDEO_AVAILABLE = False  # video panel + follow mode will show an install hint instead of crashing

DRONE_IP = "192.168.1.1"
DRONE_PORT = 7099

# Downward-facing camera stream (assumes same RTSP source as your other files -
# change this if your downward camera has a different URL).
RTSP_URL = "rtsp://192.168.1.1:7070/webcam"
VIDEO_DISPLAY_SIZE = (480, 360)   # width, height shown in the GUI
VIDEO_REFRESH_MS = 50             # how often the GUI polls for a new frame (~20fps ceiling)

CENTER = 0x80
MAX_DEV = 0x28
STICK_MAX = CENTER + MAX_DEV     # 0xA8
STICK_MIN = CENTER - MAX_DEV     # 0x58

CMD_IDLE = 0x00
CMD_TAKEOFF = 0x01
CMD_KILL = 0x04

SEND_INTERVAL_MS = 50            # ~20Hz, matches observed traffic rate
KEY_RELEASE_DEBOUNCE_MS = 60     # swallow OS key-repeat release/press flicker

# --- Follow Mode tuning ---
# Correction is deliberately gentle - a small nudge, not a full-speed stick
# push - so the drone doesn't overcorrect and wobble.
FOLLOW_MAX_DEV = 0x10             # max correction deflection (smaller than MAX_DEV on purpose)
FOLLOW_DEADBAND_PX = 15           # if object is within this many pixels of center, do nothing
FOLLOW_GAIN = 0.6                 # how strongly it reacts to how far off-center the object is


def checksum(b2, b3, b4, b5, cmd):
    return b2 ^ b3 ^ b4 ^ b5 ^ cmd


def build_frame(b2=CENTER, b3=CENTER, b4=CENTER, b5=CENTER, cmd=CMD_IDLE):
    b2, b3, b4, b5, cmd = (max(0, min(0xFF, int(v))) for v in (b2, b3, b4, b5, cmd))
    chk = checksum(b2, b3, b4, b5, cmd)
    return bytes([0x03, 0x66, b2, b3, b4, b5, cmd, chk, 0x99])


class Drone:
    """Thin wrapper around the UDP socket + protocol frame builder."""

    def __init__(self, ip=DRONE_IP, port=DRONE_PORT):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.addr = (ip, port)
        self.throttle = CENTER
        self.armed = False

    def send_axes(self, b2, b3, b4, b5, cmd=CMD_IDLE):
        self.sock.sendto(build_frame(b2, b3, b4, b5, cmd), self.addr)

    def _hold_blocking(self, duration, **axes):
        """Used only for the short discrete takeoff/kill pulses (runs in a worker thread)."""
        frame = build_frame(**axes)
        end = time.time() + duration
        while time.time() < end:
            self.sock.sendto(frame, self.addr)
            time.sleep(0.05)

    def takeoff(self):
        self._hold_blocking(1.0, cmd=CMD_TAKEOFF)
        self.throttle = CENTER
        self.armed = True

    def kill(self):
        self._hold_blocking(1.0, cmd=CMD_KILL)
        self.armed = False

    def land(self, on_progress=None, step=0x10, step_time=0.05):
        """Verified landing: ramp throttle down to zero."""
        b4 = self.throttle
        while b4 > 0:
            b4 = max(0, b4 - step)
            self.sock.sendto(build_frame(b4=b4, cmd=CMD_IDLE), self.addr)
            if on_progress:
                on_progress(b4)
            time.sleep(step_time)
        self.throttle = 0
        self.armed = False


class FollowTracker:
    """Reads the downward camera feed and tracks one user-selected object.

    Deliberately decoupled from Tkinter - it just keeps `self.latest_frame`
    (for display) and `self.offset` (how far the object is from frame
    center, in pixels) updated in a background thread. The GUI polls both
    on its own timer, so slow video can never freeze the keyboard controls.
    """

    def __init__(self, url=RTSP_URL):
        self.url = url
        self.cap = None
        self.latest_frame = None      # RGB numpy array, for display
        self.frame_size = None        # (width, height) of raw frames from the camera
        self.offset = None            # (dx, dy) in pixels: object position minus frame center
        self.tracker = None
        self.has_target = False
        self.lock = threading.Lock()
        self.running = False
        self.status = "not started"
        self._pending_roi = None      # ROI queued from the GUI thread, picked up by the video thread

    def start(self):
        self.running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self.running = False

    def set_target(self, x, y, w, h):
        """Called from the GUI thread after the user drags a selection box.
        Coordinates are in raw camera-frame pixels, not display pixels."""
        self._pending_roi = (x, y, w, h)

    def clear_target(self):
        self._pending_roi = None
        with self.lock:
            self.tracker = None
            self.has_target = False
            self.offset = None

    def get_latest_frame(self):
        with self.lock:
            return None if self.latest_frame is None else self.latest_frame.copy()

    def get_offset(self):
        with self.lock:
            return self.offset

    def _make_tracker(self):
        # Different OpenCV versions expose the tracker constructor in different
        # places - try the common ones so this doesn't crash on your install.
        for factory in (
            getattr(getattr(cv2, "legacy", None), "TrackerCSRT_create", None),
            getattr(cv2, "TrackerCSRT_create", None),
            getattr(getattr(cv2, "legacy", None), "TrackerKCF_create", None),
            getattr(cv2, "TrackerKCF_create", None),
        ):
            if factory is not None:
                return factory()
        raise RuntimeError("No object tracker available in this OpenCV install")

    def _loop(self):
        self.status = "connecting to stream..."
        self.cap = cv2.VideoCapture(self.url)
        if not self.cap.isOpened():
            self.status = "stream not available (check RTSP URL / drone connection)"
            return
        self.status = "live"

        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                self.status = "frame lost - stream ended"
                break

            h, w = frame.shape[:2]
            self.frame_size = (w, h)

            # A new selection came in from the GUI - (re)start the tracker on it.
            if self._pending_roi is not None:
                roi = self._pending_roi
                self._pending_roi = None
                try:
                    tracker = self._make_tracker()
                    tracker.init(frame, roi)
                    with self.lock:
                        self.tracker = tracker
                        self.has_target = True
                except Exception as e:
                    self.status = f"tracker init failed: {e}"

            offset = None
            with self.lock:
                tracker = self.tracker

            if tracker is not None:
                ok, box = tracker.update(frame)
                if ok:
                    x, y, bw, bh = box
                    cx, cy = x + bw / 2, y + bh / 2
                    frame_cx, frame_cy = w / 2, h / 2
                    offset = (cx - frame_cx, cy - frame_cy)
                    cv2.rectangle(frame, (int(x), int(y)), (int(x + bw), int(y + bh)),
                                  (0, 255, 0), 2)
                    cv2.circle(frame, (int(cx), int(cy)), 4, (0, 255, 0), -1)
                else:
                    with self.lock:
                        self.has_target = False
                    self.status = "lost the object - select it again"

            # crosshair at frame center, for reference while selecting/flying
            cv2.drawMarker(frame, (w // 2, h // 2), (255, 255, 0),
                            markerType=cv2.MARKER_CROSS, markerSize=16, thickness=1)

            annotated_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            with self.lock:
                self.latest_frame = annotated_rgb
                self.offset = offset

        if self.cap:
            self.cap.release()
        if self.status == "live":
            self.status = "stopped"


class DroneApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Drone Control - Stable / Follow")
        self.geometry("1000x620")
        self.configure(bg="#1e1f26")

        self.drone = Drone()
        self.pressed = set()
        self._release_timers = {}
        self.busy = False
        self.kill_armed_guard = False
        self.quit_armed_guard = False
        self.follow_mode = False

        self.action_queue = queue.Queue()
        threading.Thread(target=self._worker_loop, daemon=True).start()

        self._move_key_labels = {
            "w": "forward", "s": "backward",
            "a": "left", "d": "right",
        }
        self._last_active_move_keys = frozenset()

        self._build_ui()

        if VIDEO_AVAILABLE:
            self.tracker = FollowTracker()
            self.tracker.start()
        else:
            self.tracker = None
        self._update_video()

        self.bind_all("<KeyPress>", self._on_key_press)
        self.bind_all("<KeyRelease>", self._on_key_release)
        self.protocol("WM_DELETE_WINDOW", self._quit)
        self.focus_set()

        self._loop()

    # ---------------------------------------------------------------- UI
    def _build_ui(self):
        big = tkfont.Font(size=14, weight="bold")
        mono = tkfont.Font(family="Courier", size=11)

        header = tk.Label(self, text="DRONE CONTROL - STABLE / FOLLOW", font=big,
                           fg="#ffffff", bg="#1e1f26")
        header.pack(pady=(12, 4))

        body = tk.Frame(self, bg="#1e1f26")
        body.pack(fill="both", expand=True, padx=16, pady=(4, 16))

        # ---- left column: downward camera + object selection ----
        left = tk.Frame(body, bg="#1e1f26")
        left.pack(side="left", fill="both", expand=False, padx=(0, 12))

        tk.Label(left, text="DOWNWARD CAMERA", font=big, fg="#ffffff", bg="#1e1f26").pack(anchor="w")
        tk.Label(left, text="Click + drag a box around the object to follow",
                 font=mono, fg="#888888", bg="#1e1f26").pack(anchor="w", pady=(0, 4))

        w, h = VIDEO_DISPLAY_SIZE
        self.video_canvas = tk.Canvas(left, width=w, height=h, bg="#000000",
                                       highlightthickness=0)
        self.video_canvas.pack()
        self._video_placeholder = self.video_canvas.create_text(
            w // 2, h // 2, text="Starting camera...", fill="#888888", width=w - 20
        )
        self._video_image_id = None
        self._video_photo = None
        self._select_rect_id = None
        self._select_start = None

        self.video_canvas.bind("<ButtonPress-1>", self._on_select_start)
        self.video_canvas.bind("<B1-Motion>", self._on_select_drag)
        self.video_canvas.bind("<ButtonRelease-1>", self._on_select_end)

        self.follow_var = tk.StringVar(value="Follow Mode: OFF (no target selected)")
        tk.Label(left, textvariable=self.follow_var, font=mono, fg="#8fd6ff",
                 bg="#1e1f26").pack(anchor="w", pady=(6, 0))

        # ---- right column: status / controls / log ----
        right = tk.Frame(body, bg="#1e1f26")
        right.pack(side="left", fill="both", expand=True)

        self.status_var = tk.StringVar(value="DISARMED")
        self.status_label = tk.Label(right, textvariable=self.status_var, font=big,
                                      fg="#ff5555", bg="#1e1f26")
        self.status_label.pack(pady=4)

        telem = tk.Frame(right, bg="#2b2d38", padx=12, pady=8)
        telem.pack(pady=8, fill="x")
        self.telem_var = tk.StringVar(value="roll=0x80 pitch=0x80")
        tk.Label(telem, textvariable=self.telem_var, font=mono, fg="#8fd6ff", bg="#2b2d38").pack()

        self.action_var = tk.StringVar(value="Ready. Click the video or window, then fly.")
        tk.Label(right, textvariable=self.action_var, font=mono, fg="#cccccc", bg="#1e1f26",
                 wraplength=420, justify="left").pack(pady=6, anchor="w")

        help_text = (
            "T = takeoff        L = land        F = toggle Follow Mode\n"
            "W/S = forward/backward     A/D = left/right\n"
            "(manual keys override Follow Mode corrections while held)\n\n"
            "Hold K + I together = EMERGENCY STOP\n"
            "Hold Q + I together = QUIT (kills first)"
        )
        tk.Label(right, text=help_text, font=mono, fg="#888888", bg="#1e1f26",
                 justify="left").pack(pady=10, anchor="w")

        self.log_box = tk.Listbox(right, height=8, bg="#111218", fg="#7CFC00", font=mono,
                                   highlightthickness=0, borderwidth=0)
        self.log_box.pack(fill="both", expand=True, pady=(4, 0))

    def _log(self, msg):
        self.log_box.insert(tk.END, msg)
        self.log_box.yview_moveto(1.0)

    # ------------------------------------------------------------- video / selection
    def _on_select_start(self, event):
        self._select_start = (event.x, event.y)
        if self._select_rect_id:
            self.video_canvas.delete(self._select_rect_id)
            self._select_rect_id = None

    def _on_select_drag(self, event):
        if self._select_start is None:
            return
        x0, y0 = self._select_start
        if self._select_rect_id:
            self.video_canvas.delete(self._select_rect_id)
        self._select_rect_id = self.video_canvas.create_rectangle(
            x0, y0, event.x, event.y, outline="#00ff00", width=2
        )

    def _on_select_end(self, event):
        if self._select_start is None or self.tracker is None or self.tracker.frame_size is None:
            self._select_start = None
            return
        x0, y0 = self._select_start
        x1, y1 = event.x, event.y
        self._select_start = None

        disp_w, disp_h = VIDEO_DISPLAY_SIZE
        sel_x0, sel_x1 = sorted((max(0, min(disp_w, x0)), max(0, min(disp_w, x1))))
        sel_y0, sel_y1 = sorted((max(0, min(disp_h, y0)), max(0, min(disp_h, y1))))
        if sel_x1 - sel_x0 < 8 or sel_y1 - sel_y0 < 8:
            self._log("Selection too small - drag a bigger box around the object.")
            return

        # convert from display-panel pixels to the raw camera frame's pixel scale
        raw_w, raw_h = self.tracker.frame_size
        scale_x, scale_y = raw_w / disp_w, raw_h / disp_h
        roi = (sel_x0 * scale_x, sel_y0 * scale_y,
               (sel_x1 - sel_x0) * scale_x, (sel_y1 - sel_y0) * scale_y)

        self.tracker.set_target(*roi)
        self._log("Target selected. Press F to turn Follow Mode on.")

    def _update_video(self):
        if self.tracker is None:
            self.video_canvas.itemconfig(
                self._video_placeholder,
                text="Video/tracking disabled.\npip install opencv-python pillow"
            )
        else:
            frame = self.tracker.get_latest_frame()
            if frame is not None:
                img = Image.fromarray(frame).resize(VIDEO_DISPLAY_SIZE)
                self._video_photo = ImageTk.PhotoImage(image=img)
                if self._video_image_id is None:
                    self.video_canvas.delete(self._video_placeholder)
                    self._video_image_id = self.video_canvas.create_image(
                        0, 0, anchor="nw", image=self._video_photo
                    )
                else:
                    self.video_canvas.itemconfig(self._video_image_id, image=self._video_photo)
            else:
                self.video_canvas.itemconfig(self._video_placeholder, text=f"Camera: {self.tracker.status}")

            with self.tracker.lock:
                has_target = self.tracker.has_target
            if self.follow_mode and has_target:
                self.follow_var.set("Follow Mode: ON - holding position")
            elif self.follow_mode and not has_target:
                self.follow_var.set("Follow Mode: ON but target lost - select object again")
            elif has_target:
                self.follow_var.set("Follow Mode: OFF (target selected - press F)")
            else:
                self.follow_var.set("Follow Mode: OFF (no target selected)")

        self.after(VIDEO_REFRESH_MS, self._update_video)

    # ------------------------------------------------------------ keys
    def _on_key_press(self, event):
        key = event.keysym.lower()

        if key not in self._release_timers and key not in self.pressed:
            self._log(f"[key] {key}")

        if key in self._release_timers:
            self.after_cancel(self._release_timers.pop(key))

        newly_pressed = key not in self.pressed
        self.pressed.add(key)

        if newly_pressed:
            self._handle_single_key(key)
        self._handle_combo_keys()

    def _on_key_release(self, event):
        key = event.keysym.lower()

        def actually_release():
            self.pressed.discard(key)
            self._release_timers.pop(key, None)
            if key in ("k", "i"):
                self.kill_armed_guard = self.kill_armed_guard and (
                    "k" in self.pressed and "i" in self.pressed
                )
            if key in ("q", "i"):
                self.quit_armed_guard = self.quit_armed_guard and (
                    "q" in self.pressed and "i" in self.pressed
                )

        self._release_timers[key] = self.after(KEY_RELEASE_DEBOUNCE_MS, actually_release)

    def _handle_single_key(self, key):
        if key == "t":
            self._enqueue("Taking off...", self.drone.takeoff, done_msg="Airborne.")
        elif key == "l":
            self._enqueue("Landing...",
                           lambda: self.drone.land(on_progress=self._land_progress),
                           done_msg="Landed.")
        elif key == "f":
            self._toggle_follow()

    def _toggle_follow(self):
        if self.tracker is None:
            self._log("Follow Mode unavailable - video/tracking not installed.")
            return
        with self.tracker.lock:
            has_target = self.tracker.has_target
        if not self.follow_mode and not has_target:
            self._log("No object selected yet - click-drag a box around it first.")
            return
        self.follow_mode = not self.follow_mode
        self._log(f"Follow Mode: {'ON' if self.follow_mode else 'OFF'}")

    def _handle_combo_keys(self):
        both_ki = "k" in self.pressed and "i" in self.pressed
        both_qi = "q" in self.pressed and "i" in self.pressed

        if both_ki and not self.kill_armed_guard:
            self.kill_armed_guard = True
            self._fire_kill_now()

        if both_qi and not self.quit_armed_guard:
            self.quit_armed_guard = True
            self._quit()

    def _land_progress(self, throttle_value):
        self.after(0, lambda: self.telem_var.set(f"landing... throttle=0x{throttle_value:02X}"))

    def _enqueue(self, name, fn, done_msg=""):
        self._log(f"> queued: {name}")
        self.action_queue.put((name, fn, done_msg))

    def _worker_loop(self):
        while True:
            name, fn, done_msg = self.action_queue.get()
            self.busy = True
            self.after(0, lambda n=name: self.action_var.set(n))
            try:
                fn()
            except Exception as e:
                self.after(0, lambda err=e: self._log(f"  ERROR: {err}"))
            self.busy = False
            self.after(0, lambda m=done_msg: self._finish_action(m))

    def _finish_action(self, done_msg):
        self.action_var.set(done_msg or "Ready.")
        self._log(f"  {done_msg}")
        self._update_status()

    def _fire_kill_now(self):
        self._log("> EMERGENCY STOP (K+I)")
        try:
            while True:
                self.action_queue.get_nowait()
        except queue.Empty:
            pass

        def worker():
            self.drone.kill()
            self.after(0, lambda: self._finish_action("Motors cut."))

        threading.Thread(target=worker, daemon=True).start()

    def _update_status(self):
        if self.drone.armed:
            self.status_var.set("ARMED / FLYING")
            self.status_label.config(fg="#55ff55")
        else:
            self.status_var.set("DISARMED")
            self.status_label.config(fg="#ff5555")

    # -------------------------------------------------------- flight loop
    def _compute_axes(self):
        b2, b3 = CENTER, CENTER  # roll, pitch
        manual = False

        if "w" in self.pressed:
            b3 = STICK_MAX
            manual = True
        elif "s" in self.pressed:
            b3 = STICK_MIN
            manual = True

        if "a" in self.pressed:
            b2 = STICK_MIN
            manual = True
        elif "d" in self.pressed:
            b2 = STICK_MAX
            manual = True

        # Manual keys always win - Follow Mode only steps in when you're not
        # actively flying yourself.
        if manual:
            return b2, b3

        if self.follow_mode and self.tracker is not None:
            offset = self.tracker.get_offset()
            if offset is not None:
                dx, dy = offset
                if abs(dx) > FOLLOW_DEADBAND_PX:
                    correction = max(-FOLLOW_MAX_DEV, min(FOLLOW_MAX_DEV, dx * FOLLOW_GAIN))
                    b2 = CENTER + correction   # object drifted right (+dx) -> nudge right to re-center under it
                if abs(dy) > FOLLOW_DEADBAND_PX:
                    correction = max(-FOLLOW_MAX_DEV, min(FOLLOW_MAX_DEV, dy * FOLLOW_GAIN))
                    b3 = CENTER - correction   # object drifted down (+dy) -> nudge forward to re-center under it

        return b2, b3

    def _loop(self):
        if not self.busy:
            b2, b3 = self._compute_axes()
            self.drone.send_axes(b2, b3, self.drone.throttle, CENTER, cmd=CMD_IDLE)
            self.telem_var.set(f"roll=0x{int(b2):02X} pitch=0x{int(b3):02X}")
            self._log_movement_transition()
        self.after(SEND_INTERVAL_MS, self._loop)

    def _log_movement_transition(self):
        active = frozenset(k for k in self.pressed if k in self._move_key_labels)
        if active == self._last_active_move_keys:
            return
        self._last_active_move_keys = active
        if active:
            labels = ", ".join(self._move_key_labels[k] for k in active)
            self._log(f"» moving: {labels}")
        else:
            self._log("» centered / hover")

    def _quit(self):
        self._log("> Quitting - sending kill first.")
        try:
            self.drone.kill()
        except Exception:
            pass
        if self.tracker:
            self.tracker.stop()
        self.destroy()


if __name__ == "__main__":
    DroneApp().mainloop()
