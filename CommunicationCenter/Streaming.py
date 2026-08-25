from ConstantsCenter.constants import (
    RTSP_URL,
    YOLO_MODEL_PATH,
    CAMERA_TILT_ANGLE,
    FIRE_SAVE_COOLDOWN_SECONDS,
    VICTIM_SAVE_COOLDOWN_SECONDS,
)
from ConstantsCenter.constants import SAVE_DIR,VICTIM_DIR,FIRE_DIR
import threading
import cv2
from ultralytics import YOLO
import os
import datetime
import time
from CommunicationCenter.communication import detect_fire,fix_tilt
class VideoStream:
    def __init__(self, url=RTSP_URL, model_path=YOLO_MODEL_PATH):
        self.url = url
        self.model_path = model_path
        self.cap = None
        self.latest_frame = None
        self._latest_raw = None
        self._raw_frame_id = 0
        self._last_processed_id = -1
        self.lock = threading.Lock()
        self.raw_lock = threading.Lock()
        self.running = False
        self.status = "not started"
        self.recording = False
        self.video_writer = None
        self.record_path = None
        self.last_victim_save_time = 0.0
        self.last_fire_save_time = 0.0
        self.fire_active = False
        os.makedirs(SAVE_DIR, exist_ok=True)
        os.makedirs(VICTIM_DIR, exist_ok=True)
        os.makedirs(FIRE_DIR, exist_ok=True)

    def start(self):
        self.running = True
        threading.Thread(target=self._capture_loop, daemon=True).start()
        threading.Thread(target=self._process_loop, daemon=True).start()

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

    def _save_fire_capture(self, annotated_bgr):
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        path = os.path.join(FIRE_DIR, f"fire_{ts}.jpg")
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

    def _capture_loop(self):
        self.status = "connecting to stream..."
        self.cap = cv2.VideoCapture(self.url)
        try:
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

        if not self.cap.isOpened():
            self.status = "stream not available (check RTSP URL / drone connection)"
            return
        self.status = "live"

        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                self.status = "frame lost - stream ended"
                break
            with self.raw_lock:
                self._latest_raw = frame
                self._raw_frame_id += 1

        if self.cap:
            self.cap.release()
        if self.status == "live":
            self.status = "stopped"

    def _get_latest_raw(self):
        with self.raw_lock:
            if self._latest_raw is None or self._raw_frame_id == self._last_processed_id:
                return None, None
            return self._latest_raw.copy(), self._raw_frame_id

    def _process_loop(self):
        self.status = "loading YOLO model..."
        try:
            model = YOLO(self.model_path)
        except Exception as e:
            self.status = f"model load failed: {e}"
            return

        # wait for the capture thread to actually start producing frames
        while self.running and self._latest_raw is None:
            time.sleep(0.01)

        while self.running:
            frame, frame_id = self._get_latest_raw()
            if frame is None:
                time.sleep(0.005)
                continue
            self._last_processed_id = frame_id

            # Correct teh camera tilt
            frame = fix_tilt(frame, CAMERA_TILT_ANGLE)

            try:
                is_fire, _fire_mask = detect_fire(frame)
            except Exception:
                is_fire = False
            self.fire_active = is_fire

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

            if is_fire:
                cv2.putText(annotated, "FIRE DETECTED", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2, cv2.LINE_AA)
                now = time.time()
                if now - self.last_fire_save_time >= FIRE_SAVE_COOLDOWN_SECONDS:
                    self._save_fire_capture(annotated)
                    self.last_fire_save_time = now

            annotated_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)

            with self.lock:
                self.latest_frame = annotated_rgb.copy()
                if self.recording:
                    self._ensure_writer(annotated_rgb)
                    bgr = cv2.cvtColor(annotated_rgb, cv2.COLOR_RGB2BGR)
                    self.video_writer.write(bgr)

        with self.lock:
            if self.video_writer is not None:
                self.video_writer.release()
                self.video_writer = None

