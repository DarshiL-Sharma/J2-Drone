# J2-Drone

This branch contains the ground control dashboard developed for the J2-Drone project.

The dashboard is built using Python and Tkinter. It provides a graphical interface for controlling the drone while keeping the dashboard separate from the main control logic.

## Files

```text
J2-Drone/
├── main.py
├── dashboard.py
└── README.md
```

* `main.py` - Handles the drone control logic.
* `dashboard.py` - Contains the dashboard interface and controls.
* `README.md` - Project documentation.

## Requirements

* Python 3
* Tkinter

Make sure any other dependencies required by `main.py` are installed.

## Running the Dashboard

Make sure `main.py` and `dashboard.py` are in the same directory.

Run:

```bash
python dashboard.py
```

## Controls

The dashboard currently includes controls for drone movement, takeoff, landing, emergency stop, and other operations.

Keyboard controls are also supported for the available controls.

Some controls are still unconfirmed and are marked accordingly in the dashboard. They should not be used with the actual drone until their functionality has been verified.

## Current Status

The dashboard is still under development. The UI and controls may change as the drone control system is tested and updated.

This work is currently being developed on the `arpit` branch.
