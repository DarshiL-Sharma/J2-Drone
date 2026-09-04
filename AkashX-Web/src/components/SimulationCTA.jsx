import './simulation-cta.css';

export default function SimulationCTA() {
  const go = () => document.querySelector('#simulation')?.scrollIntoView({ behavior: 'smooth' });

  return (
    <section className="section sim-cta">
      <div className="container sim-cta-inner">
        <h2>See AKASH-X in motion</h2>
        <p>
          Explore the virtual mission environment and see how autonomous search trajectories can
          be planned, simulated and tested before real-world deployment.
        </p>
        <button className="btn btn-primary" onClick={go}>Launch simulation</button>
      </div>
    </section>
  );
}
