import { Suspense, lazy, useState } from 'react';
import { trajectoryModes } from '../data/content';
import useReveal from '../hooks/useReveal';
import './simulation.css';

const SimulationCanvas = lazy(() => import('./SimulationCanvas'));

export default function Simulation() {
  const [ref, inView] = useReveal(0.1);
  const [mode, setMode] = useState('grid');
  const [hud, setHud] = useState({ altitude: '1.6', x: '0.0', z: '0.0' });

  return (
    <section id="simulation" className="section simulation">
      <div className="container">
        <div className={`section-head reveal ${inView ? 'in' : ''}`} ref={ref}>
          <p className="section-tag">Autonomous flight simulation</p>
          <h2 className="section-title">Test search patterns before flight</h2>
          <p className="section-sub">
            A virtual environment for planning and reviewing search trajectories. This is a
            simulation used for design and testing — not live telemetry.
          </p>
        </div>

        <div className="sim-frame">
          <Suspense fallback={<div className="exploded-fallback">Loading environment…</div>}>
            <SimulationCanvas mode={mode} onUpdate={setHud} />
          </Suspense>

          <div className="sim-hud">
            <div><span>ALTITUDE</span><strong>{hud.altitude} m</strong></div>
            <div><span>POSITION</span><strong>{hud.x}, {hud.z}</strong></div>
            <div><span>MISSION</span><strong>{trajectoryModes.find((m) => m.id === mode)?.label}</strong></div>
            <div><span>SEARCH AREA</span><strong>Sector 04</strong></div>
            <div><span>DETECTION</span><strong>SIMULATED</strong></div>
          </div>

          <span className="sim-badge">SIMULATION</span>
        </div>

        <div className="sim-controls">
          {trajectoryModes.map((m) => (
            <button
              key={m.id}
              className={mode === m.id ? 'is-active' : ''}
              onClick={() => setMode(m.id)}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
