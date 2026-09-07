import socket
import time

from ConstantsCenter.constants import (
    DRONE_IP, DRONE_PORT, CENTER, STICK_MAX, STICK_MIN, MAX_DEV, CMD_IDLE, CMD_TAKEOFF, CMD_KILL,
    LAND_FAILSAFE_SECONDS, CAMERA_DOWN_FRAME, CAMERA_FORWARD_FRAME,
    BASE_LAT, BASE_LNG, SPEED
)
from CommunicationCenter.communication import build_frame
from CloudCenter.altitudeSync import AltitudeSync
from CloudCenter.geoConvert import latlng_to_north_east
from INSCenter.DeadReckoningSystem import OpenLoopINS, run_point_to_point

VERTICAL_SPEED_MPS = 2.0
BASE_TAKEOFF_HEIGHT_M = 2.0
ALTITUDE_PUSH_INTERVAL_S = 0.25


class Drone:
    def __init__(self, ip=DRONE_IP, port=DRONE_PORT, sync_to_cloud=True):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.addr = (ip, port)
        self.throttle = CENTER
        self.armed = False
        self.camera_facing_down = False
        self.altitude = 0.0
        self._last_altitude_push = 0.0
        self.ins = OpenLoopINS()  # ADDED: dead-reckoning for SOS dispatch

        self._cloud = None
        if sync_to_cloud:
            try:
                self._cloud = AltitudeSync()
            except Exception as e:
                print(f"[Drone] Cloud sync disabled (Firebase init failed): {e}")

    def send_axes(self, b2, b3, b4, b5, cmd=CMD_IDLE):
        self.sock.sendto(build_frame(b2, b3, b4, b5, cmd), self.addr)

    def _hold_blocking(self, duration, **axes):
        frame = build_frame(**axes)
        end = time.time() + duration
        while time.time() < end:
            self.sock.sendto(frame, self.addr)
            time.sleep(0.05)

    def _push_altitude(self):
        if self._cloud:
            self._cloud.push(altitude_m=round(self.altitude, 2), armed=self.armed)

    def _maybe_push_altitude(self):
        now = time.time()
        if now - self._last_altitude_push >= ALTITUDE_PUSH_INTERVAL_S:
            self._last_altitude_push = now
            self._push_altitude()

    def takeoff(self):
        self._hold_blocking(1.0, cmd=CMD_TAKEOFF)
        self.throttle = CENTER
        self.armed = True
        self.altitude = BASE_TAKEOFF_HEIGHT_M
        self._push_altitude()

    def kill(self):
        self._hold_blocking(1.0, cmd=CMD_KILL)
        self.armed = False
        self.altitude = 0.0
        self._push_altitude()

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
        self.altitude = 0.0
        self._push_altitude()

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
        self.altitude = 0.0
        self._push_altitude()

    def calibrate(self):
        self._hold_blocking(0.3, cmd=CMD_IDLE)

    def set_camera_direction(self, face_down):
        frame = CAMERA_DOWN_FRAME if face_down else CAMERA_FORWARD_FRAME
        self.sock.sendto(frame, self.addr)
        self.camera_facing_down = face_down

    def toggle_camera_direction(self):
        self.set_camera_direction(not self.camera_facing_down)
        return self.camera_facing_down

    def update_altitude(self, b4, dt_seconds):
        if not self.armed:
            return
        if b4 >= CENTER:
            span = STICK_MAX - CENTER
            vertical_speed = VERTICAL_SPEED_MPS * (b4 - CENTER) / span if span else 0.0
        else:
            span = CENTER - STICK_MIN
            vertical_speed = VERTICAL_SPEED_MPS * (b4 - CENTER) / span if span else 0.0
        self.altitude = max(0.0, self.altitude + vertical_speed * dt_seconds)
        self._maybe_push_altitude()

    def move_up(self, taps: int = 1, burst_seconds: float = 1.0):
        for _ in range(taps):
            up_value = min(STICK_MAX, CENTER + int((STICK_MAX - CENTER) * 0.5))
            self._hold_blocking(burst_seconds, b4=up_value, cmd=CMD_IDLE)
            self.sock.sendto(build_frame(b4=self.throttle, cmd=CMD_IDLE), self.addr)
            self.altitude += VERTICAL_SPEED_MPS * burst_seconds
            self._push_altitude()

    def move_down(self, taps: int = 1, burst_seconds: float = 1.0):
        for _ in range(taps):
            down_value = max(STICK_MIN, CENTER - int((CENTER - STICK_MIN) * 0.5))
            self._hold_blocking(burst_seconds, b4=down_value, cmd=CMD_IDLE)
            self.sock.sendto(build_frame(b4=self.throttle, cmd=CMD_IDLE), self.addr)
            self.altitude = max(0.0, self.altitude - VERTICAL_SPEED_MPS * burst_seconds)
            self._push_altitude()

    # ===================================================================
    # ADDED: SOS auto-dispatch
    # ===================================================================
    def _send_velocity(self, vx, vy):
        """vx=east m/s, vy=north m/s from the INS. Assumes heading=0 (never
        rotated) so INS's x(east) maps to pitch/forward (b3) and y(north)
        maps to roll (b2) — matches OpenLoopINS's own 'heading0=faces east'
        convention. VERIFY against your real drone before flying — 'a' is
        only marked 'tested', 'd' is untested per your own key labels."""
        if SPEED <= 0:
            return
        b3 = int(max(STICK_MIN, min(STICK_MAX, CENTER + (vx / SPEED) * MAX_DEV)))
        b2 = int(max(STICK_MIN, min(STICK_MAX, CENTER + (vy / SPEED) * MAX_DEV)))
        self.send_axes(b2, b3, self.throttle, CENTER, cmd=CMD_IDLE)

    def dispatch_to_sos(self, lat, lng, message=""):
        print(f"[SOS] dispatch start: {message} ({lat},{lng})")
        self.takeoff()  # already sets constant 2m altitude, no extra climb needed
        self.ins.zero_home()
        north, east = latlng_to_north_east(BASE_LAT, BASE_LNG, lat, lng)
        run_point_to_point(self.ins, target_x=east, target_y=north,
                            send_velocity_command=self._send_velocity)
        self.land()
        print("[SOS] dispatch complete, landed")
