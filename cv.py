import socket
import time
import cv2

DRONE_IP = "192.168.1.1"
DRONE_PORT = 8000

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

CONNECT = bytes.fromhex("03 66 80 80 80 80 00 00 99")
TAKEOFF = bytes.fromhex("03 66 80 80 80 80 01 01 99")
LAND    = bytes.fromhex("03 66 90 74 80 5C 04 3C 99")

def send_command(packet, times=10, delay=0.05):
    for i in range(times):
        sock.sendto(packet, (DRONE_IP, DRONE_PORT))
        time.sleep(delay)

# Step A: Drone se "handshake" jaisa connect command bhejo
send_command(CONNECT)
print("Drone connected!")

# Step B: Video stream shuru karo
cap = cv2.VideoCapture(f'http://{DRONE_IP}:8000')

if not cap.isOpened():
    print("Video stream nahi khula")
else:
    print("Video stream chalu!")
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        cv2.imshow('Drone Feed', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()