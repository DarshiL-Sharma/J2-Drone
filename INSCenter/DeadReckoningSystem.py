import math
import time
from ConstantsCenter.constants import SPEED


class OpenLoopINS:
    # X = east , y = north , while takeoff the home set to the (0,0)

    def __init__(self):
        self.SPEED = SPEED                 # constant cruise speed, m/s (from your constants file)
        self.x = 0.0                       # current estimated x position (meters)
        self.y = 0.0                       # current estimated y position (meters)
        self.home_set = False              # becomes True only after zero_home() runs
        self.heading = 0.0                 # current facing direction in radians, 0 = facing +x (east)

        self._leg_start_pos = (0.0, 0.0)   # (x, y) where the current leg began
        self._leg_start_time = None        # timestamp when the current leg began
        self._direction = (0.0, 0.0)       # unit vector of the current leg's direction

    def zero_home(self):
        # At the moment of the takeoff drone automatically assign the home point
        self.x = 0.0
        self.y = 0.0
        self.home_set = True
        self.heading = 0.0                 # reset facing direction too — same convention as position
        self._leg_start_pos = (0.0, 0.0)
        self._leg_start_time = None
        self._direction = (0.0, 0.0)

    def set_heading(self, heading_degrees):
        # Call this whenever the drone turns, BEFORE the next forward/backward/left/right move
        self.heading = math.radians(heading_degrees)

    def direction_for_command(self, command):
        # Converts a relative command into a world-frame (x, y) unit vector using trigonometry
        offsets = {
            "forward": 0.0,
            "right": -math.pi / 2,     # right = 90 degrees clockwise from forward
            "backward": math.pi,
            "left": math.pi / 2,       # left = 90 degrees counter-clockwise from forward
        }
        if command not in offsets:
            raise ValueError(f"unknown command: {command!r}")

        angle = self.heading + offsets[command]
        return math.cos(angle), math.sin(angle)   # returns BOTH x and y components together

    def UninteruptedJourney(self, direction_x, direction_y):
        """
        Call this the instant you send a movement command in a new
        direction. direction_x/direction_y don't need to be normalized —
        only the direction matters, not the magnitude.
        """
        if not self.home_set:
            raise RuntimeError("zero_home() must be called before UninteruptedJourney()")

        mag = math.hypot(direction_x, direction_y)     # length of the given (x, y) — used only to normalize
        if mag == 0:
            raise ValueError("direction cannot be (0, 0)")

        self._direction = (direction_x / mag, direction_y / mag)   # store as a unit vector
        self._leg_start_pos = (self.x, self.y)                     # remember where this leg started
        self._leg_start_time = time.time()                         # remember when this leg started
        print(f"[INS] leg started at ({self.x:.2f}, {self.y:.2f}), direction=({self._direction[0]:.2f}, {self._direction[1]:.2f})")

    def refresh(self):
        # This is pure maths — SPEED aur time se position ka measurement kar rahe he
        if self._leg_start_time is None:
            return self.position

        elapsed = time.time() - self._leg_start_time   # how long this leg has been running
        dist = self.SPEED * elapsed                    # pure math: distance = speed x time
        sx, sy = self._leg_start_pos
        ux, uy = self._direction
        self.x = sx + ux * dist                         # x and y are ALWAYS updated together, never alone
        self.y = sy + uy * dist
        print(f"[INS] live position -> x={self.x:.2f}  y={self.y:.2f}")   # live readout for testing
        return self.position

    def stop_leg(self):
        """Call this the instant you send the stop command — freezes position."""
        self.refresh()  # capture position up to the moment of stopping
        self._leg_start_time = None
        print(f"[INS] leg stopped at ({self.x:.2f}, {self.y:.2f})")

    @property
    def position(self):
        return self.x, self.y


def run_point_to_point(ins: OpenLoopINS, target_x, target_y,
                        send_velocity_command, refresh_hz=10):
    """
    Moves from wherever the INS currently estimates it is, straight to
    (target_x, target_y), then stops. Pure open-loop: computes distance
    and required travel time up front from SPEED, then commands motion
    for exactly that long.

    send_velocity_command(vx, vy): plug in your existing function that
        sends a velocity command over your drone's protocol.
    refresh_hz: how often to refresh the position estimate while waiting —
        purely for your own logging/telemetry, doesn't affect timing.

    Never touches z — call this only during a horizontal leg of your
    rectangle pattern, with altitude already locked elsewhere.
    """
    cx, cy = ins.position
    dx, dy = target_x - cx, target_y - cy
    dist = math.hypot(dx, dy)

    if dist == 0:
        return

    travel_time = dist / ins.SPEED
    vx = (dx / dist) * ins.SPEED
    vy = (dy / dist) * ins.SPEED
    print(f"[NAV] point-to-point: target=({target_x:.2f}, {target_y:.2f})  distance={dist:.2f}m  travel_time={travel_time:.2f}s")

    ins.UninteruptedJourney(dx, dy)
    send_velocity_command(vx, vy)

    period = 1.0 / refresh_hz
    leg_start = time.time()
    while (time.time() - leg_start) < travel_time:
        ins.refresh()
        time.sleep(period)

    send_velocity_command(0.0, 0.0)
    ins.stop_leg()


def run_directional_move(ins: OpenLoopINS, command, distance,
                          send_velocity_command, refresh_hz=10):
    """
    Moves the drone `distance` meters in a direction relative to its
    current heading — command is one of "forward", "backward", "left",
    "right". Same open-loop timing as run_point_to_point(), just with
    the direction coming from ins.direction_for_command() instead of a
    target point.

    Example: a "move right" command still produces a real (ux, uy) pair
    via trigonometry, so ins.x AND ins.y both get updated together —
    the DRS position is always a combined (x, y) point, never treated
    as a change on a single axis alone.
    """

    ux, uy = ins.direction_for_command(command)
    travel_time = distance / ins.SPEED
    vx, vy = ux * ins.SPEED, uy * ins.SPEED
    print(f"[NAV] directional move: command={command}  distance={distance:.2f}m  travel_time={travel_time:.2f}s")

    ins.UninteruptedJourney(ux, uy)
    send_velocity_command(vx, vy)

    period = 1.0 / refresh_hz
    leg_start = time.time()
    while (time.time() - leg_start) < travel_time:
        ins.refresh()
        time.sleep(period)

    send_velocity_command(0.0, 0.0)
    ins.stop_leg()


def return_to_home(ins: OpenLoopINS, send_velocity_command, refresh_hz=10):
    """
    Flies straight back to home (0, 0) from wherever the INS currently
    estimates the drone is.

    Uses trigonometry explicitly:
      - bearing to home = atan2(-y, -x)   (angle from current position to origin)
      - distance to home = hypot(x, y)    (straight-line distance to origin)

    Internally this reduces to the same math as run_point_to_point(),
    just always aimed at (0, 0) — kept as its own function so it reads
    clearly as the RTH step in your state machine.
    """
    cx, cy = ins.position

    distance_to_home = math.hypot(cx, cy)              # straight-line distance back to origin
    bearing_to_home = math.atan2(-cy, -cx)              # radians, angle pointing at origin

    if distance_to_home == 0:
        print("[NAV] already at home, nothing to do")
        return  # already home

    vx = math.cos(bearing_to_home) * ins.SPEED
    vy = math.sin(bearing_to_home) * ins.SPEED
    travel_time = distance_to_home / ins.SPEED
    print(f"[NAV] returning to home: distance={distance_to_home:.2f}m  travel_time={travel_time:.2f}s")

    ins.UninteruptedJourney(-cx, -cy)
    send_velocity_command(vx, vy)

    period = 1.0 / refresh_hz
    leg_start = time.time()
    while (time.time() - leg_start) < travel_time:
        ins.refresh()
        time.sleep(period)

    send_velocity_command(0.0, 0.0)
    ins.stop_leg()