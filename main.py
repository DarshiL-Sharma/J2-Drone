"""
Drone Control - Tkinter GUI with keyboard flying + live camera/object detection.

Requires:
    pip install opencv-python ultralytics pillow
(tkinter itself is standard library - no install needed for the GUI/keyboard part)

The first run will auto-download yolov8n.pt (a few MB) via ultralytics - that
happens once and can take a moment depending on your connection.

CONTROLS (window must be focused - click on it once before flying):
    T           - takeoff
    L           - land: EXPERIMENTAL. Stops sending ANY commands for 10
                  seconds, hoping the drone's own connection-loss failsafe
                  lands it automatically (matching what you remember seeing
                  with the old typed-command script). We tested this at 4s
                  and it did NOT trigger a landing, so this is now 10s as a
                  next guess - not yet re-confirmed. During this window you
                  have ZERO manual control of the drone. K+I still works
                  (runs on its own thread). A verified alternative exists in
                  code as Drone.land_ramp() (throttle-to-zero, confirmed
                  from your packet capture) if this approach keeps failing.
    C           - toggle camera direction: forward <-> downward

    W / S       - forward / backward           (pitch)
    A / D       - roll - tested / opposite pattern
    Up / Down   - throttle up / down            (climb / descend)
    Left/Right  - camera pan - direction A / B

    K + I  (hold BOTH together)  - EMERGENCY STOP (deliberately a two-key
                                    combo so you can't kill it by accident)
    Q + I  (hold BOTH together)  - quit the program (sends kill first)

    Hold any movement key and it keeps sending that direction continuously,
    at ~20Hz, for as long as it's held - exactly like a real stick. A
    background heartbeat keeps sending idle/current-position frames even
    when nothing is pressed, so the drone never loses its connection and
    auto-lands on you mid-flight.

Protocol basis (from packet captures):
    03 66 [B2] [B3] [B4] [B5] [CMD] [CHK] 99
           Roll Pitch Throttle Yaw   Cmd   Checksum = B2^B3^B4^B5^CMD
    CMD 0x00 = idle, CMD 0x01 = takeoff, CMD 0x04 = kill.
    Axes range ~0x58 (min) to 0xA8 (max) around center 0x80.
    Landing = throttle ramped to 0x00 (no dedicated land CMD exists).

    Camera direction is a separate, standalone 2-byte datagram (not part of
    the 03 66 ... 99 flight frame above):
        06 01 = camera facing forward
        06 02 = camera facing downward
"""

import socket
import time
import threading
import queue
import tkinter as tk
from tkinter import font as tkfont

try:
    import cv2
    from ultralytics import YOLO
    from PIL import Image, ImageTk
    VIDEO_AVAILABLE = True
except ImportError:
    VIDEO_AVAILABLE = False  # video panel will show an install hint instead of crashing

DRONE_IP = "192.168.1.1"
DRONE_PORT = 7099

RTSP_URL = "rtsp://192.168.1.1:7070/webcam"
YOLO_MODEL_PATH = "software/yolov8n.pt"
VIDEO_DISPLAY_SIZE = (480, 360)   # width, height shown in the GUI
VIDEO_REFRESH_MS = 50             # how often the GUI polls for a new frame (~20fps ceiling)

CENTER = 0x80
MAX_DEV = 0x28
STICK_MAX = CENTER + MAX_DEV     # 0xA8
STICK_MIN = CENTER - MAX_DEV     # 0x58

CMD_IDLE = 0x00
CMD_TAKEOFF = 0x01
CMD_KILL = 0x04

# Standalone camera-direction datagrams - separate from the flight frame protocol.
CAMERA_FORWARD_FRAME = bytes.fromhex("0601")
CAMERA_DOWN_FRAME = bytes.fromhex("0602")

SEND_INTERVAL_MS = 50            # ~20Hz, matches observed traffic rate
KEY_RELEASE_DEBOUNCE_MS = 60     # swallow OS key-repeat release/press flicker

LAND_FAILSAFE_SECONDS = 10.0


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
        self.camera_facing_down = False   # starts assuming forward-facing

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
        """The packet-capture-verified landing: ramp throttle down to zero.
        This is the one confirmed by your own capture (throttle dropping
        smoothly to 0x00 right before your kill command)."""
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
        """Alias for land() - kept so existing calls using this name still work."""
        return self.land(on_progress=on_progress, step=step, step_time=step_time)

    def land_failsafe(self, on_progress=None, duration=LAND_FAILSAFE_SECONDS):
        """Tested and did NOT work: stopping commands for ~4s did not make
        the drone land, meaning either this drone has no connection-loss
        failsafe, or its timeout is much longer than 4s. Left here in case
        you want to try a longer duration later - not currently wired to
        any key."""
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
        """Sends the standalone camera-direction datagram (06 01 / 06 02).
        This is NOT part of the 03 66 ... 99 flight frame - it's its own
        2-byte packet, fired once per toggle rather than repeated at 20Hz."""
        frame = CAMERA_DOWN_FRAME if face_down else CAMERA_FORWARD_FRAME
        self.sock.sendto(frame, self.addr)
        self.camera_facing_down = face_down

    def toggle_camera_direction(self):
        self.set_camera_direction(not self.camera_facing_down)
        return self.camera_facing_down


class VideoStream:
    """Reads the RTSP camera feed and runs YOLO detection in its own thread.

    Deliberately decoupled from Tkinter: this class knows nothing about the
    GUI. It just keeps `self.latest_frame` updated with the newest annotated
    frame (as an RGB numpy array), and the GUI polls get_latest() on its own
    timer. That's what stops slow video/inference from ever freezing the
    keyboard controls.
    """

    def __init__(self, url=RTSP_URL, model_path=YOLO_MODEL_PATH):
        self.url = url
        self.model_path = model_path
        self.cap = None
        self.latest_frame = None
        self.lock = threading.Lock()
        self.running = False
        self.status = "not started"

    def start(self):
        self.running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self.running = False

    def get_latest(self):
        with self.lock:
            return None if self.latest_frame is None else self.latest_frame.copy()

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
                annotated = results[0].plot()   # BGR numpy array with boxes drawn
            except Exception:
                annotated = frame               # fall back to raw frame if inference errors
            annotated_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            with self.lock:
                self.latest_frame = annotated_rgb

        if self.cap:
            self.cap.release()
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
        self._release_timers = {}          # key -> after() id, for debounce
        self.busy = False                   # true only while the queue worker is executing
        self.kill_armed_guard = False       # edge-trigger so combo fires once per hold
        self.quit_armed_guard = False

        # Regular actions (takeoff/land/calibrate/camera toggle) go through this queue
        # and run one at a time, in order - so pressing L while T is still finishing no
        # longer gets silently dropped, it just runs automatically right after.
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

        if VIDEO_AVAILABLE:
            self.video = VideoStream()
            self.video.start()
        else:
            self.video = None
        self._update_video()  # starts the GUI-side polling loop either way

        self.bind_all("<KeyPress>", self._on_key_press)
        self.bind_all("<KeyRelease>", self._on_key_release)
        self.protocol("WM_DELETE_WINDOW", self._quit)
        self.focus_set()

        self._loop()  # start the continuous send/telemetry loop

    # ---------------------------------------------------------------- UI
    def _build_ui(self):
        big = tkfont.Font(size=14, weight="bold")
        mono = tkfont.Font(family="Courier", size=11)

        header = tk.Label(self, text="DRONE CONTROL", font=big, fg="#ffffff", bg="#1e1f26")
        header.pack(pady=(12, 4))

        body = tk.Frame(self, bg="#1e1f26")
        body.pack(fill="both", expand=True, padx=16, pady=(4, 16))

        # ---- left column: live camera / YOLO detection panel ----
        left = tk.Frame(body, bg="#1e1f26")
        left.pack(side="left", fill="both", expand=False, padx=(0, 12))

        tk.Label(left, text="CAMERA", font=big, fg="#ffffff", bg="#1e1f26").pack(anchor="w")
        w, h = VIDEO_DISPLAY_SIZE
        # A plain Label's width/height are in TEXT units (chars/lines), not
        # pixels, until an image is set. Wrapping it in a fixed-pixel Frame
        # with pack_propagate(False) keeps the panel a fixed size from the
        # start, instead of ballooning to fit the placeholder text.
        video_frame = tk.Frame(left, bg="#000000", width=w, height=h)
        video_frame.pack_propagate(False)
        video_frame.pack()
        self.video_label = tk.Label(video_frame, text="Starting camera...", bg="#000000",
                                     fg="#888888", wraplength=w - 20, justify="center")
        self.video_label.pack(fill="both", expand=True)

        self.camera_dir_var = tk.StringVar(value="Camera: forward")
        tk.Label(left, textvariable=self.camera_dir_var, font=mono, fg="#8fd6ff",
                 bg="#1e1f26").pack(anchor="w", pady=(4, 0))

        # ---- right column: existing status / controls / log ----
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
            "W/S = forward/back     A/D = roll (tested/opposite)\n"
            "Up/Down = throttle      Left/Right = camera pan\n\n"
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

    # ------------------------------------------------------------- video
    def _update_video(self):
        """Polls the background VideoStream for its latest frame and displays
        it. Runs on its own Tkinter after() timer, independent of the flight
        loop, so a slow/stalled camera can never affect drone responsiveness."""
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
                self.video_label.imgtk = imgtk  # keep a reference - Tkinter needs this
                self.video_label.configure(image=imgtk, text="")
            else:
                self.video_label.configure(text=f"Camera: {self.video.status}", image="")
        self.after(VIDEO_REFRESH_MS, self._update_video)

    # ------------------------------------------------------------ keys
    def _on_key_press(self, event):
        key = event.keysym.lower()

        # DEBUG: logs every key press so you can confirm keys are actually
        # reaching this handler. If you press L and don't see this line at
        # all, the window doesn't have keyboard focus - click on it first.
        if key not in self._release_timers and key not in self.pressed:
            self._log(f"[key] {key}")

        # cancel any pending "treat as released" timer - key is still down
        if key in self._release_timers:
            self.after_cancel(self._release_timers.pop(key))

        newly_pressed = key not in self.pressed
        self.pressed.add(key)

        if newly_pressed:
            self._handle_single_key(key)
        self._handle_combo_keys()

    def _on_key_release(self, event):
        key = event.keysym.lower()

        # don't remove immediately - OS key-repeat sends release+press rapidly
        # while a key is genuinely held. Wait a beat; if a fresh press cancels
        # this timer, we know it was just repeat noise, not a real release.
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
        # No "if busy: return" here anymore - these get queued instead of dropped.
        if key == "t":
            self._enqueue("Taking off...", self.drone.takeoff, done_msg="Airborne.")
        elif key == "l":
            self._enqueue(f"Landing (failsafe - no commands for {LAND_FAILSAFE_SECONDS:.0f}s)...",
                           lambda: self.drone.land_failsafe(on_progress=self._land_progress),
                           done_msg="Failsafe wait finished - check if it actually landed.")
        elif key == "c":
            self._enqueue("Toggling camera direction...", self._do_toggle_camera,
                           done_msg="Camera direction toggled.")

    def _do_toggle_camera(self):
        """Runs on the worker thread - flips camera_facing_down and fires the
        single 06 01 / 06 02 datagram, then updates the GUI label."""
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
        """Queue an action to run as soon as any currently-running one finishes -
        pressing a key while another action is mid-flight no longer gets ignored."""
        self._log(f"> queued: {name}")
        self.action_queue.put((name, fn, done_msg))

    def _worker_loop(self):
        """Single background worker - runs queued actions strictly one at a time,
        so takeoff/land/calibrate/camera-toggle frames never get sent on top of
        each other."""
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
        """Kill bypasses the queue entirely and fires immediately, even if a
        takeoff/land/calibrate/camera-toggle is currently mid-flight - safety
        comes first."""
        self._log("> EMERGENCY STOP (K+I)")
        # cancel anything waiting in line so it doesn't run right after the kill
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
        # Paused only while a queued action (T/L/C) is actively sending its own
        # frames, so we don't interleave a stray idle frame mid-takeoff/land.
        # Kill runs on its own thread outside this flag, so it's never delayed.
        if not self.busy:
            b2, b3, b4, b5 = self._compute_axes()
            if "up" in self.pressed or "down" in self.pressed:
                self.drone.throttle = b4
            self.drone.send_axes(b2, b3, b4, b5, cmd=CMD_IDLE)
            self.telem_var.set(f"roll=0x{b2:02X} pitch=0x{b3:02X} throttle=0x{b4:02X} yaw=0x{b5:02X}")
            self._log_movement_transition()
        self.after(SEND_INTERVAL_MS, self._loop)

    def _log_movement_transition(self):
        """Logs a line whenever a movement key starts/stops being held, so W/A/S/D
        etc. give visible confirmation they're actually being detected."""
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
