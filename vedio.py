# video connect by drone camera

import cv2

cap = cv2.VideoCapture('rtsp://192.168.1.1:7070/webcam')

if not cap.isOpened():
    print("Stream nahi khula")
else:
    print("Stream khul gaya!")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Frame nahi mila")
            break
        cv2.imshow('Drone Feed', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()