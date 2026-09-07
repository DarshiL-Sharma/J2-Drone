# 🚁 J2-Drone — Autonomous Disaster Response System

> An intelligent autonomous drone platform for disaster-affected areas with on-device AI for survivor detection and hazard identification. Built for the **Smart India Hackathon (SIH)** with multi-sensor capabilities (RGB + thermal imaging) and real-time command center control.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Status](https://img.shields.io/badge/status-active-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

---

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Installation & Setup](#installation--setup)
- [Project Structure](#project-structure)
- [Module Documentation](#module-documentation)
- [Development Conventions](#development-conventions)
- [Testing](#testing)
- [Contributing Guidelines](#contributing-guidelines)
- [Troubleshooting](#troubleshooting)

---

## 📖 Project Overview

**J2-Drone** is an autonomous drone system designed to assist in disaster management and relief operations. The system combines:

- **On-Device AI**: Real-time survivor and hazard detection using computer vision
- **Multi-Sensor Fusion**: RGB camera + thermal imaging for comprehensive environmental awareness
- **Remote Command Center**: Web-based dashboard for real-time drone control and monitoring
- **Live Streaming**: Low-latency video streaming from drone to ground station
- **Autonomous Navigation**: INS (Inertial Navigation System) for precise positioning

The platform prioritizes **fast deployment**, **local processing** (no cloud dependency), and **reliability in emergency scenarios**.

---

## ✨ Key Features

### 🎯 Core Capabilities
- **Autonomous Flight Control** — Automatic takeoff, landing, and waypoint navigation
- **Real-Time Detection** — Survivor identification and hazard detection on edge device
- **Dual Imaging** — RGB + thermal sensor fusion for day/night operation
- **Live Command Center** — Web dashboard for remote operator control
- **Streaming Protocol** — Efficient video/telemetry streaming over various network conditions
- **INS Navigation** — Precise drone positioning and altitude hold

### 🔧 System Integration
- **Modular Architecture** — Independent centers for commands, communication, display, etc.
- **Extensible Design** — Easy to add new sensors or detection algorithms
- **Configuration Management** — Centralized constants for quick tuning
- **Error Handling** — Robust communication and failsafe mechanisms

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    COMMAND CENTER (GUI)                      │
│            ↓                                    ↓             │
├─────────────────────────────────────────────────────────────┤
│  DisplayCenter  │  FrontEndCenter  │  CommandsCenter         │
│  (Tkinter UI)   │  (Web Dashboard) │  (Drone Commands)       │
└────────┬─────────────────┬────────────────────┬──────────────┘
         │                 │                    │
         └─────────────────┴────────────────────┘
                    │
         ┌──────────┴──────────┐
         │                     │
    ┌────▼──────────────┐   ┌─▼──────────────┐
    │ CommunicationCtr  │   │ ConstantsCenter│
    │ (Protocols/Data)  │   │ (Config Values)│
    └────┬──────────────┘   └────────────────┘
         │
    ┌────▼─────────────────────────┐
    │   DRONE HARDWARE              │
    │ ├─ Flight Controller          │
    │ ├─ RGB Camera                 │
    │ ├─ Thermal Camera             │
    │ ├─ IMU/Barometer (INS)        │
    │ └─ Communication Module       │
    └──────────────────────────────┘
```

---

## 🚀 Installation & Setup

### Prerequisites
- **Python 3.8** or higher
- **pip** (Python package manager)
- Virtual environment (recommended)
- Operating System: Windows, macOS, or Linux

### Step 1: Clone the Repository

```bash
git clone https://github.com/DarshiL-Sharma/J2-Drone.git
cd J2-Drone
```

### Step 2: Create Virtual Environment

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Run the Application

```bash
python main.py
```

The system will launch the main Tkinter interface. Verify all systems are operational before flight.

---

## 📁 Project Structure

```
J2-Drone/
│
├── 📄 main.py                          ← Entry point (starts DisplayCenter)
├── 📄 requirements.txt                 ← Python dependencies
├── 📄 README.md                        ← This file
├── 📄 .gitignore                       ← Git ignore rules
│
├── 📦 AutonomusCenter/                 ← Autonomous flight logic
│   └── autonomy.py                     ← Waypoint navigation, flight modes
│
├── 📦 CloudCenter/                     ← Cloud integration (future)
│   └── cloud_sync.py
│
├── 📦 CommandsCenter/                  ← Drone command generation
│   ├── Commands.py                     ← Command building & execution
│   └── command_queue.py
│
├── 📦 CommunicationCenter/             ← Protocol & streaming
│   ├── communication.py                ← MAVLink/Protocol handler
│   ├── Streaming.py                    ← Video/telemetry streaming
│   └── serial_handler.py
│
├── 📦 ConstantsCenter/                 ← Configuration (SINGLE SOURCE OF TRUTH)
│   ├── constants.py                    ← All tunable parameters
│   └── hw_config.py                    ← Hardware-specific settings
│
├── 📦 DisplayCenter/                   ← UI Layer (Tkinter)
│   ├── Display.py                      ← Main Tkinter window
│   ├── widgets.py                      ← Custom UI components
│   └── telemetry_display.py            ← Telemetry visualization
│
├── 📦 FrontEndCenter/                  ← Web Command Dashboard
│   ├── website.html                    ← Dashboard markup
│   ├── website.css                     ← Dashboard styling
│   ├── website.js                      ← Dashboard interactivity
│   └── server.py                       ← Flask/FastAPI backend
│
├── 📦 GlobalVideoStreamingCenter/      ← Video streaming pipeline
│   ├── frame_processor.py              ← Frame capture & encoding
│   ├── stream_server.py                ← Streaming protocol
│   └── compression.py
│
├── 📦 INSCenter/                       ← Inertial Navigation System
│   ├── ins_filter.py                   ← IMU fusion algorithm
│   ├── altitude_estimator.py           ← Barometric altitude calc
│   └── position_tracking.py            ← XYZ position estimate
│
├── 📦 software/                        ← Core packages (reusable modules)
│   ├── detection/                      ← AI detection models
│   │   ├── survivor_detector.py        ← Human detection model
│   │   ├── hazard_detector.py          ← Fire/debris detection
│   │   └── thermal_processor.py        ← Thermal image processing
│   ├── utils/                          ← Utility functions
│   │   ├── logger.py                   ← Logging setup
│   │   ├── error_handler.py            ← Exception handling
│   │   └── validators.py               ← Input validation
│   └── drivers/                        ← Hardware drivers
│       ├── camera_driver.py            ← Camera interface
│       └── imu_driver.py               ← IMU/sensor interface
│
├── 📦 TestCenter/                      ← Unit & integration tests
│   ├── test_commands.py                ← CommandsCenter tests
│   ├── test_communication.py           ← CommunicationCenter tests
│   ├── test_streaming.py               ← Streaming tests
│   ├── test_display.py                 ← UI tests
│   ├── test_detection.py               ← AI detection tests
│   └── conftest.py                     ← Pytest configuration
│
├── 📦 oldFiles/                        ← DEPRECATED (reference only)
│   ├── cv.py
│   ├── old.py
│   └── old1.py
│
└── 📦 __pycache__/                     ← Python bytecode (ignored)
```

---

## 📚 Module Documentation

### **CommandsCenter** — Drone Command Interface
Generates and sends commands to the drone's flight controller.

**Key Classes:**
- `CommandBuilder` — Constructs MAVLink/custom protocol commands
- `CommandQueue` — Manages command execution queue
- `CommandValidator` — Validates commands before sending

**Example:**
```python
from CommandsCenter.Commands import CommandBuilder

builder = CommandBuilder()
cmd = builder.create_takeoff(altitude=10)  # 10m takeoff
send_to_drone(cmd)
```

---

### **CommunicationCenter** — Protocol & Streaming
Handles all drone-to-ground communication and live video/telemetry streaming.

**Key Modules:**
- `communication.py` — Protocol implementation (MAVLink, custom serial)
- `Streaming.py` — Video/data streaming over TCP/UDP
- `serial_handler.py` — Serial port communication

**Example:**
```python
from CommunicationCenter.communication import DroneLink
from CommunicationCenter.Streaming import VideoStreamer

link = DroneLink(port="/dev/ttyUSB0", baudrate=115200)
streamer = VideoStreamer(target="192.168.1.100", port=5000)
streamer.start()
```

---

### **ConstantsCenter** — Configuration (SINGLE SOURCE OF TRUTH)
**All constants must be defined here.** No magic numbers in code!

**Convention:** All constants use `ALL_CAPS_WITH_UNDERSCORES`

**Example structure:**
```python
# ConstantsCenter/constants.py

# Flight Limits
MAX_ALTITUDE_M = 120
MIN_SAFE_ALTITUDE_M = 5
MAX_SPEED_MS = 20
MAX_TILT_DEG = 45

# Detection Thresholds
SURVIVOR_CONFIDENCE_MIN = 0.75
THERMAL_ANOMALY_THRESHOLD_C = 45.0

# Communication
SERIAL_BAUDRATE = 115200
STREAMING_BITRATE_KBPS = 2500
```

---

### **DisplayCenter** — Tkinter User Interface
The ground control station UI for operators.

**Features:**
- Real-time telemetry display (altitude, speed, position)
- Live video feed with overlays (detections, grid)
- Command buttons (takeoff, land, emergency stop)
- Sensor health indicators
- Flight log viewer

**Example:**
```python
from DisplayCenter.Display import DroneApp

app = DroneApp()
app.mainloop()  # Runs Tkinter event loop
```

---

### **FrontEndCenter** — Web Dashboard
Browser-based command center for remote operations.

**Files:**
- `website.html` — Dashboard structure
- `website.css` — Responsive styling
- `website.js` — Real-time updates & control
- `server.py` — WebSocket/REST API backend

**Features:**
- 3D map view of drone position
- Live video stream
- Command palette
- Telemetry graphs
- Detection log

---

### **GlobalVideoStreamingCenter** — Video Streaming Pipeline
Efficient streaming with adaptive bitrate and compression.

**Modules:**
- `frame_processor.py` — Frame capture, resizing, encoding
- `stream_server.py` — Streaming server (RTMP/RTP/custom)
- `compression.py` — H.264/H.265 encoding

---

### **INSCenter** — Inertial Navigation System
Fuses IMU + barometric data for precise positioning.

**Algorithm:**
1. Capture IMU accelerometer + gyroscope data
2. Fuse with barometric altitude
3. Estimate XYZ position & velocity
4. Correct drift using GPS (if available)

**Example:**
```python
from INSCenter.ins_filter import EKF_INS

ins = EKF_INS()
state = ins.update(accel=(0.1, 0.05, 9.8), gyro=(0, 0, 0.02), alt=25.3)
print(f"Position: {state.position}, Velocity: {state.velocity}")
```

---

### **software/detection** — AI Detection Models
Computer vision for survivor and hazard detection.

**Modules:**
- `survivor_detector.py` — Human body detection (YOLOv8 / ResNet)
- `hazard_detector.py` — Fire/debris/obstacles detection
- `thermal_processor.py` — Thermal image enhancement & analysis

**Example:**
```python
from software.detection.survivor_detector import SurvivorDetector

detector = SurvivorDetector(model_path="models/yolov8_humans.pt")
results = detector.detect(frame)  # Returns bboxes + confidence

for detection in results:
    print(f"Human at {detection.bbox}, confidence: {detection.conf}")
```

---

## 🛠️ Development Conventions

### **1. Constants Only in ConstantsCenter**
❌ **WRONG:**
```python
# In CommandsCenter/Commands.py
MAX_ALT = 120  # Magic number!
```

✅ **RIGHT:**
```python
# In ConstantsCenter/constants.py
MAX_ALTITUDE_M = 120

# In CommandsCenter/Commands.py
from ConstantsCenter.constants import MAX_ALTITUDE_M
```

### **2. Module Independence**
Each `*Center` is self-contained. Avoid circular imports:
- ✅ `CommandsCenter` → `ConstantsCenter` (OK)
- ❌ `CommandsCenter` → `CommunicationCenter` → `CommandsCenter` (BAD)

### **3. Import Paths**
Never change import paths without team sign-off. Other modules depend on the current structure:

```python
# Established imports — do NOT change these without approval
from CommandsCenter.Commands import CommandBuilder
from CommunicationCenter.communication import DroneLink
from ConstantsCenter.constants import MAX_ALTITUDE_M
```

### **4. Logging**
Use the centralized logger:

```python
from software.utils.logger import get_logger

logger = get_logger(__name__)
logger.info("Drone armed successfully")
logger.warning("Low battery: 15%")
logger.error("Motor 3 failed!")
```

### **5. Error Handling**
Use custom exceptions from `software.utils.error_handler`:

```python
from software.utils.error_handler import CommunicationError, SafetyViolation

try:
    link.send_command(cmd)
except CommunicationError as e:
    logger.error(f"Failed to send command: {e}")
    # Implement fallback
```

### **6. Configuration/Constant Changes**
Any tuning of constants requires a PR with clear justification:

```
PR Title: Increase MAX_ALTITUDE from 100m to 120m for extended search ops

Changed in ConstantsCenter/constants.py:
- OLD: MAX_ALTITUDE_M = 100
+ NEW: MAX_ALTITUDE_M = 120

Reason: New hardware (more powerful battery) supports higher altitude.
        Testing complete at test range.
```

---

## 🧪 Testing

All tests belong in `TestCenter/`, mirroring the module structure.

### Test Organization

```
TestCenter/
├── test_commands.py           ← Tests for CommandsCenter
├── test_communication.py       ← Tests for CommunicationCenter
├── test_streaming.py          ← Tests for GlobalVideoStreamingCenter
├── test_display.py            ← Tests for DisplayCenter
├── test_detection.py          ← Tests for software/detection
└── conftest.py                ← Pytest configuration & fixtures
```

### Running Tests

```bash
# Run all tests
pytest TestCenter/

# Run specific test file
pytest TestCenter/test_commands.py

# Run with coverage
pytest TestCenter/ --cov=. --cov-report=html

# Run with verbose output
pytest TestCenter/ -v

# Run specific test
pytest TestCenter/test_commands.py::test_takeoff_command
```

### Writing Tests

**Example test structure:**
```python
# TestCenter/test_commands.py
import pytest
from CommandsCenter.Commands import CommandBuilder
from ConstantsCenter.constants import MAX_ALTITUDE_M

class TestCommandBuilder:
    
    def test_takeoff_command_valid(self):
        builder = CommandBuilder()
        cmd = builder.create_takeoff(altitude=10)
        assert cmd.type == "TAKEOFF"
        assert cmd.altitude == 10
    
    def test_takeoff_exceeds_max_altitude(self):
        builder = CommandBuilder()
        with pytest.raises(ValueError):
            builder.create_takeoff(altitude=MAX_ALTITUDE_M + 50)
    
    def test_land_command(self):
        builder = CommandBuilder()
        cmd = builder.create_land()
        assert cmd.type == "LAND"
```

---

## 👥 Contributing Guidelines

### Before You Start
1. **Understand the architecture** — Read this README and module docs
2. **Follow conventions** — Constants go in `ConstantsCenter`, imports are established
3. **Sync with team** — Don't rename/move existing code without discussion

### Workflow

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes** following conventions above

3. **Write tests** in `TestCenter/` for your changes

4. **Test locally:**
   ```bash
   pytest TestCenter/ -v
   ```

5. **Commit with clear messages:**
   ```bash
   git commit -m "Add thermal detection to hazard module

   - Implemented ThermalDetector class
   - Added unit tests in test_detection.py
   - Tuned THERMAL_THRESHOLD_C constant
   - Verified with thermal dataset"
   ```

6. **Push and open a PR:**
   ```bash
   git push origin feature/your-feature-name
   ```

### PR Checklist
- [ ] Tests pass (`pytest TestCenter/`)
- [ ] No changes to import paths without approval
- [ ] Constants updated in `ConstantsCenter/` (not hardcoded)
- [ ] Code follows Python style (PEP 8)
- [ ] PR description explains what & why
- [ ] No deprecated code imported

---

## 🔧 Troubleshooting

### Issue: ImportError when running `python main.py`

**Cause:** Virtual environment not activated or dependencies not installed

**Solution:**
```bash
# Activate venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate      # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

---

### Issue: Serial connection fails (Cannot open port)

**Cause:** Drone not connected or port name incorrect

**Solution:**
```python
# In ConstantsCenter/constants.py, update:
SERIAL_PORT = "/dev/ttyUSB0"  # or COM3 on Windows
SERIAL_BAUDRATE = 115200

# On Windows, find COM port in Device Manager
# On Linux/Mac: ls /dev/tty*
```

---

### Issue: Video streaming not working

**Cause:** Network issue or streaming server not started

**Solution:**
```bash
# Check if streaming is enabled in constants
# In DisplayCenter/Display.py or FrontEndCenter/server.py:
ENABLE_STREAMING = True
STREAM_PORT = 5000

# Verify network connectivity
ping 192.168.1.100  # (target streaming IP)
```

---

### Issue: Drone not responding to commands

**Cause:** Communication protocol mismatch or hardware issue

**Solution:**
1. Check `CommunicationCenter/communication.py` protocol settings
2. Verify baudrate in `ConstantsCenter/constants.py`
3. Check drone firmware compatibility
4. Review logs in `TestCenter/test_communication.py`

---

## 📝 License

This project is licensed under the **MIT License** — see LICENSE file for details.

---

## 📞 Support & Contact

- **Author:** DarshiL-Sharma
- **GitHub:** https://github.com/DarshiL-Sharma/J2-Drone
- **Issues:** [Report a bug](https://github.com/DarshiL-Sharma/J2-Drone/issues)

---

## 🎯 Roadmap

- [ ] Multi-drone coordination
- [ ] Cloud data sync with offline-first fallback
- [ ] Advanced ML models (object segmentation, trajectory prediction)
- [ ] Web dashboard expansion (3D terrain mapping)
- [ ] Hardware abstraction layer (support multiple drone platforms)
- [ ] Formal documentation site

---

**Happy flying! 🚁**
