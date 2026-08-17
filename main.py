"""
Keyboard-controlled drone flying - real-time, held-key style (like a real RC stick).

Requires: pip install pynput

CONTROLS:
    T           - takeoff
    L           - land (throttle ramps to zero)
    K / ESC     - EMERGENCY STOP (instant motor cut)
    Q           - quit program (sends kill first, for safety)

    W           - forward   (pitch)
    S           - backward  (pitch)                    [unconfirmed direction/range]
    A           - roll, tested pattern                 [physical L/R unconfirmed - see below]
    D           - roll, opposite pattern                [unconfirmed]
    Up arrow    - throttle up / climb                   [inferred from axis order, unconfirmed]
    Down arrow  - throttle down / descend                [inferred, unconfirmed]
    Left arrow  - camera pan, direction A                [unconfirmed]
    Right arrow - camera pan, direction B                [unconfirmed]

    Hold a key to keep moving in that direction, same as a real analog stick.
    Release it and the axis returns to center automatically.
"""

import socket
import time
import threading

try:
    from pynput import keyboard
except ImportError:
    raise SystemExit(
        "Missing dependency. Install it first:\n    pip install pynput"
    )

DRONE_IP = "192.168.1.1"
DRONE_PORT = 7099

CENTER = 0x80
MAX_DEV = 0x28                  # observed max deviation from center on any axis
STICK_MAX = CENTER + MAX_DEV    # 0xA8
STICK_MIN = CENTER - MAX_DEV    # 0x58

CMD_IDLE = 0x00
CMD_TAKEOFF = 0x01
CMD_KILL = 0x04

SEND_INTERVAL = 0.05            # ~20Hz, matches observed traffic rate


def checksum(b2, b3, b4, b5, cmd):
    return b2 ^ b3 ^ b4 ^ b5 ^ cmd


def build_frame(b2=CENTER, b3=CENTER, b4=CENTER, b5=CENTER, cmd=CMD_IDLE):
    b2, b3, b4, b5, cmd = (max(0, min(0xFF, v)) for v in (b2, b3, b4, b5, cmd))
    chk = checksum(b2, b3, b4, b5, cmd)
    return bytes([0x03, 0x66, b2, b3, b4, b5, cmd, chk, 0x99])


class Drone:
    def __init__(self, ip=DRONE_IP, port=DRONE_PORT):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.addr = (ip, port)
        self.throttle = CENTER

    def _send(self, frame):
        self.sock.sendto(frame, self.addr)

    def _hold(self, duration, **axes):
        frame = build_frame(**axes)
        end = time.time() + duration
        while time.time() < end:
            self._send(frame)
            time.sleep(SEND_INTERVAL)

    def send_axes(self, b2, b3, b4, b5, cmd=CMD_IDLE):
        self._send(build_frame(b2, b3, b4, b5, cmd))

    def takeoff(self):
        print("Taking off...")
        self._hold(1.0, cmd=CMD_TAKEOFF)
        self.throttle = CENTER

    def kill(self):
        print("!! EMERGENCY STOP - motors cut instantly !!")
        self._hold(1.0, cmd=CMD_KILL)

    def land(self, step=0x10, step_time=0.05):
        print("Landing (throttle ramp to zero)...")
        b4 = self.throttle
        while b4 > 0:
            b4 = max(0, b4 - step)
            self._send(build_frame(b4=b4, cmd=CMD_IDLE))
            time.sleep(step_time)
        self.throttle = 0
        print("Landed.")


class KeyboardFlyer:
    def __init__(self):
        self.drone = Drone()
        self.pressed = set()
        self.running = True
        # edge-trigger guards so holding T/L/K doesn't repeat the action every loop tick
        self.action_lock = threading.Lock()
        self.action_in_progress = False

    # ---- key events ----
    def on_press(self, key):
        name = self._key_name(key)
        if name is None:
            return
        if name not in self.pressed:
            self.pressed.add(name)
            self._maybe_trigger_action(name)

    def on_release(self, key):
        name = self._key_name(key)
        if name is None:
            return
        self.pressed.discard(name)
        if name == "esc" or name == "q":
            self.running = False
            return False  # stop listener

    @staticmethod
    def _key_name(key):
        try:
            return key.char.lower()
        except AttributeError:
            return {
                keyboard.Key.up: "up",
                keyboard.Key.down: "down",
                keyboard.Key.left: "left",
                keyboard.Key.right: "right",
                keyboard.Key.esc: "esc",
            }.get(key)

    def _maybe_trigger_action(self, name):
        if name not in ("t", "l", "k", "esc"):
            return
        if self.action_in_progress:
            return

        def run():
            with self.action_lock:
                self.action_in_progress = True
                try:
                    if name == "t":
                        self.drone.takeoff()
                    elif name == "l":
                        self.drone.land()
                    elif name in ("k", "esc"):
                        self.drone.kill()
                finally:
                    self.action_in_progress = False

        threading.Thread(target=run, daemon=True).start()

    # ---- continuous flight loop ----
    def compute_axes(self):
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

    def run(self):
        listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        listener.start()

        print(__doc__)
        print("Listening for keys... hold T to take off, ESC/K to kill, Q to quit.\n")

        try:
            while self.running:
                if not self.action_in_progress:
                    b2, b3, b4, b5 = self.compute_axes()
                    if "up" in self.pressed or "down" in self.pressed:
                        self.drone.throttle = b4
                    self.drone.send_axes(b2, b3, b4, b5, cmd=CMD_IDLE)
                time.sleep(SEND_INTERVAL)
        except KeyboardInterrupt:
            pass
        finally:
            print("\nExiting - sending kill for safety.")
            self.drone.kill()
            listener.stop()


if __name__ == "__main__":
    KeyboardFlyer().run()