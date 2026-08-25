"""Tkinter ground-control dashboard and gallery UI

It wires Drone and VideoStream into the UI
"""

import os
import queue
import threading
import time
import tkinter as tk
from tkinter import font as tkfont, ttk

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    Image = None
    ImageTk = None
    PIL_AVAILABLE = False

from config import (
    CENTER,
    CMD_IDLE,
    DRONE_IP,
    DRONE_PORT,
    FIRE_SAVE_COOLDOWN_SECONDS,
    FULL_VIEW_MAX_SIZE,
    GALLERY_MAX_STRIP_THUMBS,
    GALLERY_REFRESH_MS,
    GALLERY_THUMB_SIZE,
    KEY_MAP,
    KEY_RELEASE_DEBOUNCE_MS,
    LAND_FAILSAFE_SECONDS,
    SEND_INTERVAL_MS,
    STICK_MAX,
    STICK_MIN,
    THROTTLE_STEP,
    VICTIM_DIR,
    VICTIM_SAVE_COOLDOWN_SECONDS,
    VIDEO_DISPLAY_SIZE,
    VIDEO_REFRESH_MS,
)
from drone import Drone
from video_stream import VideoStream, VIDEO_STREAM_AVAILABLE

VIDEO_AVAILABLE = VIDEO_STREAM_AVAILABLE and PIL_AVAILABLE


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


class DroneDashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("J2 Control - Ground Control Dashboard")
        self.geometry("1180x680")
        self.configure(bg="#1e1e1e")

        self.drone = Drone(DRONE_IP, DRONE_PORT)
        self.video = VideoStream() if VIDEO_AVAILABLE else None

        self.pressed = set()
        self._release_timers = {}
        self.busy = False
        self.running = True
        self.kill_armed_guard = False
        self.quit_armed_guard = False
        self.action_queue = queue.Queue()

        self._move_key_labels = {
            "w": "forward", "s": "backward",
            "a": "roll (tested)", "d": "roll (opposite)",
            "up": "throttle up", "down": "throttle down",
            "left": "camera pan A", "right": "camera pan B",
        }
        self._last_active_move_keys = frozenset()

        self._build_ui()
        self._bind_keys()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        threading.Thread(target=self._worker_loop, daemon=True).start()
        self.sender_thread = threading.Thread(target=self._send_loop, daemon=True)
        self.sender_thread.start()

        if self.video:
            self.video.start()
        self._update_video()
        self._refresh_gallery_strip()
        self.focus_set()

    #UI
    def _build_ui(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        mono = tkfont.Font(family="Consolas", size=9)

        main = tk.Frame(self, bg="#1e1e1e")
        main.pack(fill="both", expand=True, padx=10, pady=10)

        #left: video + gallery
        left = tk.Frame(main, bg="#1e1e1e")
        left.pack(side="left", fill="both", expand=True)

        w, h = VIDEO_DISPLAY_SIZE
        video_frame = tk.Frame(left, bg="black", width=w, height=h)
        video_frame.pack(fill="x")
        video_frame.pack_propagate(False)
        self.video_label = tk.Label(
            video_frame,
            text="Starting camera...",
            bg="black",
            fg="#888888",
            justify="center",
        )
        self.video_label.pack(fill="both", expand=True)

        status_row = tk.Frame(left, bg="#1e1e1e")
        status_row.pack(fill="x", pady=(4, 0))
        self.camera_dir_var = tk.StringVar(value="Camera: forward")
        tk.Label(status_row, textvariable=self.camera_dir_var, bg="#1e1e1e",
                 fg="#4fc3f7", font=mono).pack(side="left")
        self.fire_status_var = tk.StringVar(value="Fire: clear")
        self.fire_status_label = tk.Label(status_row, textvariable=self.fire_status_var,
                                           bg="#1e1e1e", fg="#7CFC00", font=mono)
        self.fire_status_label.pack(side="right")

        gallery_header = tk.Frame(left, bg="#1e1e1e")
        gallery_header.pack(fill="x", pady=(12, 4))
        tk.Label(gallery_header, text="VICTIM CAPTURES", bg="#1e1e1e", fg="white",
                 font=("Segoe UI", 11, "bold")).pack(side="left")
        self.victim_count_var = tk.StringVar(value="(0)")
        tk.Label(gallery_header, textvariable=self.victim_count_var, bg="#1e1e1e",
                 fg="#ffb347", font=mono).pack(side="left", padx=(6, 0))

        self.gallery_strip = tk.Frame(left, bg="#1e1e1e")
        self.gallery_strip.pack(fill="x")
        self._gallery_thumb_widgets = []

        tk.Button(left, text="View All Captures", command=self._open_gallery_window,
                  bg="#33475b", fg="white", activebackground="#3d5871", relief="flat",
                  font=mono).pack(fill="x", pady=(6, 0))

        log_frame = tk.LabelFrame(left, text="Log", bg="#1e1e1e", fg="white")
        log_frame.pack(fill="both", expand=True, pady=(10, 0))
        self.log_box = tk.Listbox(log_frame, height=6, bg="#111218", fg="#7CFC00",
                                   font=mono, highlightthickness=0, borderwidth=0)
        self.log_box.pack(fill="both", expand=True)

        # ---------------- right: controls ----------------
        right = tk.Frame(main, bg="#1e1e1e", width=400)
        right.pack(side="right", fill="y", padx=(10, 0))
        right.pack_propagate(False)

        tk.Label(right, text="FLIGHT CONTROL", bg="#1e1e1e", fg="white",
                 font=("Segoe UI", 14, "bold")).pack(pady=(0, 10))

        top_row = tk.Frame(right, bg="#1e1e1e")
        top_row.pack(fill="x", pady=5)
        self._make_button(top_row, "TAKEOFF (T)", "#34bd3b", self._takeoff).pack(
            side="left", expand=True, fill="x", padx=2)
        self._make_button(top_row, "LAND (L)", "#d0a700", self._land).pack(
            side="left", expand=True, fill="x", padx=2)
        self._make_button(top_row, "KILL (Esc / K+I)", "#d60909", self._kill).pack(
            side="left", expand=True, fill="x", padx=2)

        util_row = tk.Frame(right, bg="#1e1e1e")
        util_row.pack(fill="x", pady=5)
        self._make_button(util_row, "Calibrate", "#647a85", self._calibrate).pack(
            side="left", expand=True, fill="x", padx=2)
        self._make_button(util_row, "Camera dir (C)", "#8d5b00", self._do_toggle_camera).pack(
            side="left", expand=True, fill="x", padx=2)

        cap_row = tk.Frame(right, bg="#1e1e1e")
        cap_row.pack(fill="x", pady=5)
        self.record_btn = self._make_button(cap_row, "Record (R)", "#647a85", self._toggle_recording)
        self.record_btn.pack(side="left", expand=True, fill="x", padx=2)
        self._make_button(cap_row, "Photo (P)", "#647a85", self._take_snapshot).pack(
            side="left", expand=True, fill="x", padx=2)

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

        throttle_frame = tk.LabelFrame(right, text="Throttle  [unconfirmed]", bg="#1e1e1e", fg="white")
        throttle_frame.pack(fill="x", pady=(0, 10))
        up_b = self._make_button(throttle_frame, "UP   Throttle +", "#8d5b00", None)
        up_b.pack(fill="x", pady=2)
        up_b.bind("<ButtonPress-1>", lambda e: self._key_down("up"))
        up_b.bind("<ButtonRelease-1>", lambda e: self._key_up("up"))
        down_b = self._make_button(throttle_frame, "DOWN   Throttle -", "#8d5b00", None)
        down_b.pack(fill="x", pady=2)
        down_b.bind("<ButtonPress-1>", lambda e: self._key_down("down"))
        down_b.bind("<ButtonRelease-1>", lambda e: self._key_up("down"))

        status_frame = tk.LabelFrame(right, text="Status", bg="#1e1e1e", fg="white")
        status_frame.pack(fill="x", pady=10)
        self.status_var = tk.StringVar(value="DISARMED - press TAKEOFF to start")
        self.status_label = tk.Label(status_frame, textvariable=self.status_var, bg="#1e1e1e",
                                      fg="#ff5555", wraplength=340, justify="left")
        self.status_label.pack(anchor="w", padx=5, pady=2)
        self.action_var = tk.StringVar(value="Ready. Click this window, then fly.")
        tk.Label(status_frame, textvariable=self.action_var, bg="#1e1e1e", fg="#cccccc",
                 wraplength=340, justify="left", font=mono).pack(anchor="w", padx=5, pady=2)
        self.telem_var = tk.StringVar(value=f"roll=0x{CENTER:02X} pitch=0x{CENTER:02X} "
                                             f"throttle=0x{CENTER:02X} yaw=0x{CENTER:02X}")
        tk.Label(status_frame, textvariable=self.telem_var, bg="#1e1e1e", fg="#9e9e9e",
                 font=mono).pack(anchor="w", padx=5, pady=2)

        tk.Label(
            right,
            text=(
                "Gray = confirmed from packet capture\n"
                "Orange = unconfirmed, verify before real flight\n\n"
                "W/S/A/D or the buttons above to fly, Up/Down for throttle,\n"
                "Left/Right for camera pan. T/L/C/R/P also work as keys.\n"
                "Hold K+I = emergency stop.  Hold Q+I = quit (kills first).\n\n"
                f"Victim captures auto-save every {VICTIM_SAVE_COOLDOWN_SECONDS:.0f}s max "
                "(see gallery, left).\n"
                f"Fire captures auto-save every {FIRE_SAVE_COOLDOWN_SECONDS:.0f}s max "
                "to output/fire."
            ),
            bg="#1e1e1e", fg="#757575", justify="left", font=("Segoe UI", 8),
        ).pack(anchor="w", pady=(6, 0))

    def _make_button(self, parent, text, color, command):
        return tk.Button(
            parent, text=text, bg=color, fg="white", activebackground=color,
            relief="flat", command=command, font=("Segoe UI", 10, "bold"),
            padx=6, pady=6,
        )

    def _log(self, msg):
        self.log_box.insert(tk.END, msg)
        self.log_box.yview_moveto(1.0)

    #keyboard (global)
    def _bind_keys(self):
        # bind_all (not bind) so keyboard flying keeps working no matter
        # which widget currently has focus - carried over from the old
        # built-in DroneApp GUI.
        self.bind_all("<KeyPress>", self._on_key_press)
        self.bind_all("<KeyRelease>", self._on_key_release)
        self.bind_all("<Escape>", lambda e: self._kill())

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

        # debounced so OS key-repeat (press/release flicker while a key is
        # held down) doesn't register as the key being let go
        self._release_timers[key] = self.after(KEY_RELEASE_DEBOUNCE_MS, actually_release)

    def _handle_single_key(self, key):
        if key == "t":
            self._takeoff()
        elif key == "l":
            self._land()
        elif key == "c":
            self._do_toggle_camera()
        elif key == "r":
            self._toggle_recording()
        elif key == "p":
            self._take_snapshot()

    def _handle_combo_keys(self):
        both_ki = "k" in self.pressed and "i" in self.pressed
        both_qi = "q" in self.pressed and "i" in self.pressed

        if both_ki and not self.kill_armed_guard:
            self.kill_armed_guard = True
            self._kill()

        if both_qi and not self.quit_armed_guard:
            self.quit_armed_guard = True
            self._quit_combo()

    #movement (keys+buttons)
    def _key_down(self, key):
        self.pressed.add(key)

    def _key_up(self, key):
        self.pressed.discard(key)

    def _compute_axes(self):
        b2, b3, b4, b5 = CENTER, CENTER, self.drone.throttle, CENTER
        for key, (axis, value, _, _) in KEY_MAP.items():
            if key in self.pressed:
                if axis == "b2":
                    b2 = value
                elif axis == "b3":
                    b3 = value
                elif axis == "b5":
                    b5 = value
        if "up" in self.pressed:
            b4 = min(STICK_MAX, self.drone.throttle + THROTTLE_STEP)
        elif "down" in self.pressed:
            b4 = max(STICK_MIN, self.drone.throttle - THROTTLE_STEP)
        return b2, b3, b4, b5

    def _send_loop(self):
        while self.running:
            if not self.busy:
                b2, b3, b4, b5 = self._compute_axes()
                if "up" in self.pressed or "down" in self.pressed:
                    self.drone.throttle = b4
                self.drone.send_axes(b2, b3, b4, b5, cmd=CMD_IDLE)
                telem = f"roll=0x{b2:02X} pitch=0x{b3:02X} throttle=0x{b4:02X} yaw=0x{b5:02X}"
                self.after(0, lambda t=telem: self.telem_var.set(t))
                self._log_movement_transition()
            time.sleep(SEND_INTERVAL_MS / 1000.0)

    def _log_movement_transition(self):
        active = frozenset(k for k in self.pressed if k in self._move_key_labels)
        if active == self._last_active_move_keys:
            return
        self._last_active_move_keys = active
        if active:
            labels = ", ".join(self._move_key_labels[k] for k in active)
            msg = f"» moving: {labels}"
        else:
            msg = "» centered / hover"
        self.after(0, lambda m=msg: self._log(m))

    #worker/queue actions
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

    def _update_status(self):
        if self.drone.armed:
            self.status_var.set("ARMED - flying")
            self.status_label.config(fg="#55ff55")
        else:
            self.status_var.set("DISARMED")
            self.status_label.config(fg="#ff5555")

    def _takeoff(self):
        self._enqueue("Taking off...", self.drone.takeoff, done_msg="Airborne.")

    def _land(self):
        self._enqueue(
            f"Landing (failsafe - no commands for {LAND_FAILSAFE_SECONDS:.0f}s)...",
            lambda: self.drone.land_failsafe(on_progress=self._land_progress),
            done_msg="Failsafe wait finished - check if it actually landed.",
        )

    def _land_progress(self, remaining_seconds):
        self.after(0, lambda: self.telem_var.set(
            f"waiting for failsafe... {remaining_seconds:.1f}s left (no commands being sent)"
        ))

    def _calibrate(self):
        self._enqueue("Calibrating...", self.drone.calibrate, done_msg="Calibrated.")

    def _kill(self):
        self._log("> EMERGENCY STOP")
        try:
            while True:
                self.action_queue.get_nowait()
        except queue.Empty:
            pass

        def worker():
            self.drone.kill()
            self.after(0, lambda: self._finish_action("Motors cut."))

        threading.Thread(target=worker, daemon=True).start()

    def _do_toggle_camera(self):
        self._enqueue("Toggling camera direction...", self._toggle_camera_blocking,
                       done_msg="Camera direction toggled.")

    def _toggle_camera_blocking(self):
        now_down = self.drone.toggle_camera_direction()
        label = "downward" if now_down else "forward"
        self.after(0, lambda: self.camera_dir_var.set(f"Camera: {label}"))

    def _toggle_recording(self):
        if self.video is None:
            self._log("» video unavailable")
            return
        if self.video.recording:
            self.video.stop_recording()
            self._log("» recording stopped")
            self.action_var.set("Recording stopped.")
            self.record_btn.config(text="Record (R)", bg="#647a85", activebackground="#647a85")
        else:
            self.video.start_recording()
            self._log("» recording started")
            self.action_var.set("Recording started.")
            self.record_btn.config(text="Stop (R)", bg="#d60909", activebackground="#d60909")

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

    #video
    def _update_video(self):
        if self.video is None:
            self.video_label.configure(
                text="Video disabled.\npip install opencv-python ultralytics pillow numpy",
                image="",
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

    #victim gallery
    def _refresh_gallery_strip(self):
        all_paths = list_victim_captures()
        self.victim_count_var.set(f"({len(all_paths)})")

        for w in self._gallery_thumb_widgets:
            w.destroy()
        self._gallery_thumb_widgets = []

        recent = all_paths[:GALLERY_MAX_STRIP_THUMBS]
        if not recent:
            lbl = tk.Label(self.gallery_strip, text="No captures yet", fg="#666666",
                            bg="#1e1e1e", font=("Courier", 9))
            lbl.pack(side="left")
            self._gallery_thumb_widgets.append(lbl)
        elif not VIDEO_AVAILABLE:
            lbl = tk.Label(self.gallery_strip, text=f"{len(recent)} saved (install pillow to preview)",
                            fg="#666666", bg="#1e1e1e", font=("Courier", 9))
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
                thumb.image = photo
                thumb.pack(side="left", padx=2)
                thumb.bind("<Button-1>", lambda e, p=path: self._show_full_image(p))
                self._gallery_thumb_widgets.append(thumb)

        if self.video is not None:
            if self.video.fire_active:
                self.fire_status_var.set("Fire: DETECTED")
                self.fire_status_label.config(fg="#ff5555")
            else:
                self.fire_status_var.set("Fire: clear")
                self.fire_status_label.config(fg="#7CFC00")

        self.after(GALLERY_REFRESH_MS, self._refresh_gallery_strip)

    def _show_full_image(self, path):
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
        top = tk.Toplevel(self)
        top.title("All Victim Captures")
        top.geometry("640x480")
        top.configure(bg="#1e1e1e")

        canvas = tk.Canvas(top, bg="#1e1e1e", highlightthickness=0)
        scrollbar = tk.Scrollbar(top, orient="vertical", command=canvas.yview)
        grid_frame = tk.Frame(canvas, bg="#1e1e1e")

        grid_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=grid_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Mouse wheel / touchpad scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def on_linux_scroll_up(event):
            canvas.yview_scroll(-3, "units")

        def on_linux_scroll_down(event):
            canvas.yview_scroll(3, "units")

        # Bind to the gallery window AND its children
        top.bind_all("<MouseWheel>", on_mousewheel)
        top.bind_all("<Button-4>", on_linux_scroll_up)
        top.bind_all("<Button-5>", on_linux_scroll_down)

        def close_gallery():
            top.unbind_all("<MouseWheel>")
            top.unbind_all("<Button-4>")
            top.unbind_all("<Button-5>")
            top.destroy()

        top.protocol("WM_DELETE_WINDOW", close_gallery)

        paths = list_victim_captures()
        if not paths:
            tk.Label(grid_frame, text="No captures yet.", fg="#888888", bg="#1e1e1e").pack(padx=20, pady=20)
            return
        if not VIDEO_AVAILABLE:
            tk.Label(grid_frame, text=f"{len(paths)} files saved - install pillow to preview them.",
                     fg="#888888", bg="#1e1e1e").pack(padx=20, pady=20)
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
            cell = tk.Frame(grid_frame, bg="#1e1e1e")
            cell.grid(row=i // cols, column=i % cols, padx=6, pady=6)
            lbl = tk.Label(cell, image=photo, bg="#000000", cursor="hand2")
            lbl.pack()
            lbl.bind("<Button-1>", lambda e, p=path: self._show_full_image(p))
            tk.Label(cell, text=os.path.basename(path), fg="#888888", bg="#1e1e1e",
                     font=("Courier", 7)).pack()
        top.thumb_refs = thumb_refs

    #close
    def _shutdown(self):
        self.running = False
        try:
            self.drone.kill()
        except Exception:
            pass
        if self.video:
            self.video.stop()

    def _on_close(self):
        self.status_var.set("Closing - sending kill for safety...")
        self._shutdown()
        self.destroy()

    def _quit_combo(self):
        self._log("> Quitting (Q+I) - sending kill first.")
        self._shutdown()
        self.destroy()
