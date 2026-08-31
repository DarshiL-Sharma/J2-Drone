import socket
import time

DRONE_IP = "192.168.1.1" # Ip address of the drone*
DRONE_PORT = 7099 # the port for commands 7099 , 8000 for video streaming(work later on it)

packet = bytes.fromhex("03 66 90 74 80 5C 04 3C 99") # the kill command here !


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP (User Data gram Protocol)

print("Sending neutral command...")

for i in range(10):
    sock.sendto(packet, (DRONE_IP, DRONE_PORT))
    print(f"Sent packet {i + 1}/10")
    time.sleep(0.05)

print("Done.")
# 03 66 80 80 80 80 00 00 99 # the first command to(calibrate)

# 03 66 80 80 80 80 01 01 99 # the takeoff command to(make drone up)

# 03 66 90 74 80 5C 04 3C 99 # the kill command to(make the drone off)


