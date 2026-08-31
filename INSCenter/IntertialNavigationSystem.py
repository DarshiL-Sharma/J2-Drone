# This system can only be used when the sensors are there 😗😗 (Try Dead reckoning system)


import math
import time

class INSTracker:
    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.home_set = False

    def zero_home(self):
        # Assign the value to home
        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.home_set = True

    def update(self, ax, ay, dt):
        self.vx += ax * dt
        self.vy += ay * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

    @property
    def position(self):
        return self.x, self.y


class PointToPointNavigator:

    def __init__(self, ins: INSTracker, cruise_speed=3.5, arrival_tolerance=0.5):
        """
        cruise_speed: m/s — keep this inside your 3-4 m/s range
        arrival_tolerance: meters — how close counts as "arrived"
        """
        self.ins = ins
        self.cruise_speed = cruise_speed
        self.arrival_tolerance = arrival_tolerance
        self.target = None

    def set_target(self, target_x, target_y):
        self.target = (target_x, target_y)

    def has_arrived(self):
        if self.target is None:
            return True
        cx, cy = self.ins.position
        tx, ty = self.target
        return math.hypot(tx - cx, ty - cy) <= self.arrival_tolerance

    def compute_velocity_command(self):

        if self.target is None or self.has_arrived():
            return 0.0, 0.0

        cx, cy = self.ins.position
        tx, ty = self.target
        dx, dy = tx - cx, ty - cy
        dist = math.hypot(dx, dy)

        vx = (dx / dist) * self.cruise_speed
        vy = (dy / dist) * self.cruise_speed
        return vx, vy


def run_point_to_point(ins: INSTracker, navigator: PointToPointNavigator,
                        target_x, target_y, send_velocity_command, get_imu_sample,
                        control_hz=20):

    navigator.set_target(target_x, target_y)
    period = 1.0 / control_hz
    last_time = time.time()

    while not navigator.has_arrived():
        now = time.time()
        dt = now - last_time
        last_time = now

        ax, ay = get_imu_sample()
        ins.update(ax, ay, dt)

        vx, vy = navigator.compute_velocity_command()
        send_velocity_command(vx, vy)

        time.sleep(period)

    send_velocity_command(0.0, 0.0)  # stop at arrival