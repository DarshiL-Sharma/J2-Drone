import { useState } from 'react';
import useReveal from '../hooks/useReveal';
import './computer-vision.css';

const BOXES = [
  { top: '34%', left: '18%', w: '11%', h: '22%', conf: 0.87 },
  { top: '52%', left: '61%', w: '9%', h: '19%', conf: 0.79 },
  { top: '22%', left: '73%', w: '8%', h: '16%', conf: 0.68 },
];

const TECHS = ['YOLO', 'OpenCV', 'Python', 'PyTorch'];

export default function ComputerVision() {
  const [ref, inView] = useReveal(0.1);
  const [view, setView] = useState('rgb');

  return (
    <section id="vision" className="section vision">
      <div className="container">
        <div className={`vision-grid reveal ${inView ? 'in' : ''}`} ref={ref}>
          <div className="vision-copy">
            <p className="section-tag">Computer vision</p>
            <h2 className="section-title">Seeing what humans can miss</h2>
            <p className="section-sub">
              AKASH-X uses computer vision to analyze the drone's live video feed and identify
              possible people in the environment.
            </p>

            <div className="vision-tech">
              {TECHS.map((t) => (
                <span key={t}>{t}</span>
              ))}
            </div>

            <div className="vision-toggle">
              <button className={view === 'rgb' ? 'is-active' : ''} onClick={() => setView('rgb')}>
                RGB view
              </button>
              <button className={view === 'thermal' ? 'is-active' : ''} onClick={() => setView('thermal')}>
                Thermal view
              </button>
            </div>
          </div>

          <div className={`vision-feed ${view === 'thermal' ? 'is-thermal' : ''}`}>
            <span className="vision-badge">DEMO FEED · SIMULATION</span>
            <div className="vision-terrain" />
            {BOXES.map((b, i) => (
              <div
                key={i}
                className="vision-box"
                style={{ top: b.top, left: b.left, width: b.w, height: b.h }}
              >
                <span>PERSON {Math.round(b.conf * 100)}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
