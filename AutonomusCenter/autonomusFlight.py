from CommandsCenter.Commands import Drone
from INSCenter.DeadReckoningSystem import OpenLoopINS
from AutonomusCenter.AutonomusCommandsCenter.autonomusController import takeoff, move_for_duration, return_home, land

FORWARD_SECONDS = 5
RIGHT_SECONDS = 5


def main():
    drone = Drone()
    ins = OpenLoopINS()

    print("STATUS: TAKING OFF")
    takeoff(drone, ins)

    print("STATUS: MOVING FORWARD")
    move_for_duration(drone, ins, "forward", FORWARD_SECONDS)
    print(f"STATUS: position after forward leg -> {ins.position}")

    print("STATUS: MOVING RIGHT")
    move_for_duration(drone, ins, "right", RIGHT_SECONDS)
    print(f"STATUS: position after right leg -> {ins.position}")

    print("STATUS: RETURNING HOME")
    return_home(drone, ins)
    print(f"STATUS: position after return -> {ins.position}")

    print("STATUS: LANDING")
    land(drone)

    print("STATUS: FLIGHT COMPLETE")


if __name__ == "__main__":
    main()