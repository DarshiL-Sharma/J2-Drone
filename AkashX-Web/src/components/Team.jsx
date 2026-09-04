import { team } from '../data/content';
import useReveal from '../hooks/useReveal';
import './team.css';

export default function Team() {
  const [ref, inView] = useReveal(0.1);

  return (
    <section id="team" className="section team">
      <div className="container">
        <div className={`section-head reveal ${inView ? 'in' : ''}`} ref={ref}>
          <p className="section-tag">Team AkashX</p>
          <h2 className="section-title">The team</h2>
        </div>

        <div className="team-grid">
          {team.map((m) => (
            <div key={m.name} className={`team-card ${m.lead ? 'is-lead' : ''}`}>
              {m.lead && <span className="team-lead-tag">Team Lead</span>}
              <h4>{m.name}</h4>
              <p className="team-role">{m.role}</p>
              <p className="team-desc">{m.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
