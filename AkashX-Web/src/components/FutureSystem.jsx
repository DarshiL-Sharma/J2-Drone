import useReveal from '../hooks/useReveal';
import './future-system.css';

const CURRENT = ['Prebuilt drone', 'Wi-Fi control', 'AI detection in development', 'Video streaming'];
const FUTURE = [
  'Custom hardware',
  'Dedicated telemetry',
  'Multi-sensor fusion',
  'Position estimation',
  'Autonomous navigation',
  'Autonomous search',
];

export default function FutureSystem() {
  const [ref, inView] = useReveal(0.1);

  return (
    <section className="section future">
      <div className="container">
        <div className={`section-head reveal ${inView ? 'in' : ''}`} ref={ref}>
          <p className="section-tag">Current beta → future AKASH-X</p>
          <h2 className="section-title">What exists today, and what we're building toward</h2>
        </div>

        <div className="future-compare">
          <div className="future-col">
            <span className="status current">CURRENT BETA</span>
            <ul>
              {CURRENT.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          </div>

          <div className="future-arrow">→</div>

          <div className="future-col is-future">
            <span className="status future">FUTURE · ROADMAP</span>
            <ul>
              {FUTURE.map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
