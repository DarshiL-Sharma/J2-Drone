import useReveal from '../hooks/useReveal';
import './project-overview.css';

const POINTS = [
  'Search-only approaches can miss people who are hidden, partially covered, or difficult to reach.',
  'Rescue teams can lose critical time navigating uncertain disaster environments.',
  'AKASH-X combines computer vision, live sensing, and autonomous navigation concepts to assist search operations.',
  'The system is designed around a low-cost, deployable architecture.',
];

const METRICS = [
  { label: 'AI Detection', detail: 'YOLO-based person detection on the live video feed.' },
  { label: 'Real-Time Streaming', detail: 'RGB video delivered to the ground station during flight.' },
  { label: 'Autonomous Navigation', detail: 'Waypoint and search-pattern flight, in active development.' },
];

export default function ProjectOverview() {
  const [ref, inView] = useReveal(0.15);

  return (
    <section className="section overview">
      <div className="container">
        <div className={`overview-grid reveal ${inView ? 'in' : ''}`} ref={ref}>
          <div className="overview-copy">
            <p className="section-tag">Project overview</p>
            <h2 className="section-title">Built for the first response</h2>
            <ul className="overview-points">
              {POINTS.map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          </div>

          <div className="overview-metrics">
            {METRICS.map((m) => (
              <div className="metric-card" key={m.label}>
                <h4>{m.label}</h4>
                <p>{m.detail}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
