export const droneParts = [
  {
    id: 'frame',
    name: '450MM DRONE FRAME',
    short: 'Structural airframe',
    desc: 'Quadcopter frame carrying all propulsion, compute and sensing hardware.',
    position: [0, 0, 0],
  },
  {
    id: 'motors',
    name: 'BLDC MOTORS',
    short: 'Propulsion',
    desc: 'Brushless motors driving each rotor arm, controlled independently for lift and attitude.',
    position: [1.6, 0.15, 1.6],
  },
  {
    id: 'props',
    name: '10–12" PROPELLERS',
    short: 'Lift generation',
    desc: 'Fixed-pitch propellers matched to the BLDC motors for stable hover and controlled thrust.',
    position: [1.6, 0.55, 1.6],
  },
  {
    id: 'esc',
    name: 'ESCs (20–30A)',
    short: 'Motor control',
    desc: 'Electronic speed controllers translating flight-controller commands into motor output.',
    position: [-1.4, -0.1, 1.2],
  },
  {
    id: 'pixhawk',
    name: 'PIXHAWK',
    short: 'Flight controller',
    desc: 'Dedicated flight controller responsible for stabilization and low-level flight control.',
    position: [0, 0.35, 0],
  },
  {
    id: 'battery',
    name: 'LIPO BATTERY — 5000MAH',
    short: 'Power system',
    desc: 'Primary power source sized for the current airframe and payload during test flights.',
    position: [0, -0.45, -0.3],
  },
  {
    id: 'rxtx',
    name: 'TRANSMITTER / RECEIVER',
    short: 'Manual link',
    desc: 'RC uplink used for manual override and safety pilot control during testing.',
    position: [-1.6, 0.4, -1.4],
  },
  {
    id: 'rpi',
    name: 'RASPBERRY PI 5',
    short: 'Companion computer',
    desc: 'Companion computing platform for AI inference, sensor fusion and higher-level autonomy.',
    position: [0, 0.7, 0.55],
  },
  {
    id: 'rgb',
    name: 'RGB CAMERA',
    short: 'Visual sensing',
    desc: 'Primary visual sensing source for live video and computer vision.',
    position: [0.5, 0.35, 1.1],
  },
  {
    id: 'thermal',
    name: 'FLIR LEPTON THERMAL',
    short: 'Thermal sensing',
    desc: 'Provides thermal information to improve detection in difficult visual conditions.',
    position: [-0.5, 0.35, 1.1],
  },
  {
    id: 'telemetry',
    name: '915MHz TELEMETRY RADIO',
    short: 'Data link',
    desc: 'Long-range radio link carrying telemetry between the drone and ground station.',
    position: [1.5, 0.55, -1.3],
  },
  {
    id: 'ground',
    name: 'GROUND SUPPORT SYSTEM',
    short: 'Ground control',
    desc: 'Laptop-based control and monitoring station receiving video, telemetry and status data.',
    position: [0, -1.6, -2.6],
  },
];

export const roadmap = [
  { n: '01', title: 'Capture & Understand', detail: 'Studying the existing drone platform and how it communicates during normal operation.', status: 'done' },
  { n: '02', title: 'Decode Control Layer', detail: 'Analyzing control-message structure and identifying communication patterns.', status: 'done' },
  { n: '03', title: 'Safe Software Control', detail: 'Rebuilding a minimal, safe control layer in Python on top of the analyzed protocol.', status: 'current' },
  { n: '04', title: 'Full Laptop Control', detail: 'Complete flight command set available from the ground control application.', status: 'current' },
  { n: '05', title: 'Live Video', detail: 'RGB video streamed from the drone to the ground station in real time.', status: 'current' },
  { n: '06', title: 'Unified Dashboard', detail: 'Video, controls and detection output combined into a single laptop application.', status: 'next' },
  { n: '07', title: 'Position Data', detail: 'Onboard position and IMU data made available to the ground system.', status: 'next' },
  { n: '08', title: 'Position Estimation', detail: 'Fusing sensor data into a usable position estimate for mission planning.', status: 'future' },
  { n: '09', title: 'Point-to-Point Navigation', detail: 'Commanding the drone to fly between defined waypoints autonomously.', status: 'future' },
  { n: '10', title: 'Autonomous Search', detail: 'Independent execution of search patterns across a defined disaster area.', status: 'future' },
];

export const team = [
  {
    name: 'Darshil Sharma',
    role: 'Commands, Control & Reverse Engineering',
    desc: 'Leads the team and works on drone command/control systems, understanding the existing platform and developing the software control layer through reverse engineering.',
    lead: true,
  },
  {
    name: 'Arpit Charpe',
    role: 'YOLO, OpenCV, Streaming & Computer Vision',
    desc: 'Works on YOLO-based detection, OpenCV, video streaming and image-processing pipelines.',
  },
  {
    name: 'Ayush Nainawadiya',
    role: 'YOLO, OpenCV, Streaming & Computer Vision',
    desc: 'Works on computer vision, YOLO, OpenCV, live streaming and image-processing integration.',
  },
  {
    name: 'Dhruv',
    role: 'Hardware Research & System References',
    desc: 'Researches suitable hardware components, studies system requirements, and finds technical references for models and components.',
  },
  {
    name: 'Ayushi',
    role: 'Project Testing, Gap Analysis & Website',
    desc: 'Focuses on finding loopholes and gaps in the project, testing the system and contributing to the development of the project website.',
  },
  {
    name: 'Aryan',
    role: 'Autonomous Features, Simulation & Testing',
    desc: 'Works on autonomous features, the simulator/virtual-world environment and testing the system\u2019s navigation behaviour.',
  },
];

export const techStack = {
  hardware: [
    'Raspberry Pi 5',
    'Pixhawk',
    'BLDC Motors',
    'RGB Camera',
    'FLIR Lepton Thermal Camera',
    'LiPo Battery',
    'Telemetry Radio',
  ],
  software: [
    'Python',
    'OpenCV',
    'YOLOv8',
    'PyTorch',
    'RTSP',
    'MAVLink',
    'Flask',
    'Flutter',
    'Linux / Ubuntu',
  ],
};

export const trajectoryModes = [
  { id: 'grid', label: 'GRID' },
  { id: 'zigzag', label: 'ZIG-ZAG' },
  { id: 'spiral', label: 'SPIRAL' },
  { id: 'waypoint', label: 'WAYPOINT' },
  { id: 'return', label: 'RETURN' },
];
