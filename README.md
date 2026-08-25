# J2 Control - Ground Control Dashboard

A Python-based ground control dashboard for controlling a drone over
UDP and monitoring its camera feed.

The project started as a single `main.py` file and was split into
smaller modules so the flight control, packet handling, video
processing, and GUI code are easier to work on independently.

## Features

-   Tkinter-based ground control dashboard
-   UDP communication with the drone
-   Takeoff, land, kill, and calibration controls
-   Camera direction control
-   Keyboard controls using W/A/S/D
-   Throttle control using Up/Down
-   Emergency stop using `K + I`
-   Quick quit using `Q + I`
-   RTSP/OpenCV video stream support
-   YOLO-based person detection
-   Automatic victim image capture
-   HSV-based fire detection
-   Automatic fire image capture
-   Video recording
-   Manual snapshot capture
-   Victim capture gallery
-   Image preview and full-size viewing
-   Mouse wheel and touchpad scrolling in the capture gallery
-   Action and movement logging

## Project Structure

``` text
drone_controller/
│
├── main.py
├── config.py
├── protocol.py
├── drone.py
├── video_stream.py
├── dashboard.py
│
└── software/
    └── yolov8n.pt
```

### `main.py`

The entry point of the application. It only starts the dashboard.

### `config.py`

Contains the configuration and constants used throughout the project,
including drone settings, camera settings, command values, timing
values, capture directories, detection thresholds, and keyboard
mappings.

### `protocol.py`

Contains the low-level, stateless helper functions:

-   `checksum()`
-   `build_frame()`
-   `fix_tilt()`
-   `detect_fire()`

### `drone.py`

Contains the `Drone` class and handles communication with the drone over
UDP.

It is responsible for sending control packets, takeoff, landing,
emergency kill, calibration, camera direction, and basic drone state.

### `video_stream.py`

Contains the `VideoStream` class.

It handles camera capture, frame processing, YOLO inference, fire
detection, person detection, automatic captures, video recording, and
snapshots.

The capture and processing work on separate threads so slow YOLO
inference does not make the displayed video continuously fall behind the
live stream.

### `dashboard.py`

Contains the `DroneDashboard` Tkinter application.

This is the glue between the drone, video stream, and user interface.

It handles the GUI, flight buttons, keyboard input, movement sending,
action queue, status updates, video display, recording, snapshots, and
the victim gallery.

The gallery is intentionally kept in `dashboard.py` because it is
tightly coupled to the Tkinter widgets.

## Requirements

Python 3.9 or newer is recommended.

Install the required packages:

``` bash
pip install opencv-python ultralytics pillow numpy
```

Tkinter is normally included with Python on Windows.

## YOLO Model

The project expects the model at:

``` text
software/yolov8n.pt
```

If the model is somewhere else, change `YOLO_MODEL_PATH` in `config.py`.

## Configuration

Check `config.py` before running the controller.

The main settings are:

``` python
DRONE_IP = "192.168.1.1"
DRONE_PORT = 7099

RTSP_URL = 0
YOLO_MODEL_PATH = "software/yolov8n.pt"
```

`RTSP_URL = 0` uses the default OpenCV camera. If the drone provides an
RTSP stream, replace it with the appropriate RTSP URL.

## Running the Application

From the project directory:

``` bash
python main.py
```

## Keyboard Controls

  Key       Action
  --------- -------------------------
  `W`       Forward
  `S`       Backward
  `A`       Roll
  `D`       Roll
  `Up`      Increase throttle
  `Down`    Decrease throttle
  `Left`    Camera pan
  `Right`   Camera pan
  `T`       Takeoff
  `L`       Land
  `C`       Toggle camera direction
  `R`       Start/stop recording
  `P`       Take snapshot
  `Esc`     Kill
  `K + I`   Emergency stop
  `Q + I`   Quit after sending kill

Movement controls are press-and-hold controls.

## Captures

The application creates an `output` directory when needed:

``` text
output/
│
├── snapshot_*.jpg
├── record_*.avi
│
├── victims/
│   └── victim_*.jpg
│
└── fire/
    └── fire_*.jpg
```

Victim and fire captures have cooldown periods to prevent the same
detection from filling the disk with images.

These values can be changed in `config.py`:

``` python
VICTIM_SAVE_COOLDOWN_SECONDS = 5.0
FIRE_SAVE_COOLDOWN_SECONDS = 5.0
```

## Detection

Person detection is handled by YOLO.

Fire detection currently uses an HSV color threshold instead of a
trained fire-detection model.

The fire detection settings are:

``` python
FIRE_LOWER_HSV
FIRE_UPPER_HSV
FIRE_PIXEL_THRESHOLD
```

These values may need to be adjusted depending on the camera, lighting,
and environment.

## Video Processing

The video pipeline uses two threads:

1.  The capture thread continuously reads the newest camera frame.
2.  The processing thread takes the latest available frame and runs tilt
    correction, fire detection, and YOLO.

Frames are not allowed to build up in a processing queue. If processing
is slower than the camera, older frames are skipped so the dashboard
stays closer to the live feed.

## Safety

Some flight controls in the current configuration are confirmed from
packet captures while others are still marked as unconfirmed in the
dashboard.

Do not assume that an unconfirmed command is safe for real flight.

Test the controller with the drone in a controlled environment before
relying on movement or camera commands.

The `KILL` control is intended as an emergency motor-stop command, but
it should not replace normal flight-safety procedures.

## Notes

The main reason for splitting the project was to avoid keeping
everything inside one large file.

Changes to UDP packet construction belong in `protocol.py`, drone
behavior belongs in `drone.py`, video and detection code belongs in
`video_stream.py`, and Tkinter changes belong in `dashboard.py`.

The application still starts from a single command:

``` bash
python main.py
```
