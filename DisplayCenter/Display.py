from ConstantsCenter.constants import (
    VIDEO_DISPLAY_SIZE,
    VIDEO_REFRESH_MS,
    FIRE_SAVE_COOLDOWN_SECONDS,
    CENTER,
    STICK_MAX,
    STICK_MIN,
    CMD_IDLE,
    SEND_INTERVAL_MS,
    KEY_RELEASE_DEBOUNCE_MS,
    LAND_FAILSAFE_SECONDS,
    VICTIM_SAVE_COOLDOWN_SECONDS,
    GALLERY_THUMB_SIZE,
    GALLERY_MAX_STRIP_THUMBS,
    GALLERY_REFRESH_MS,
    FULL_VIEW_MAX_SIZE,
    SOS_REFRESH_MS,
    SOS_THUMB_SIZE,
)
from CommunicationCenter.communication import list_victim_captures, list_fire_captures
from CommunicationCenter.sos_store import list_sos_reports

from CommandsCenter.Commands import Drone
from CommunicationCenter.Streaming import VideoStream
import threading
import queue
import tkinter as tk
from tkinter import font as tkfont
import os
try:
    import cv2
    import numpy as np
    from ultralytics import YOLO
    from PIL import Image, ImageTk
    VIDEO_AVAILABLE = True
except ImportError:
    VIDEO_AVAILABLE = False

# ---- palette (visual style only - no functional meaning) ----
BG = "#14151b"
PANEL_BG = "#1b1d26"
CARD_BG = "#20222c"
BORDER = "#2c2f3d"
ACCENT = "#8fd6ff"
GREEN = "#5be36a"
RED = "#ff5555"
AMBER = "#ffb347"
MUTED = "#777f8f"
TEXT = "#e8e9ee"


class DroneApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Drone Control")
        self.geometry("1320x800")
        self.minsize(1080, 620)
        self.configure(bg=BG)

        self.drone = Drone()
        self.video = None  # set below, but must exist before _refresh_galleries()
                            # (called from _build_ui path) checks it
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
        self._refresh_galleries()
        self._refresh_sos()

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

    # ================= UI BUILD =================

    def _build_ui(self):
        big = tkfont.Font(size=16, weight="bold")
        section = tkfont.Font(size=11, weight="bold")
        mono = tkfont.Font(family="Consolas", size=9)
        mono_bold = tkfont.Font(family="Consolas", size=9, weight="bold")
        self._fonts = dict(big=big, section=section, mono=mono, mono_bold=mono_bold)

        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=16, pady=(12, 6))
        tk.Label(header, text="DRONE GROUND CONTROL", font=big, fg="#ffffff", bg=BG).pack(side="left")

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        left_inner = self._build_scrollable_left(body)
        right = tk.Frame(body, bg=PANEL_BG, width=320)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        self._build_left(left_inner, mono, mono_bold, section)
        self._build_right(right, mono, mono_bold, section)

    def _build_scrollable_left(self, body):
        """Wraps the left column in a Canvas+Scrollbar so nothing (log, SOS
        panel, etc.) ever silently gets clipped off the bottom on a shorter
        screen - the operator can just scroll to reach it instead."""
        container = tk.Frame(body, bg=BG)
        container.pack(side="left", fill="both", expand=True, padx=(0, 12))

        canvas = tk.Canvas(container, bg=BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=BG)

        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=e.width))
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _wheel_up(event):
            canvas.yview_scroll(-3, "units")

        def _wheel_down(event):
            canvas.yview_scroll(3, "units")

        def _bind_wheel(_event):
            canvas.bind_all("<MouseWheel>", _wheel)
            canvas.bind_all("<Button-4>", _wheel_up)
            canvas.bind_all("<Button-5>", _wheel_down)

        def _unbind_wheel(_event):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        canvas.bind("<Enter>", _bind_wheel)
        canvas.bind("<Leave>", _unbind_wheel)

        return inner

    # ---------- left column: video, alerts, galleries, log + sos ----------

    def _build_left(self, left, mono, mono_bold, section):
        w, h = VIDEO_DISPLAY_SIZE
        video_frame = tk.Frame(left, bg="#000000", width=w, height=h)
        video_frame.pack_propagate(False)
        video_frame.pack(fill="x")
        self.video_label = tk.Label(video_frame, text="Starting camera...", bg="#000000",
                                     fg="#888888", justify="center")
        self.video_label.pack(fill="both", expand=True)

        # ---- camera status + fire/smoke alert row ----
        status_row = tk.Frame(left, bg=BG)
        status_row.pack(fill="x", pady=(8, 10))

        cam_card = tk.Frame(status_row, bg=CARD_BG, padx=12, pady=8,
                             highlightthickness=1, highlightbackground=BORDER)
        cam_card.pack(side="left", fill="both", padx=(0, 8))
        tk.Label(cam_card, text="CAMERA", font=("Segoe UI", 8, "bold"),
                 fg=MUTED, bg=CARD_BG).pack(anchor="w")
        self.camera_dir_var = tk.StringVar(value="Forward")
        tk.Label(cam_card, textvariable=self.camera_dir_var, font=mono_bold,
                 fg=ACCENT, bg=CARD_BG).pack(anchor="w")

        self.alert_card = tk.Frame(status_row, bg=CARD_BG, padx=12, pady=8,
                                    highlightthickness=2, highlightbackground=BORDER)
        self.alert_card.pack(side="left", fill="both", expand=True)
        tk.Label(self.alert_card, text="FIRE / SMOKE MONITOR", font=("Segoe UI", 8, "bold"),
                 fg=MUTED, bg=CARD_BG).pack(anchor="w")
        alert_row = tk.Frame(self.alert_card, bg=CARD_BG)
        alert_row.pack(anchor="w", fill="x", pady=(2, 0))
        self.fire_status_var = tk.StringVar(value="\U0001F7E2 FIRE CLEAR")
        self.fire_status_label = tk.Label(alert_row, textvariable=self.fire_status_var,
                                           font=mono_bold, fg=GREEN, bg=CARD_BG)
        self.fire_status_label.pack(side="left", padx=(0, 18))
        self.smoke_status_var = tk.StringVar(value="\U0001F7E2 SMOKE CLEAR")
        self.smoke_status_label = tk.Label(alert_row, textvariable=self.smoke_status_var,
                                            font=mono_bold, fg=GREEN, bg=CARD_BG)
        self.smoke_status_label.pack(side="left")

        # ---- captures row: victim + fire/smoke galleries side by side ----
        captures_row = tk.Frame(left, bg=BG)
        captures_row.pack(fill="x", pady=(0, 8))

        victim_col = tk.Frame(captures_row, bg=BG)
        victim_col.pack(side="left", fill="both", expand=True, padx=(0, 6))
        self.victim_count_var = tk.StringVar(value="(0)")
        self.gallery_strip = self._build_gallery_section(
            victim_col, "VICTIM CAPTURES", self.victim_count_var,
            lambda: self._open_full_gallery("All Victim Captures", list_victim_captures),
            section, mono,
        )
        self._gallery_thumb_widgets = []

        fire_col = tk.Frame(captures_row, bg=BG)
        fire_col.pack(side="left", fill="both", expand=True, padx=(6, 0))
        self.fire_count_var = tk.StringVar(value="(0)")
        self.fire_gallery_strip = self._build_gallery_section(
            fire_col, "FIRE & SMOKE CAPTURES", self.fire_count_var,
            lambda: self._open_full_gallery("All Fire & Smoke Captures", list_fire_captures),
            section, mono, accent=AMBER,
        )
        self._fire_thumb_widgets = []

        # ---- bottom row: compact log + SOS alerts, side by side ----
        bottom_row = tk.Frame(left, bg=BG, height=190)
        bottom_row.pack(fill="both", expand=True, pady=(4, 4))
        bottom_row.pack_propagate(False)

        log_frame = tk.LabelFrame(bottom_row, text="Log", bg=BG, fg=MUTED,
                                   labelanchor="nw", bd=1, highlightbackground=BORDER)
        log_frame.pack(side="left", fill="both", expand=True, padx=(0, 6))
        self.log_box = tk.Listbox(log_frame, bg="#111218", fg="#7CFC00", font=mono,
                                   highlightthickness=0, borderwidth=0)
        self.log_box.pack(fill="both", expand=True, padx=2, pady=2)

        self._build_sos_section(bottom_row, mono, mono_bold, section)

    def _build_gallery_section(self, parent, title, count_var, view_all_cmd, section, mono, accent=AMBER):
        header = tk.Frame(parent, bg=BG)
        header.pack(fill="x", pady=(2, 4))
        tk.Label(header, text=title, font=section, fg="#ffffff", bg=BG).pack(side="left")
        tk.Label(header, textvariable=count_var, font=mono, fg=accent, bg=BG).pack(side="left", padx=(6, 0))

        thumb_h = GALLERY_THUMB_SIZE[1] if isinstance(GALLERY_THUMB_SIZE, (tuple, list)) else 80
        strip_container = tk.Frame(parent, bg=BG)
        strip_container.pack(fill="x")
        canvas = tk.Canvas(strip_container, bg=BG, height=thumb_h + 10, highlightthickness=0)
        scrollbar = tk.Scrollbar(strip_container, orient="horizontal", command=canvas.xview)
        strip = tk.Frame(canvas, bg=BG)
        strip.bind("<Configure>", lambda e, c=canvas: c.configure(scrollregion=c.bbox("all")))
        canvas.create_window((0, 0), window=strip, anchor="nw")
        canvas.configure(xscrollcommand=scrollbar.set)
        canvas.pack(side="top", fill="x")
        scrollbar.pack(side="top", fill="x")

        tk.Button(parent, text="View All Captures", command=view_all_cmd,
                  bg="#33475b", fg="white", activebackground="#3d5871", relief="flat",
                  font=mono).pack(fill="x", pady=(2, 10))
        return strip

    def _build_sos_section(self, parent, mono, mono_bold, section):
        sos_frame = tk.LabelFrame(parent, text="SOS Alerts", bg=BG, fg=RED,
                                   labelanchor="nw", bd=1, highlightbackground=BORDER)
        sos_frame.pack(side="left", fill="both", expand=True, padx=(6, 0))

        header = tk.Frame(sos_frame, bg=BG)
        header.pack(fill="x", padx=4, pady=(0, 2))
        self.sos_count_var = tk.StringVar(value="(0)")
        tk.Label(header, textvariable=self.sos_count_var, font=mono, fg=RED, bg=BG).pack(side="left")

        list_container = tk.Frame(sos_frame, bg=BG)
        list_container.pack(fill="both", expand=True, padx=2, pady=(0, 2))
        canvas = tk.Canvas(list_container, bg=BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
        self.sos_list_frame = tk.Frame(canvas, bg=BG)
        self.sos_list_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.sos_list_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._sos_card_widgets = []

    # ---------- right column: keyboard controls + status ----------

    def _build_right(self, right, mono, mono_bold, section):
        tk.Label(right, text="KEYBOARD CONTROLS", font=section, fg="#ffffff",
                 bg=PANEL_BG).pack(anchor="w", padx=14, pady=(16, 8))

        controls_frame = tk.Frame(right, bg=PANEL_BG)
        controls_frame.pack(fill="x", padx=14)
        controls = [
            ("T", "Takeoff"),
            ("L", "Land"),
            ("C", "Toggle camera direction"),
            ("R", "Start / stop recording"),
            ("P", "Capture photo"),
            ("W / S", "Forward / Backward"),
            ("A / D", "Roll left / Roll right"),
            ("UP / DOWN", "Throttle + / \u2212"),
            ("LEFT / RIGHT", "Camera pan"),
        ]
        for key_text, desc in controls:
            self._control_row(controls_frame, key_text, desc, mono, mono_bold)

        self._separator(right)

        tk.Label(right, text="SAFETY", font=section, fg="#ffffff",
                 bg=PANEL_BG).pack(anchor="w", padx=14, pady=(0, 8))
        safety_frame = tk.Frame(right, bg=PANEL_BG)
        safety_frame.pack(fill="x", padx=14)
        self._control_row(safety_frame, "K + I", "EMERGENCY STOP", mono, mono_bold,
                           key_bg="#5a1f1f", key_fg="#ff9a9a", desc_fg="#ff9a9a")
        self._control_row(safety_frame, "Q + I", "Quit (kills first)", mono, mono_bold,
                           key_bg="#5a4318", key_fg="#ffcf80", desc_fg="#ffcf80")

        self._separator(right)

        tk.Label(right, text="STATUS", font=section, fg="#ffffff",
                 bg=PANEL_BG).pack(anchor="w", padx=14, pady=(0, 8))
        status_card = tk.Frame(right, bg=CARD_BG, padx=12, pady=10,
                                highlightthickness=1, highlightbackground=BORDER)
        status_card.pack(fill="x", padx=14)

        self.status_var = tk.StringVar(value="DISARMED")
        self.status_label = tk.Label(status_card, textvariable=self.status_var,
                                      font=("Segoe UI", 13, "bold"), fg=RED, bg=CARD_BG)
        self.status_label.pack(anchor="w")

        self.action_var = tk.StringVar(value="Ready. Click this window, then fly.")
        tk.Label(status_card, textvariable=self.action_var, font=mono, fg="#cccccc", bg=CARD_BG,
                 wraplength=270, justify="left").pack(anchor="w", pady=(6, 6))

        self.telem_var = tk.StringVar(value="roll=0x80 pitch=0x80 throttle=0x80 yaw=0x80")
        tk.Label(status_card, textvariable=self.telem_var, font=mono, fg=ACCENT, bg=CARD_BG,
                 justify="left", wraplength=270).pack(anchor="w")

        tk.Label(
            right,
            text=(
                f"Victim captures autosave every {VICTIM_SAVE_COOLDOWN_SECONDS:.0f}s max.\n"
                f"Fire/smoke captures autosave every {FIRE_SAVE_COOLDOWN_SECONDS:.0f}s max."
            ),
            font=("Segoe UI", 8), fg=MUTED, bg=PANEL_BG, justify="left",
        ).pack(anchor="w", padx=14, pady=(12, 0))

    def _control_row(self, parent, key_text, desc_text, mono, mono_bold,
                      key_bg="#2c3e50", key_fg="white", desc_fg="#cccccc"):
        row = tk.Frame(parent, bg=PANEL_BG)
        row.pack(fill="x", pady=2)
        tk.Label(row, text=key_text, font=mono_bold, fg=key_fg, bg=key_bg,
                 padx=8, pady=3, width=11, anchor="center").pack(side="left")
        tk.Label(row, text=desc_text, font=mono, fg=desc_fg, bg=PANEL_BG,
                 anchor="w").pack(side="left", padx=(8, 0), fill="x", expand=True)
        return row

    def _separator(self, parent):
        sep = tk.Frame(parent, bg=BORDER, height=1)
        sep.pack(fill="x", padx=14, pady=10)

    # ================= LOG =================

    def _log(self, msg):
        self.log_box.insert(tk.END, msg)
        self.log_box.yview_moveto(1.0)

    # ================= GALLERIES + FIRE/SMOKE ALERT =================

    def _refresh_galleries(self):
        """Re-reads the victims and fire/smoke folders and redraws both thumbnail
        strips, then refreshes the fire/smoke alert card. Runs on its own timer,
        fully decoupled from the video/flight loops - a stalled camera or a
        missing PIL install can never affect flying."""
        victim_paths = list_victim_captures()
        self._refresh_thumb_strip(self.gallery_strip, self._gallery_thumb_widgets,
                                   victim_paths, self.victim_count_var)

        fire_paths = list_fire_captures()
        self._refresh_thumb_strip(self.fire_gallery_strip, self._fire_thumb_widgets,
                                   fire_paths, self.fire_count_var)

        self._update_fire_smoke_alert()

        self.after(GALLERY_REFRESH_MS, self._refresh_galleries)

    def _refresh_thumb_strip(self, strip, widget_list, paths, count_var):
        count_var.set(f"({len(paths)})")

        for w in widget_list:
            w.destroy()
        widget_list.clear()

        recent = paths[:GALLERY_MAX_STRIP_THUMBS]
        if not recent:
            lbl = tk.Label(strip, text="No captures yet", fg="#666666",
                            bg=BG, font=("Courier", 9))
            lbl.pack(side="left")
            widget_list.append(lbl)
        elif not VIDEO_AVAILABLE:
            lbl = tk.Label(strip, text=f"{len(recent)} saved (install pillow to preview)",
                            fg="#666666", bg=BG, font=("Courier", 9))
            lbl.pack(side="left")
            widget_list.append(lbl)
        else:
            for path in recent:
                try:
                    img = Image.open(path)
                    img.thumbnail(GALLERY_THUMB_SIZE)
                    photo = ImageTk.PhotoImage(img)
                except Exception:
                    continue
                thumb = tk.Label(strip, image=photo, bg="#000000", cursor="hand2")
                thumb.image = photo  # keep a reference or Tkinter will garbage-collect it
                thumb.pack(side="left", padx=2)
                thumb.bind("<Button-1>", lambda e, p=path: self._show_full_image(p))
                widget_list.append(thumb)

    def _update_fire_smoke_alert(self):
        if self.video is None:
            return

        fire = self.video.fire_active
        smoke = self.video.smoke_active

        if fire:
            self.fire_status_var.set("\U0001F534 FIRE DETECTED")
            self.fire_status_label.config(fg=RED)
        else:
            self.fire_status_var.set("\U0001F7E2 FIRE CLEAR")
            self.fire_status_label.config(fg=GREEN)

        if smoke:
            self.smoke_status_var.set("\U0001F7E0 SMOKE DETECTED")
            self.smoke_status_label.config(fg=AMBER)
        else:
            self.smoke_status_var.set("\U0001F7E2 SMOKE CLEAR")
            self.smoke_status_label.config(fg=GREEN)

        if fire or smoke:
            border = RED if fire else AMBER
            self.alert_card.config(bg=CARD_BG, highlightbackground=border, highlightthickness=3)
        else:
            self.alert_card.config(highlightbackground=BORDER, highlightthickness=2)

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

    def _open_full_gallery(self, title, list_fn):
        """Full scrollable grid of every capture saved so far for a given list_fn
        (list_victim_captures or list_fire_captures)."""
        top = tk.Toplevel(self)
        top.title(title)
        top.geometry("640x480")
        top.configure(bg=BG)

        canvas = tk.Canvas(top, bg=BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(top, orient="vertical", command=canvas.yview)
        grid_frame = tk.Frame(canvas, bg=BG)

        grid_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=grid_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        paths = list_fn()
        if not paths:
            tk.Label(grid_frame, text="No captures yet.", fg="#888888", bg=BG).pack(padx=20, pady=20)
            return
        if not VIDEO_AVAILABLE:
            tk.Label(grid_frame, text=f"{len(paths)} files saved - install pillow to preview them.",
                     fg="#888888", bg=BG).pack(padx=20, pady=20)
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
            cell = tk.Frame(grid_frame, bg=BG)
            cell.grid(row=i // cols, column=i % cols, padx=6, pady=6)
            lbl = tk.Label(cell, image=photo, bg="#000000", cursor="hand2")
            lbl.pack()
            lbl.bind("<Button-1>", lambda e, p=path: self._show_full_image(p))
            tk.Label(cell, text=os.path.basename(path), fg="#888888", bg=BG,
                     font=("Courier", 7)).pack()
        top.thumb_refs = thumb_refs

    # ================= SOS ALERTS =================

    def _refresh_sos(self):
        """Polls the SOS database (see CommunicationCenter/sos_store.py) and
        redraws the alert list. Empty until something actually starts calling
        save_sos_report() - e.g. a future receiver for the mobile app."""
        try:
            reports = list_sos_reports()
        except Exception:
            self.sos_count_var.set("(error)")
            self.after(SOS_REFRESH_MS, self._refresh_sos)
            return

        self.sos_count_var.set(f"({len(reports)})")

        for w in self._sos_card_widgets:
            w.destroy()
        self._sos_card_widgets = []

        if not reports:
            lbl = tk.Label(self.sos_list_frame, text="No SOS alerts.", fg="#666666",
                            bg=BG, font=("Courier", 9))
            lbl.pack(anchor="w", padx=4, pady=4)
            self._sos_card_widgets.append(lbl)
        else:
            for r in reports:
                self._sos_card_widgets.append(self._build_sos_card(r))

        self.after(SOS_REFRESH_MS, self._refresh_sos)

    def _build_sos_card(self, report):
        card = tk.Frame(self.sos_list_frame, bg=CARD_BG, highlightthickness=1,
                         highlightbackground=RED, padx=6, pady=4)
        card.pack(fill="x", padx=4, pady=3)

        name = report.get("name") or "Unknown"
        ts = report.get("created_at") or ""
        tk.Label(card, text=f"{name}   {ts}", font=("Segoe UI", 9, "bold"),
                 fg="#ffffff", bg=CARD_BG).pack(anchor="w")

        phone = report.get("phone") or "\u2014"
        tk.Label(card, text=f"Phone: {phone}", font=("Consolas", 8),
                 fg="#cccccc", bg=CARD_BG).pack(anchor="w")

        condition = report.get("health_condition") or "\u2014"
        tk.Label(card, text=f"Condition: {condition}", font=("Consolas", 8),
                 fg=AMBER, bg=CARD_BG).pack(anchor="w")

        lat, lon = report.get("latitude"), report.get("longitude")
        loc_text = (f"Location: {lat:.5f}, {lon:.5f}"
                    if lat is not None and lon is not None else "Location: unknown")
        tk.Label(card, text=loc_text, font=("Consolas", 8),
                 fg=ACCENT, bg=CARD_BG).pack(anchor="w")

        if VIDEO_AVAILABLE:
            imgs_row = tk.Frame(card, bg=CARD_BG)
            imgs_row.pack(anchor="w", pady=(4, 0))
            for path in (report.get("front_image_path"), report.get("back_image_path")):
                if not path or not os.path.exists(path):
                    continue
                try:
                    img = Image.open(path)
                    img.thumbnail(SOS_THUMB_SIZE)
                    photo = ImageTk.PhotoImage(img)
                except Exception:
                    continue
                thumb = tk.Label(imgs_row, image=photo, bg="#000000", cursor="hand2")
                thumb.image = photo
                thumb.pack(side="left", padx=2)
                thumb.bind("<Button-1>", lambda e, p=path: self._show_full_image(p))

        return card

    # ================= VIDEO =================

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

    # ================= KEYBOARD HANDLING =================

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
        label = "Downward" if now_down else "Forward"
        self.after(0, lambda: self.camera_dir_var.set(label))

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

    # ================= ACTION QUEUE =================

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
            self.status_label.config(fg=GREEN)
        else:
            self.status_var.set("DISARMED")
            self.status_label.config(fg=RED)

    # ================= FLIGHT AXES LOOP =================

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
