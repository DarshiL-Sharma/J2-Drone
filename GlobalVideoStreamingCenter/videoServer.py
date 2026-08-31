from flask import Flask, Response
import cv2

from CommunicationCenter.Streaming import VideoStream

app = Flask(__name__)
video_stream = VideoStream()
video_stream.start()


import time

def generate_frames():
    last_sent_time = 0
    target_interval = 1 / 8  # limit to ~8 frames per second

    while True:
        now = time.time()
        if now - last_sent_time < target_interval:
            time.sleep(0.01)
            continue
        last_sent_time = now

        frame = video_stream.get_latest()
        if frame is None:
            time.sleep(0.05)
            continue

        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        frame = cv2.resize(frame, (640, 360))

        encode_params = [cv2.IMWRITE_JPEG_QUALITY, 50]
        ret, buffer = cv2.imencode('.jpg', frame, encode_params)
        if not ret:
            continue

        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
@app.route('/video')
def video():
    return Response(generate_frames(),
                     mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/')
def home():
    return "Drone video server is running! Go to /video to see the stream."


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)