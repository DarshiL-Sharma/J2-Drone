import useReveal from '../hooks/useReveal';
import './impact.css';

const CARDS = [
  { title: 'Faster search', desc: 'Reduce the time required to search disaster areas.' },
  { title: 'Better visibility', desc: 'Combine visual and thermal sensing to help identify difficult-to-see survivors.' },
  { title: 'Safer response', desc: 'Provide rescue teams with useful information before entering uncertain environments.' },
];

const APPLICATIONS = ['Floods', 'Earthquakes', 'Landslides', 'Cyclones', 'Collapsed structures'];

export default function Impact() {
  const [ref, inView] = useReveal(0.1);

  return (
    <section className="section impact">
      <div className="container">
        <div className={`section-head reveal ${inView ? 'in' : ''}`} ref={ref}>
          <p className="section-tag">Impact</p>
          <h2 className="section-title">Designed for the critical first response</h2>
        </div>

        <div className="impact-cards">
          {CARDS.map((c) => (
            <div key={c.title} className="impact-card">
              <h4>{c.title}</h4>
              <p>{c.desc}</p>
            </div>
          ))}
        </div>

        <div className="impact-applications">
          <p className="tech-col-label">Applications</p>
          <div className="tech-chips">
            {APPLICATIONS.map((a) => (
              <span key={a}>{a}</span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
