import { Suspense, lazy, useMemo, useState } from 'react';
import { droneParts } from '../data/content';
import useReveal from '../hooks/useReveal';
import './exploded-drone.css';

const ExplodedCanvas = lazy(() => import('./ExplodedCanvas'));

export default function ExplodedDrone() {
  const [ref, inView] = useReveal(0.1);
  const [explode, setExplode] = useState(0.7);
  const [selected, setSelected] = useState('rpi');

  const targets = useMemo(() => {
    const t = {};
    droneParts.forEach((p) => { t[p.id] = p.position; });
    return t;
  }, []);

  const active = droneParts.find((p) => p.id === selected);

  return (
    <section id="system" className="section exploded">
      <div className="container">
        <div className={`section-head reveal ${inView ? 'in' : ''}`} ref={ref}>
          <p className="section-tag">System / component breakdown</p>
          <h2 className="section-title">Every part, and what it does</h2>
          <p className="section-sub">
            AKASH-X combines flight hardware, sensing and compute into a single airframe. Drag the
            slider to separate the assembly, and select a component to read its role.
          </p>
        </div>

        <div className="exploded-grid">
          <div className="exploded-viewport">
            <Suspense fallback={<div className="exploded-fallback">Loading model…</div>}>
              <ExplodedCanvas explode={explode} targets={targets} highlighted={selected} />
            </Suspense>

            <div className="exploded-controls">
              <span className="section-tag">ASSEMBLED</span>
              <input
                type="range"
                min={0}
                max={1}
                step={0.01}
                value={explode}
                onChange={(e) => setExplode(parseFloat(e.target.value))}
                aria-label="Explode amount"
              />
              <span className="section-tag">EXPLODED</span>
            </div>
          </div>

          <div className="exploded-panel">
            {active && (
              <div className="exploded-detail">
                <p className="section-tag">{active.short}</p>
                <h3>{active.name}</h3>
                <p>{active.desc}</p>
              </div>
            )}

            <ul className="exploded-list">
              {droneParts.map((p) => (
                <li key={p.id}>
                  <button
                    className={selected === p.id ? 'is-active' : ''}
                    onClick={() => setSelected(p.id)}
                  >
                    {p.name}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
