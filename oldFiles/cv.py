import cv2
from ultralytics import YOLO

model = YOLO('../software/yolov8n.pt')
cap = cv2.VideoCapture('rtsp://192.168.1.1:7070/webcam')

if not cap.isOpened():
    print("Stream nahi khula")
else:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Frame nahi mila")
            break

        results = model(frame)
        annotated_frame = results[0].plot()

        cv2.imshow('Drone Object Detection', annotated_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()