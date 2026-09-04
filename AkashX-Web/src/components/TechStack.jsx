import { techStack } from '../data/content';
import useReveal from '../hooks/useReveal';
import './tech-stack.css';

export default function TechStack() {
  const [ref, inView] = useReveal(0.1);

  return (
    <section className="section tech">
      <div className="container">
        <div className={`section-head reveal ${inView ? 'in' : ''}`} ref={ref}>
          <p className="section-tag">Technology stack</p>
          <h2 className="section-title">What it's built on</h2>
        </div>

        <div className="tech-columns">
          <div>
            <p className="tech-col-label">Hardware</p>
            <div className="tech-chips">
              {techStack.hardware.map((h) => (
                <span key={h}>{h}</span>
              ))}
            </div>
          </div>
          <div>
            <p className="tech-col-label">Software</p>
            <div className="tech-chips">
              {techStack.software.map((s) => (
                <span key={s}>{s}</span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
