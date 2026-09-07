import time
from CloudCenter.geoConvert import latlng_to_north_east
from ConstantsCenter.constants import BASE_LAT, BASE_LNG, CRUISE_CLIMB_SECONDS

class SOSDispatcher:
    def __init__(self, drone, ins, send_velocity_command, on_status=None):
        self.drone = drone
        self.ins = ins
        self.send_velocity_command = send_velocity_command
        self.on_status = on_status or (lambda *_: None)
        self.busy = False

    def dispatch(self, sos_id, lat, lng, message):
        if self.busy:
            self.on_status(sos_id, "ignored — already dispatched")
            return
        self.busy = True
        try:
            self.on_status(sos_id, f"takeoff — {message}")
            self.drone.takeoff()

            self.on_status(sos_id, "climbing to 2m")
            self._climb_to_constant_altitude()

            self.ins.zero_home()
            north, east = latlng_to_north_east(BASE_LAT, BASE_LNG, lat, lng)
            self.on_status(sos_id, f"enroute north={north:.1f}m east={east:.1f}m")

            from AutonomusCenter.ins import run_point_to_point
            run_point_to_point(self.ins, target_x=east, target_y=north,
                                send_velocity_command=self.send_velocity_command)

            self.on_status(sos_id, "landing")
            self.drone.land()
            self.on_status(sos_id, "landed")
        finally:
            self.busy = False

    def _climb_to_constant_altitude(self):
        """No barometer feedback — pure time-based climb, matching your
        request for a fixed 2m with no altitude variation logic."""
        self.drone.throttle = 0xA8
        start = time.time()
        while time.time() - start < CRUISE_CLIMB_SECONDS:
            self.send_velocity_command(0.0, 0.0)
            time.sleep(0.05)
        self.drone.throttle = 0x80  # hold