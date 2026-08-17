"""
Interactive drone control - built from reverse-engineered WiFi protocol.

Frame format (9 bytes):
    03 66 [B2] [B3] [B4] [B5] [CMD] [CHK] 99
           Roll Pitch Throttle Yaw  Cmd   Checksum

CONFIRMED from packet captures:
    - Checksum = B2 ^ B3 ^ B4 ^ B5 ^ CMD  (verified against every captured frame)
    - CMD 0x00 = idle / calibrate (sent continuously at ~20Hz as a heartbeat)
    - CMD 0x01 = takeoff
    - CMD 0x04 = emergency stop (cuts motors instantly - NOT a landing)
    - All stick axes range roughly 0x58 (min) to 0xA8 (max) around center 0x80
    - Forward = pitch (B3) above center, up to ~0xA8
    - Backward = pitch (B3) below center, down to ~0x58 (by symmetry, unconfirmed)
    - Landing = throttle (B4) ramped down to 0x00 over ~0.4-0.5s, CMD stays 0x00
      (there is no dedicated "land" CMD value in this protocol)

UNCONFIRMED - flagged in the relevant functions below, verify before relying on them:
    - Which physical direction (left vs right) each roll byte range produces -
      you observed pressing "left" made the drone visibly go right, most likely
      because the drone was facing toward you rather than away. Re-test with
      the drone facing away from you before trusting the left/right naming.
    - Camera pan direction mapping - your capture showed jittery values with
      B5 hitting full extremes (0x01 / 0xFF), separate from the flight-stick
      range, but the two directions weren't cleanly isolated in that capture.
"""

import socket
import time

DRONE_IP = "192.168.1.1"
DRONE_PORT = 7099

CENTER = 0x80
MAX_DEV = 0x28          # observed max deviation from center on any axis
STICK_MAX = CENTER + MAX_DEV   # 0xA8
STICK_MIN = CENTER - MAX_DEV   # 0x58

CMD_IDLE = 0x00
CMD_TAKEOFF = 0x01
CMD_KILL = 0x04

SEND_INTERVAL = 0.05    # ~20Hz, matches the observed traffic rate


def clamp01(x):
    return max(0.0, min(1.0, x))


def checksum(b2, b3, b4, b5, cmd):
    return b2 ^ b3 ^ b4 ^ b5 ^ cmd


def build_frame(b2=CENTER, b3=CENTER, b4=CENTER, b5=CENTER, cmd=CMD_IDLE):
    for name, val in [("roll", b2), ("pitch", b3), ("throttle", b4), ("yaw", b5), ("cmd", cmd)]:
        if not 0 <= val <= 0xFF:
            raise ValueError(f"{name} byte out of range: {val}")
    chk = checksum(b2, b3, b4, b5, cmd)
    return bytes([0x03, 0x66, b2, b3, b4, b5, cmd, chk, 0x99])


class Drone:
    def __init__(self, ip=DRONE_IP, port=DRONE_PORT):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.addr = (ip, port)
        self.throttle = CENTER  # tracked so land() knows what to ramp down from

    def _send(self, frame):
        self.sock.sendto(frame, self.addr)

    def _hold(self, duration, **axes):
        frame = build_frame(**axes)
        end = time.time() + duration
        while time.time() < end:
            self._send(frame)
            time.sleep(SEND_INTERVAL)

    def calibrate(self, duration=0.3):
        print("Calibrating (centered idle)...")
        self._hold(duration, cmd=CMD_IDLE)

    def takeoff(self):
        print("Taking off...")
        self._hold(1.0, cmd=CMD_TAKEOFF)
        self.throttle = CENTER
        self.calibrate()

    def kill(self):
        print("!! EMERGENCY STOP - motors cut instantly !!")
        self._hold(1.0, cmd=CMD_KILL)
        self.calibrate()

    def forward(self, duration=1.0, intensity=1.0):
        b3 = int(CENTER + MAX_DEV * clamp01(intensity))
        print(f"Forward (pitch={hex(b3)})...")
        self._hold(duration, b3=b3, b4=self.throttle)
        self.calibrate()

    def backward(self, duration=1.0, intensity=1.0):
        # By symmetry with forward - not directly captured, verify in a real test.
        b3 = int(CENTER - MAX_DEV * clamp01(intensity))
        print(f"Backward (pitch={hex(b3)}) [unconfirmed]...")
        self._hold(duration, b3=b3, b4=self.throttle)
        self.calibrate()

    def roll_left(self, duration=1.0, intensity=1.0):
        # This is the byte pattern from your "left" test (B2 dropping to 0x58).
        # You observed the drone physically move RIGHT during this - likely an
        # orientation effect (drone nose toward you). Confirm facing before trusting.
        b2 = int(CENTER - MAX_DEV * clamp01(intensity))
        print(f"Roll - tested pattern (roll={hex(b2)})...")
        self._hold(duration, b2=b2, b4=self.throttle)
        self.calibrate()

    def roll_right(self, duration=1.0, intensity=1.0):
        # Mirrored by symmetry from roll_left - NOT captured/confirmed yet.
        b2 = int(CENTER + MAX_DEV * clamp01(intensity))
        print(f"Roll - opposite pattern (roll={hex(b2)}) [unconfirmed]...")
        self._hold(duration, b2=b2, b4=self.throttle)
        self.calibrate()

    def camera_pan_a(self, duration=0.3):
        # Camera pan reuses the yaw byte slot and hit full extremes in your
        # capture, not the flight-stick range. Direction (left/right) unconfirmed.
        print("Camera pan - direction A [unconfirmed]...")
        self._hold(duration, b5=0x01, b4=self.throttle)
        self.calibrate()

    def camera_pan_b(self, duration=0.3):
        print("Camera pan - direction B [unconfirmed]...")
        self._hold(duration, b5=0xFF, b4=self.throttle)
        self.calibrate()

    def land(self, step=0x10, step_time=0.05):
        """Ramp throttle down to zero - matches the smooth landing you captured."""
        print("Landing (throttle ramp to zero)...")
        b4 = self.throttle
        while b4 > 0:
            b4 = max(0, b4 - step)
            self._send(build_frame(b4=b4, cmd=CMD_IDLE))
            time.sleep(step_time)
        self.throttle = 0
        self.calibrate()
        print("Landed.")


MENU = """
Commands:
  cal              - calibrate / center (idle)
  takeoff          - take off
  fwd [sec]        - move forward
  back [sec]       - move backward               [unconfirmed direction/range]
  left [sec]       - roll (tested pattern)        [physical direction unconfirmed]
  right [sec]      - roll (opposite pattern)      [unconfirmed]
  camA [sec]       - camera pan A                 [unconfirmed]
  camB [sec]       - camera pan B                 [unconfirmed]
  land             - ramp throttle to zero and land
  kill             - EMERGENCY STOP (instant motor cut)
  quit             - exit (sends kill first, for safety)
"""


def main():
    drone = Drone()
    print(MENU)
    while True:
        try:
            raw = input("> ").strip().lower().split()
        except (EOFError, KeyboardInterrupt):
            print("\nInterrupted - sending kill for safety.")
            drone.kill()
            break

        if not raw:
            continue
        cmd, *args = raw

        try:
            if cmd == "cal":
                drone.calibrate()
            elif cmd == "takeoff":
                drone.takeoff()
            elif cmd == "fwd":
                drone.forward(duration=float(args[0]) if args else 1.0)
            elif cmd == "back":
                drone.backward(duration=float(args[0]) if args else 1.0)
            elif cmd == "left":
                drone.roll_left(duration=float(args[0]) if args else 1.0)
            elif cmd == "right":
                drone.roll_right(duration=float(args[0]) if args else 1.0)
            elif cmd == "cama":
                drone.camera_pan_a(duration=float(args[0]) if args else 0.3)
            elif cmd == "camb":
                drone.camera_pan_b(duration=float(args[0]) if args else 0.3)
            elif cmd == "land":
                drone.land()
            elif cmd == "kill":
                drone.kill()
            elif cmd == "quit":
                print("Sending kill before exit, for safety...")
                drone.kill()
                break
            else:
                print(MENU)
        except Exception as e:
            print(f"Error: {e} -- sending kill for safety.")
            drone.kill()


if __name__ == "__main__":
    main()
