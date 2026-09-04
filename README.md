# Drone — Autonomous Disaster Response System

Autonomous drone system for disaster-affected areas with on-device AI for survivor and hazard detection (RGB + thermal), built for the Smart India Hackathon (SIH).

## Getting Started

Clone the repository:

```bash
git clone <https://github.com/DarshiL-Sharma/J2-Drone.git>
cd Drone
```

Set up the virtual environment:

```bash
python -m venv .venv

# Activate it
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Run the project:

```bash
python main.py
```

## Project Structure

```
Drone/
├── .venv/                     (library root)
│
├── CommandsCenter/
│   └── Commands.py            <- Puri Commands yahi se control ho rahi he 
│
├── CommunicationCenter/
│   ├── communication.py       <- commands and protocol yahi se 
│   └── Streaming.py           <- Live video/data streaming sab kuch yaha se manage hoga
│
├── ConstantsCenter/
│   └── constants.py           <- Sare Constants yahi pe store he 
│
├── DisplayCenter/
│   └── Display.py             <- Tkinter Logic (UI display) yaha se manage hoga 
│
├── FrontEndCenter/
│   ├── website.css            <- Command center dashboard styling
│   ├── website.html           <- Command center dashboard markup
│   └── website.js             <- Command center dashboard logic
│
├── TestCenter/                <- Customed Folder he testing ke liye
│   └── ...                    
│
├── oldFiles/
│   ├── cv.py                  Deprecated — kept for reference only
│   ├── old.py                 Deprecated — kept for reference only
│   └── old1.py                Deprecated — kept for reference only
│
├── software/                  Core software modules (Basically packages he)
│
├── main.py                    Entry point
└── requirements.txt           Python dependencies
```

## Conventions

- **Constants live in `ConstantsCenter/constants.py`, and only there.** Every constant is written in `ALL_CAPS_WITH_UNDERSCORES` (e.g. `MAX_ALTITUDE_M`, `THERMAL_THRESHOLD_C`). If a value doesn't change at runtime, it belongs in this file, not hardcoded elsewhere.
- Each `*Center` folder is a self-contained module for one subsystem (commands, communication, display, etc.). Keep logic in the folder it belongs to rather than cross-mixing.
- `oldFiles/` holds deprecated code kept only for reference — do not import from it in active code.

## ⚠️ Important — Do Not Modify

- **Do not change existing import paths/statements** without team sign-off — other modules depend on the current structure, and a rename/move will silently break them.
- **Do not change existing constant values in `constants.py`** without discussion — these values are tuned/agreed on for the hardware and detection pipeline, and an unreviewed change can affect flight safety and detection accuracy.
- If a constant genuinely needs to change, open a PR that calls out the old vs. new value and why.

## Testing

All tests go in `TestCenter/`, mirroring the structure of the module they test, e.g.:

```
TestCenter/
├── test_commands.py
├── test_communication.py
├── test_streaming.py
└── test_display.py
```

Run tests with:

```bash
pytest TestCenter/
```
