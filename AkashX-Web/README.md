# AKASH-X — AI-Powered Autonomous Search & Rescue Drone

Website for Smart India Hackathon 2026, Problem Statement SIH26177 (Robotics & Drones — Hardware).

## Stack
React + Vite, Three.js / React Three Fiber for the 3D exploded-view drone and flight
simulation, plain CSS with design tokens in `src/index.css`.

## Getting started

```bash
npm install
npm run dev      # local dev server
npm run build    # production build to /dist
npm run preview  # preview the production build
```

## Structure

```
src/
  data/content.js        Drone parts, roadmap, team, tech stack, trajectory modes
  hooks/useReveal.js      Scroll-reveal intersection observer hook
  components/
    Navbar, Hero, HeroDrone
    ProjectOverview
    ExplodedDrone, ExplodedCanvas, DroneModel   (shared procedural drone geometry)
    SystemArchitecture
    Simulation, SimulationCanvas, SimulationScene
    ComputerVision
    ReverseEngineering
    Roadmap
    Team
    TechStack
    Impact
    FutureSystem
    SimulationCTA
    Footer
```

## Notes

- `DroneModel.jsx` is a single procedural drone built from primitives, shared by the hero
  background and the exploded-view section. Replace it with a GLB/GLTF loader
  (`useGLTF` from `@react-three/drei`) once a real 3D asset is available — the per-part
  `id`/position structure in `src/data/content.js` is already set up for that swap.
- The computer-vision feed and flight simulation are clearly labeled as
  simulation/demo content, per the project's current development stage.
- Colors, type, and spacing tokens live at the top of `src/index.css`.
