"""
`USE dashboard.py with main.py`
***needs python3
`just run 'python dashboard.py' to access controller` 

Ground Control Dashboard:

Wires control layer (main.py) into a live
Tkinter dashboard: on-screen buttons + keyboard hold-controls for flight,
a status/telemetry panel, and a video panel slot ('not ready' go to set_video_frame())

SAFETY - READ BEFORE FLYING FOR REAL:
  Only takeoff / land / kill / calibrate / forward are backed by CONFIRMED
  packet captures (see main.py's own docstring/comments). backward,
  roll_left, roll_right, and the camera pan buttons are UNCONFIRMED -
  they're shown in orange here for that reason

"""

import tkinter as tk
from tkinter import ttk
import threading
import time

from main import (
    Drone,
    build_frame,
    CENTER,
    STICK_MAX,
    STICK_MIN,
    CMD_IDLE,
    SEND_INTERVAL,
    DRONE_IP,
    DRONE_PORT,
)


class LiveControlState:
    """
    The dashboard's background sender reads this ~20 times a second and
    turns it into a packet, exactly like the real controller does.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.b2 = CENTER  # roll
        self.b3 = CENTER  # pitch
        self.b4 = CENTER  # throttle
        self.b5 = CENTER  # camera pan

    def set_axis(self, name, value):
        with self._lock:
            setattr(self, name, value)

    def reset_axis(self, name):
        with self._lock:
            setattr(self, name, CENTER)

    def snapshot(self):
        with self._lock:
            return self.b2, self.b3, self.b4, self.b5


#keyboard keys
KEY_MAP = {
    "w": ("b3", STICK_MAX, "Forward", True),
    "s": ("b3", STICK_MIN, "Backward  [unconfirmed]", False),
    "a": ("b2", STICK_MIN, "Roll 1  [dir. unconfirmed]", False),
    "d": ("b2", STICK_MAX, "Roll 2  [dir. unconfirmed]", False),
    "q": ("b5", 0x01, "Camera pan A  [unconfirmed]", False),
    "e": ("b5", 0xFF, "Camera pan B  [unconfirmed]", False),
}


class DroneDashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("J2 Control")
        self.geometry("980x600")
        self.configure(bg="#1e1e1e")

        self.drone = Drone(DRONE_IP, DRONE_PORT)
        self.state = LiveControlState()
        self.running = True

        self._build_ui()
        self._bind_keys()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.sender_thread = threading.Thread(target=self._send_loop, daemon=True)
        self.sender_thread.start()

    #interface
    def _build_ui(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        main = tk.Frame(self, bg="#1e1e1e")
        main.pack(fill="both", expand=True, padx=10, pady=10)

        #video panel
        video_frame = tk.Frame(main, bg="black", width=560, height=560)
        video_frame.pack(side="left", fill="both", expand=True)
        video_frame.pack_propagate(False)
        self.video_label = tk.Label(
            video_frame,
            text="Video feed not connected yet\n\n(see set_video_frame())",
            bg="black",
            fg="#888888",
            justify="center",
        )
        self.video_label.pack(fill="both", expand=True)

        #buttons
        right = tk.Frame(main, bg="#1e1e1e", width=380)
        right.pack(side="right", fill="y", padx=(10, 0))

        tk.Label(
            right, text="FLIGHT CONTROL", bg="#1e1e1e", fg="white",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=(0, 10))

        btn_row = tk.Frame(right, bg="#1e1e1e")
        btn_row.pack(fill="x", pady=5)
        self._make_button(btn_row, "TAKEOFF", "#34bd3b", self._takeoff).pack(
            side="left", expand=True, fill="x", padx=2
        )
        self._make_button(btn_row, "LAND", "#d0a700", self._land).pack(
            side="left", expand=True, fill="x", padx=2
        )
        self._make_button(btn_row, "KILL (Esc)", "#d60909", self._kill).pack(
            side="left", expand=True, fill="x", padx=2
        )

        move_frame = tk.LabelFrame(right, text="Movement (press & hold)", bg="#1e1e1e", fg="white")
        move_frame.pack(fill="x", pady=10)
        for key, (_, _, label, confirmed) in KEY_MAP.items():
            b = self._make_button(
                move_frame,
                f"{key.upper()}   {label}",
                "#647a85" if confirmed else "#8d5b00",
                None,
            )
            b.pack(fill="x", pady=2)
            b.bind("<ButtonPress-1>", lambda e, k=key: self._key_down(k))
            b.bind("<ButtonRelease-1>", lambda e, k=key: self._key_up(k))

        status_frame = tk.LabelFrame(right, text="Status", bg="#1e1e1e", fg="white")
        status_frame.pack(fill="x", pady=10)
        self.status_var = tk.StringVar(value="DISARMED - press TAKEOFF to start")
        tk.Label(
            status_frame, textvariable=self.status_var, bg="#1e1e1e", fg="#4fc3f7",
            wraplength=340, justify="left",
        ).pack(anchor="w", padx=5, pady=2)
        self.frame_var = tk.StringVar(value="last frame: -")
        tk.Label(
            status_frame, textvariable=self.frame_var, bg="#1e1e1e", fg="#9e9e9e",
            font=("Consolas", 9),
        ).pack(anchor="w", padx=5, pady=2)

        tk.Label(
            right,
            text="Gray = confirmed from packet capture\nOrange = unconfirmed, verify before real flight",
            bg="#1e1e1e", fg="#757575", justify="left", font=("Segoe UI", 8),
        ).pack(anchor="w", pady=(10, 0))

    def _make_button(self, parent, text, color, command):
        return tk.Button(
            parent, text=text, bg=color, fg="white", activebackground=color,
            relief="flat", command=command, font=("Segoe UI", 10, "bold"),
            padx=6, pady=6,
        )

    #keyboard cntrl
    def _bind_keys(self):
        for key in KEY_MAP:
            self.bind(f"<KeyPress-{key}>", lambda e, k=key: self._key_down(k))
            self.bind(f"<KeyRelease-{key}>", lambda e, k=key: self._key_up(k))
        self.bind("<Escape>", lambda e: self._kill())

    def _key_down(self, key):
        axis, value, _, _ = KEY_MAP[key]
        self.state.set_axis(axis, value)

    def _key_up(self, key):
        axis, _, _, _ = KEY_MAP[key]
        self.state.reset_axis(axis)

    #drone act
    def _run_async(self, fn):
        threading.Thread(target=fn, daemon=True).start()

    def _takeoff(self):
        self.status_var.set("Taking off...")

        def go():
            self.drone.takeoff()
            self.status_var.set("ARMED - flying")

        self._run_async(go)

    def _land(self):
        self.status_var.set("Landing...")

        def go():
            self.drone.land()
            self.status_var.set("DISARMED - landed")

        self._run_async(go)

    def _kill(self):
        self.status_var.set("EMERGENCY STOP")

        def go():
            self.drone.kill()
            self.status_var.set("DISARMED - kill switch used")

        self._run_async(go)

    def _send_loop(self):
        while self.running:
            b2, b3, b4, b5 = self.state.snapshot()
            frame = build_frame(b2=b2, b3=b3, b4=b4, b5=b5, cmd=CMD_IDLE)
            self.drone._send(frame)
            self.frame_var.set(f"last frame: {frame.hex(' ')}")
            time.sleep(SEND_INTERVAL)

    def _on_close(self):
        self.status_var.set("Closing - sending kill for safety...")
        self.running = False
        try:
            self.drone.kill()
        except Exception:
            pass
        self.destroy()

    #video integrattion
    def set_video_frame(self, pil_image):
        #opencv
        pass


if __name__ == "__main__":
    app = DroneDashboard()
    app.mainloop()
