import useReveal from '../hooks/useReveal';
import './system-architecture.css';

export default function SystemArchitecture() {
  const [ref, inView] = useReveal(0.1);

  return (
    <section className="section architecture">
      <div className="container">
        <div className={`section-head reveal ${inView ? 'in' : ''}`} ref={ref}>
          <p className="section-tag">System architecture</p>
          <h2 className="section-title">How sensing becomes a decision</h2>
          <p className="section-sub">
            Data from the drone's sensors flows through a single onboard pipeline, from raw
            capture to a flight command.
          </p>
        </div>

        <div className="arch-diagram">
          <div className="arch-main">
            <div className="arch-row arch-inputs">
              <div className="arch-node small">RGB Camera</div>
              <div className="arch-node small">Thermal Camera</div>
              <div className="arch-node small">Position / IMU Data</div>
            </div>
            <div className="arch-connector" />
            <div className="arch-node">Sensing Layer</div>
            <div className="arch-connector" />
            <div className="arch-node">Raspberry Pi 5</div>
            <div className="arch-connector" />
            <div className="arch-node">AI / Computer Vision</div>
            <div className="arch-connector" />
            <div className="arch-node accent">Mission Manager</div>
            <div className="arch-connector" />
            <div className="arch-node">Navigation + Route Planning</div>
            <div className="arch-connector" />
            <div className="arch-node">Flight Controller</div>
            <div className="arch-connector" />
            <div className="arch-node small">Drone</div>
          </div>

          <div className="arch-side">
            <div className="arch-branch">
              <div className="arch-node small">Live Video</div>
              <div className="arch-connector short" />
              <div className="arch-node small">Streaming</div>
              <div className="arch-connector short" />
              <div className="arch-node small">Ground Control</div>
            </div>
            <div className="arch-branch">
              <div className="arch-node small">SOS / Priority Input</div>
              <div className="arch-connector short" />
              <div className="arch-node small ghost">→ Mission Manager</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
