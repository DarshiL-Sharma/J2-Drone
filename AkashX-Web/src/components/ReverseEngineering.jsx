import useReveal from '../hooks/useReveal';
import './reverse-engineering.css';

const STEPS = [
  'Capturing drone communication traffic during normal operation',
  'Analyzing control-message structure',
  'Identifying communication patterns',
  'Rebuilding the control layer in Python',
  'Integrating video, navigation and detection above that layer',
];

const FLOW = ['Drone App', 'Communication Analysis', 'Control Layer', 'Python', 'Mission System'];

export default function ReverseEngineering() {
  const [ref, inView] = useReveal(0.1);

  return (
    <section className="section reverse">
      <div className="container">
        <div className={`reverse-grid reveal ${inView ? 'in' : ''}`} ref={ref}>
          <div className="reverse-copy">
            <p className="section-tag">Control &amp; reverse engineering</p>
            <h2 className="section-title">From closed system to open control</h2>
            <p className="section-sub">
              The team studied the communication behaviour of the existing drone platform and
              developed its own software control layer.
            </p>

            <ol className="reverse-steps">
              {STEPS.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ol>

            <span className="status current" style={{ marginTop: 24, display: 'inline-block' }}>
              CONTROL LAYER — ENGINEERING DEVELOPMENT
            </span>
          </div>

          <div className="reverse-flow">
            {FLOW.map((f, i) => (
              <div key={f} className="reverse-flow-item">
                <div className="reverse-node">{f}</div>
                {i < FLOW.length - 1 && <div className="reverse-arrow">↓</div>}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
