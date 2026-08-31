import math
import time
from ConstantsCenter.constants import CENTER, STICK_MAX, STICK_MIN, CMD_IDLE, SEND_INTERVAL_MS

from CommandsCenter.Commands import Drone
from INSCenter.DeadReckoningSystem import OpenLoopINS


def axes_for_command(drone, command):
    # Same mapping as the manual keyboard's _compute_axes — w/s drive b3 (pitch), a/d drive b2 (roll)
    b2, b3, b4, b5 = CENTER, CENTER, drone.throttle, CENTER

    if command == "forward":
        b3 = STICK_MAX
    elif command == "backward":
        b3 = STICK_MIN
    elif command == "left":
        b2 = STICK_MIN
    elif command == "right":
        b2 = STICK_MAX

    return b2, b3, b4, b5


def move(drone: Drone, ins: OpenLoopINS, command, distance, send_interval_ms=SEND_INTERVAL_MS):
    #  Calculate the moments
    travel_time = distance / ins.SPEED
    b2, b3, b4, b5 = axes_for_command(drone, command)
    print(f"[AUTO] {command}: distance={distance:.2f}m  travel_time={travel_time:.2f}s")

    ux, uy = ins.direction_for_command(command)   # heading stays fixed at 0, no rotation in this control scheme
    ins.UninteruptedJourney(ux, uy)

    period = send_interval_ms / 1000.0
    leg_start = time.time()
    while (time.time() - leg_start) < travel_time:
        drone.send_axes(b2, b3, b4, b5, cmd=CMD_IDLE)   # resent every cycle, same as the manual loop
        ins.refresh()
        time.sleep(period)

    # release back to center — same as letting go of the key
    drone.send_axes(CENTER, CENTER, drone.throttle, CENTER, cmd=CMD_IDLE)
    ins.stop_leg()


def move_for_duration(drone: Drone, ins: OpenLoopINS, command, duration, send_interval_ms=SEND_INTERVAL_MS):
    # Just include the time monito in it
    b2, b3, b4, b5 = axes_for_command(drone, command)
    print(f"[AUTO] {command}: duration={duration:.2f}s")

    ux, uy = ins.direction_for_command(command)
    ins.UninteruptedJourney(ux, uy)

    period = send_interval_ms / 1000.0
    leg_start = time.time()
    while (time.time() - leg_start) < duration:
        drone.send_axes(b2, b3, b4, b5, cmd=CMD_IDLE)
        ins.refresh()
        time.sleep(period)

    drone.send_axes(CENTER, CENTER, drone.throttle, CENTER, cmd=CMD_IDLE)
    ins.stop_leg()


def return_home(drone: Drone, ins: OpenLoopINS):

    x, y = ins.position
    distance = math.hypot(x, y)
    print(f"[AUTO] returning home from x={x:.2f}, y={y:.2f}  distance={distance:.2f}m")

    if distance < 0.01:
        print("[AUTO] already home")
        return

    ux, uy = -x / distance, -y / distance   # unit vector pointing back to origin (trigonometry: normalized -x,-y)

    # scale each axis's deflection by its own component of that direction —
    # this is what makes it a resultant instead of full-deflection-only
    b3 = int(CENTER + ux * (STICK_MAX - CENTER))          # forward/backward axis, proportional to x component
    b2 = int(CENTER - uy * (STICK_MAX - CENTER))          # left/right axis, proportional to y component (sign matches axes_for_command's right=STICK_MAX,left=STICK_MIN)
    b3 = max(STICK_MIN, min(STICK_MAX, b3))                # clamp, in case CENTER isn't perfectly symmetric
    b2 = max(STICK_MIN, min(STICK_MAX, b2))
    b4, b5 = drone.throttle, CENTER

    travel_time = distance / ins.SPEED   # NOTE: still assumes single-axis SPEED even though both axes are pushed at once — see caveat below

    ins.UninteruptedJourney(ux, uy)

    period = SEND_INTERVAL_MS / 1000.0
    leg_start = time.time()
    while (time.time() - leg_start) < travel_time:
        drone.send_axes(b2, b3, b4, b5, cmd=CMD_IDLE)
        ins.refresh()
        time.sleep(period)

    drone.send_axes(CENTER, CENTER, drone.throttle, CENTER, cmd=CMD_IDLE)
    ins.stop_leg()
    print(f"[AUTO] home leg complete, position now: {ins.position}")


def takeoff(drone: Drone, ins: OpenLoopINS):
    print("[AUTO] takeoff")
    drone.takeoff()
    ins.zero_home()   # home is assigned the instant takeoff happens, same as pressing T


def land(drone: Drone):
    print("[AUTO] landing")
    drone.land()