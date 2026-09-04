import { roadmap } from '../data/content';
import useReveal from '../hooks/useReveal';
import './roadmap.css';

const LABEL = { done: 'DONE', current: 'CURRENT', next: 'NEXT', future: 'FUTURE' };

export default function Roadmap() {
  const [ref, inView] = useReveal(0.1);

  return (
    <section id="roadmap" className="section roadmap">
      <div className="container">
        <div className={`section-head reveal ${inView ? 'in' : ''}`} ref={ref}>
          <p className="section-tag">Development roadmap</p>
          <h2 className="section-title">Progressive engineering toward autonomy</h2>
          <p className="section-sub">
            Each stage builds on the last, moving from understanding the existing platform to a
            fully autonomous search capability.
          </p>
        </div>

        <ol className="roadmap-list">
          {roadmap.map((r) => (
            <li key={r.n} className={`roadmap-item status-${r.status}`}>
              <span className="roadmap-n">{r.n}</span>
              <div className="roadmap-body">
                <h4>{r.title}</h4>
                <p>{r.detail}</p>
              </div>
              <span className={`status ${r.status}`}>{LABEL[r.status]}</span>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
