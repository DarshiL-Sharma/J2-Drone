"""
Drone Control - GUI with keyboard flying, live camera/object detection,
manual photo/recording save.py-->aayush, and automatic victim-capture +
gallery-->arpit: whenever the YOLO feed detects a person, the annotated
frame is auto-saved to output/victims/ (rate-limited, see
VICTIM_SAVE_COOLDOWN_SECONDS below) and shown in a gallery panel in the
GUI - both an inline thumbnail strip and a "View All Captures" grid

Everything else in this file is unchanged from the tested branch this
was built on - only the victim-capture pieces are new (search for
"victim" to find every change)
"""

import socket
import time
import threading
import queue
import tkinter as tk
from tkinter import font as tkfont
import os
import datetime

try:
    import cv2
    from ultralytics import YOLO
    from PIL import Image, ImageTk
    VIDEO_AVAILABLE = True
except ImportError:
    VIDEO_AVAILABLE = False

DRONE_IP = "192.168.1.1"
DRONE_PORT = 7099

RTSP_URL = 1
YOLO_MODEL_PATH = "software/yolov8n.pt"
VIDEO_DISPLAY_SIZE = (480, 360)
VIDEO_REFRESH_MS = 50
RTSP_URL = "rtsp://192.168.1.1:7070/webcam"
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

SAVE_DIR = "output"

#Victim capture & autosave to gallery
VICTIM_DIR = os.path.join(SAVE_DIR, "victims")
VICTIM_SAVE_COOLDOWN_SECONDS = 5.0   # min gap between auto-saves, so a person
                                      # standing in frame doesn't fill the disk
GALLERY_THUMB_SIZE = (110, 80)       # inline strip thumbnail size
GALLERY_MAX_STRIP_THUMBS = 5         # how many recent thumbnails show inline
GALLERY_REFRESH_MS = 2000            # how often the GUI re-checks the folder
FULL_VIEW_MAX_SIZE = (900, 700)      # cap for the "click to enlarge" popup


def list_victim_captures(limit=None):
    """Newest-first list of saved victim capture filepaths. Just reads the
    folder - safe to call from the GUI thread any time, no locking needed."""
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


class Drone:
    def __init__(self, ip=DRONE_IP, port=DRONE_PORT):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.addr = (ip, port)
        self.throttle = CENTER
        self.armed = False
        self.camera_facing_down = False

    def send_axes(self, b2, b3, b4, b5, cmd=CMD_IDLE):
        self.sock.sendto(build_frame(b2, b3, b4, b5, cmd), self.addr)

    def _hold_blocking(self, duration, **axes):
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
        b4 = self.throttle
        while b4 > 0:
            b4 = max(0, b4 - step)
            self.sock.sendto(build_frame(b4=b4, cmd=CMD_IDLE), self.addr)
            if on_progress:
                on_progress(b4)
            time.sleep(step_time)
        self.throttle = 0
        self.armed = False

    def land_ramp(self, on_progress=None, step=0x10, step_time=0.05):
        return self.land(on_progress=on_progress, step=step, step_time=step_time)

    def land_failsafe(self, on_progress=None, duration=LAND_FAILSAFE_SECONDS):
        start = time.time()
        while time.time() - start < duration:
            remaining = duration - (time.time() - start)
            if on_progress:
                on_progress(remaining)
            time.sleep(0.1)
        self.throttle = CENTER
        self.armed = False

    def calibrate(self):
        self._hold_blocking(0.3, cmd=CMD_IDLE)

    def set_camera_direction(self, face_down):
        frame = CAMERA_DOWN_FRAME if face_down else CAMERA_FORWARD_FRAME
        self.sock.sendto(frame, self.addr)
        self.camera_facing_down = face_down

    def toggle_camera_direction(self):
        self.set_camera_direction(not self.camera_facing_down)
        return self.camera_facing_down


class VideoStream:
    def __init__(self, url=RTSP_URL, model_path=YOLO_MODEL_PATH):
        self.url = url
        self.model_path = model_path
        self.cap = None
        self.latest_frame = None
        self.lock = threading.Lock()
        self.running = False
        self.status = "not started"
        self.recording = False
        self.video_writer = None
        self.record_path = None
        self.last_victim_save_time = 0.0
        os.makedirs(SAVE_DIR, exist_ok=True)
        os.makedirs(VICTIM_DIR, exist_ok=True)

    def start(self):
        self.running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self.running = False
        self.stop_recording()

    def get_latest(self):
        with self.lock:
            return None if self.latest_frame is None else self.latest_frame.copy()

    def start_recording(self):
        with self.lock:
            self.recording = True

    def stop_recording(self):
        with self.lock:
            self.recording = False
            if self.video_writer is not None:
                self.video_writer.release()
                self.video_writer = None
                self.record_path = None

    def save_snapshot(self):
        frame = self.get_latest()
        if frame is None:
            return None
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(SAVE_DIR, f"snapshot_{ts}.jpg")
        bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        cv2.imwrite(path, bgr)
        return path

    def _contains_person(self, results):
        """True if this YOLO result contains at least one 'person' detection.
        Wrapped defensively - if the ultralytics output shape ever changes,
        this just skips auto-save instead of crashing the video thread."""
        try:
            boxes = results[0].boxes
            if boxes is None or boxes.cls is None:
                return False
            names = results[0].names
            for cls_id in boxes.cls.tolist():
                if names.get(int(cls_id), "").lower() == "person":
                    return True
        except Exception:
            pass
        return False

    def _save_victim_capture(self, annotated_bgr):
        #Saves the annotated frame
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        path = os.path.join(VICTIM_DIR, f"victim_{ts}.jpg")
        try:
            cv2.imwrite(path, annotated_bgr)
        except Exception:
            pass

    def _ensure_writer(self, frame_rgb):
        if self.video_writer is not None:
            return
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.record_path = os.path.join(SAVE_DIR, f"record_{ts}.avi")
        h, w = frame_rgb.shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        self.video_writer = cv2.VideoWriter(self.record_path, fourcc, 20.0, (w, h))

    def _loop(self):
        self.status = "loading YOLO model..."
        try:
            model = YOLO(self.model_path)
        except Exception as e:
            self.status = f"model load failed: {e}"
            return

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
            try:
                results = model(frame, verbose=False)
                annotated = results[0].plot()
                if self._contains_person(results):
                    now = time.time()
                    if now - self.last_victim_save_time >= VICTIM_SAVE_COOLDOWN_SECONDS:
                        self._save_victim_capture(annotated)
                        self.last_victim_save_time = now
            except Exception:
                annotated = frame
            annotated_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)

            with self.lock:
                self.latest_frame = annotated_rgb.copy()
                if self.recording:
                    self._ensure_writer(annotated_rgb)
                    bgr = cv2.cvtColor(annotated_rgb, cv2.COLOR_RGB2BGR)
                    self.video_writer.write(bgr)

        if self.cap:
            self.cap.release()
        with self.lock:
            if self.video_writer is not None:
                self.video_writer.release()
                self.video_writer = None
        if self.status == "live":
            self.status = "stopped"


class DroneApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Drone Control")
        self.geometry("1040x620")
        self.configure(bg="#1e1f26")

        self.drone = Drone()
        self.pressed = set()
        self._release_timers = {}
        self.busy = False
        self.kill_armed_guard = False
        self.quit_armed_guard = False

        self.action_queue = queue.Queue()
        threading.Thread(target=self._worker_loop, daemon=True).start()

        self._move_key_labels = {
            "w": "forward", "s": "backward",
            "a": "roll (tested)", "d": "roll (opposite)",
            "up": "throttle up", "down": "throttle down",
            "left": "camera pan A", "right": "camera pan B",
        }
        self._last_active_move_keys = frozenset()

        self._build_ui()
        self._refresh_gallery_strip()

        if VIDEO_AVAILABLE:
            self.video = VideoStream()
            self.video.start()
        else:
            self.video = None
        self._update_video()

        self.bind_all("<KeyPress>", self._on_key_press)
        self.bind_all("<KeyRelease>", self._on_key_release)
        self.protocol("WM_DELETE_WINDOW", self._quit)
        self.focus_set()

        self._loop()

    def _build_ui(self):
        big = tkfont.Font(size=14, weight="bold")
        mono = tkfont.Font(family="Courier", size=11)

        header = tk.Label(self, text="DRONE CONTROL", font=big, fg="#ffffff", bg="#1e1f26")
        header.pack(pady=(12, 4))

        body = tk.Frame(self, bg="#1e1f26")
        body.pack(fill="both", expand=True, padx=16, pady=(4, 16))

        left = tk.Frame(body, bg="#1e1f26")
        left.pack(side="left", fill="both", expand=False, padx=(0, 12))

        tk.Label(left, text="CAMERA", font=big, fg="#ffffff", bg="#1e1f26").pack(anchor="w")
        w, h = VIDEO_DISPLAY_SIZE
        video_frame = tk.Frame(left, bg="#000000", width=w, height=h)
        video_frame.pack_propagate(False)
        video_frame.pack()
        self.video_label = tk.Label(video_frame, text="Starting camera...", bg="#000000",
                                     fg="#888888", wraplength=w - 20, justify="center")
        self.video_label.pack(fill="both", expand=True)

        self.camera_dir_var = tk.StringVar(value="Camera: forward")
        tk.Label(left, textvariable=self.camera_dir_var, font=mono, fg="#8fd6ff",
                 bg="#1e1f26").pack(anchor="w", pady=(4, 0))

        # ---- victim capture gallery ----
        gallery_header = tk.Frame(left, bg="#1e1f26")
        gallery_header.pack(fill="x", pady=(14, 4))
        tk.Label(gallery_header, text="VICTIM CAPTURES", font=big, fg="#ffffff",
                 bg="#1e1f26").pack(side="left")
        self.victim_count_var = tk.StringVar(value="(0)")
        tk.Label(gallery_header, textvariable=self.victim_count_var, font=mono,
                 fg="#ffb347", bg="#1e1f26").pack(side="left", padx=(6, 0))

        self.gallery_strip = tk.Frame(left, bg="#1e1f26")
        self.gallery_strip.pack(fill="x", pady=(0, 4))
        self._gallery_thumb_widgets = []  # keeps widget + PhotoImage refs alive

        tk.Button(left, text="View All Captures", command=self._open_gallery_window,
                  bg="#33475b", fg="white", activebackground="#3d5871", relief="flat",
                  font=mono).pack(fill="x", pady=(2, 0))

        right = tk.Frame(body, bg="#1e1f26")
        right.pack(side="left", fill="both", expand=True)

        self.status_var = tk.StringVar(value="DISARMED")
        self.status_label = tk.Label(right, textvariable=self.status_var, font=big,
                                      fg="#ff5555", bg="#1e1f26")
        self.status_label.pack(pady=4)

        telem = tk.Frame(right, bg="#2b2d38", padx=12, pady=8)
        telem.pack(pady=8, fill="x")
        self.telem_var = tk.StringVar(value="roll=0x80 pitch=0x80 throttle=0x80 yaw=0x80")
        tk.Label(telem, textvariable=self.telem_var, font=mono, fg="#8fd6ff", bg="#2b2d38").pack()

        self.action_var = tk.StringVar(value="Ready. Click this window, then fly.")
        tk.Label(right, textvariable=self.action_var, font=mono, fg="#cccccc", bg="#1e1f26",
                 wraplength=420, justify="left").pack(pady=6, anchor="w")

        help_text = (
            "T = takeoff        L = land (EXPERIMENTAL, 10s)   C = toggle camera dir\n"
            "R = start/stop video record   P = photo save\n"
            "W/S = forward/back     A/D = roll (tested/opposite)\n"
            "Up/Down = throttle      Left/Right = camera pan\n\n"
            "Hold K + I together = EMERGENCY STOP\n"
            "Hold Q + I together = QUIT (kills first)\n\n"
            f"Victim captures auto-save (max once every {VICTIM_SAVE_COOLDOWN_SECONDS:.0f}s)\n"
            "when a person is detected - see gallery, top-left."
        )
        tk.Label(right, text=help_text, font=mono, fg="#888888", bg="#1e1f26",
                 justify="left").pack(pady=10, anchor="w")

        self.log_box = tk.Listbox(right, height=8, bg="#111218", fg="#7CFC00", font=mono,
                                   highlightthickness=0, borderwidth=0)
        self.log_box.pack(fill="both", expand=True, pady=(4, 0))

    def _log(self, msg):
        self.log_box.insert(tk.END, msg)
        self.log_box.yview_moveto(1.0)

    #victim gallery
    def _refresh_gallery_strip(self):
        """Re-reads the victims folder and redraws the inline thumbnail strip.
        Runs on its own timer, fully decoupled from the video/flight loops -
        a stalled camera or a missing PIL install can never affect flying."""
        all_paths = list_victim_captures()
        self.victim_count_var.set(f"({len(all_paths)})")

        for w in self._gallery_thumb_widgets:
            w.destroy()
        self._gallery_thumb_widgets = []

        recent = all_paths[:GALLERY_MAX_STRIP_THUMBS]
        if not recent:
            lbl = tk.Label(self.gallery_strip, text="No captures yet", fg="#666666",
                            bg="#1e1f26", font=("Courier", 9))
            lbl.pack(side="left")
            self._gallery_thumb_widgets.append(lbl)
        elif not VIDEO_AVAILABLE:
            lbl = tk.Label(self.gallery_strip, text=f"{len(recent)} saved (install pillow to preview)",
                            fg="#666666", bg="#1e1f26", font=("Courier", 9))
            lbl.pack(side="left")
            self._gallery_thumb_widgets.append(lbl)
        else:
            for path in recent:
                try:
                    img = Image.open(path)
                    img.thumbnail(GALLERY_THUMB_SIZE)
                    photo = ImageTk.PhotoImage(img)
                except Exception:
                    continue
                thumb = tk.Label(self.gallery_strip, image=photo, bg="#000000", cursor="hand2")
                thumb.image = photo  # keep a reference or Tkinter will garbage-collect it
                thumb.pack(side="left", padx=2)
                thumb.bind("<Button-1>", lambda e, p=path: self._show_full_image(p))
                self._gallery_thumb_widgets.append(thumb)

        self.after(GALLERY_REFRESH_MS, self._refresh_gallery_strip)

    def _show_full_image(self, path):
        """Opens one capture at a larger size in its own window."""
        top = tk.Toplevel(self)
        top.title(os.path.basename(path))
        top.configure(bg="#000000")
        if not VIDEO_AVAILABLE:
            tk.Label(top, text="pip install pillow to preview images", fg="white",
                     bg="#000000").pack(padx=20, pady=20)
            return
        try:
            img = Image.open(path)
            img.thumbnail(FULL_VIEW_MAX_SIZE)
            photo = ImageTk.PhotoImage(img)
            lbl = tk.Label(top, image=photo, bg="#000000")
            lbl.image = photo
            lbl.pack()
        except Exception as e:
            tk.Label(top, text=f"Could not open image: {e}", fg="white", bg="#000000").pack(padx=20, pady=20)

    def _open_gallery_window(self):
        """Full scrollable grid of every victim capture saved so far."""
        top = tk.Toplevel(self)
        top.title("All Victim Captures")
        top.geometry("640x480")
        top.configure(bg="#1e1f26")

        canvas = tk.Canvas(top, bg="#1e1f26", highlightthickness=0)
        scrollbar = tk.Scrollbar(top, orient="vertical", command=canvas.yview)
        grid_frame = tk.Frame(canvas, bg="#1e1f26")

        grid_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=grid_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        paths = list_victim_captures()
        if not paths:
            tk.Label(grid_frame, text="No captures yet.", fg="#888888", bg="#1e1f26").pack(padx=20, pady=20)
            return
        if not VIDEO_AVAILABLE:
            tk.Label(grid_frame, text=f"{len(paths)} files saved - install pillow to preview them.",
                     fg="#888888", bg="#1e1f26").pack(padx=20, pady=20)
            return

        cols = 4
        thumb_refs = []
        for i, path in enumerate(paths):
            try:
                img = Image.open(path)
                img.thumbnail((130, 100))
                photo = ImageTk.PhotoImage(img)
            except Exception:
                continue
            thumb_refs.append(photo)
            cell = tk.Frame(grid_frame, bg="#1e1f26")
            cell.grid(row=i // cols, column=i % cols, padx=6, pady=6)
            lbl = tk.Label(cell, image=photo, bg="#000000", cursor="hand2")
            lbl.pack()
            lbl.bind("<Button-1>", lambda e, p=path: self._show_full_image(p))
            tk.Label(cell, text=os.path.basename(path), fg="#888888", bg="#1e1f26",
                     font=("Courier", 7)).pack()
        top.thumb_refs = thumb_refs

    def _update_video(self):
        if self.video is None:
            self.video_label.configure(
                text="Video disabled.\npip install opencv-python ultralytics pillow",
                image=""
            )
        else:
            frame = self.video.get_latest()
            if frame is not None:
                img = Image.fromarray(frame).resize(VIDEO_DISPLAY_SIZE)
                imgtk = ImageTk.PhotoImage(image=img)
                self.video_label.imgtk = imgtk
                self.video_label.configure(image=imgtk, text="")
            else:
                self.video_label.configure(text=f"Camera: {self.video.status}", image="")
        self.after(VIDEO_REFRESH_MS, self._update_video)

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
            self._enqueue(f"Landing (failsafe - no commands for {LAND_FAILSAFE_SECONDS:.0f}s)...",
                           lambda: self.drone.land_failsafe(on_progress=self._land_progress),
                           done_msg="Failsafe wait finished - check if it actually landed.")
        elif key == "c":
            self._enqueue("Toggling camera direction...", self._do_toggle_camera,
                           done_msg="Camera direction toggled.")
        elif key == "r":
            self._toggle_recording()
        elif key == "p":
            self._take_snapshot()

    def _toggle_recording(self):
        if self.video is None:
            self._log("» video unavailable")
            return
        if self.video.recording:
            self.video.stop_recording()
            self._log("» recording stopped")
            self.action_var.set("Recording stopped.")
        else:
            self.video.start_recording()
            self._log("» recording started")
            self.action_var.set("Recording started.")

    def _take_snapshot(self):
        if self.video is None:
            self._log("» video unavailable")
            return
        path = self.video.save_snapshot()
        if path:
            self._log(f"» photo saved: {path}")
            self.action_var.set("Photo saved.")
        else:
            self._log("» no frame available")
            self.action_var.set("No frame to save.")

    def _do_toggle_camera(self):
        now_down = self.drone.toggle_camera_direction()
        label = "downward" if now_down else "forward"
        self.after(0, lambda: self.camera_dir_var.set(f"Camera: {label}"))

    def _handle_combo_keys(self):
        both_ki = "k" in self.pressed and "i" in self.pressed
        both_qi = "q" in self.pressed and "i" in self.pressed

        if both_ki and not self.kill_armed_guard:
            self.kill_armed_guard = True
            self._fire_kill_now()

        if both_qi and not self.quit_armed_guard:
            self.quit_armed_guard = True
            self._quit()

    def _land_progress(self, remaining_seconds):
        self.after(0, lambda: self.telem_var.set(
            f"waiting for failsafe... {remaining_seconds:.1f}s left (no commands being sent)"
        ))

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
            #Arpit
            self.status_var.set("DISARMED")
            self.status_label.config(fg="#ff5555")

    def _compute_axes(self):
        b2, b3, b4, b5 = CENTER, CENTER, self.drone.throttle, CENTER

        if "w" in self.pressed:
            b3 = STICK_MAX
        elif "s" in self.pressed:
            b3 = STICK_MIN

        if "a" in self.pressed:
            b2 = STICK_MIN
        elif "d" in self.pressed:
            b2 = STICK_MAX

        if "up" in self.pressed:
            b4 = min(STICK_MAX, self.drone.throttle + 4)
        elif "down" in self.pressed:
            b4 = max(STICK_MIN, self.drone.throttle - 4)

        if "left" in self.pressed:
            b5 = 0x01
        elif "right" in self.pressed:
            b5 = 0xFF

        return b2, b3, b4, b5

    def _loop(self):
        if not self.busy:
            b2, b3, b4, b5 = self._compute_axes()
            if "up" in self.pressed or "down" in self.pressed:
                self.drone.throttle = b4
            self.drone.send_axes(b2, b3, b4, b5, cmd=CMD_IDLE)
            self.telem_var.set(f"roll=0x{b2:02X} pitch=0x{b3:02X} throttle=0x{b4:02X} yaw=0x{b5:02X}")
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
        if self.video:
            self.video.stop()
        self.destroy()


if __name__ == "__main__":
    DroneApp().mainloop()