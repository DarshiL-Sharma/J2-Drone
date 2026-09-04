import { Suspense, lazy } from 'react';
import './hero.css';

const HeroDrone = lazy(() => import('./HeroDrone'));

export default function Hero() {
  const go = (href) => document.querySelector(href)?.scrollIntoView({ behavior: 'smooth' });

  return (
    <section id="top" className="hero">
      <div className="hero-terrain" aria-hidden="true" />
      <div className="hero-canvas" aria-hidden="true">
        <Suspense fallback={null}>
          <HeroDrone />
        </Suspense>
      </div>

      <div className="container hero-content">
        <p className="hero-meta">SMART INDIA HACKATHON 2026</p>

        <h1 className="hero-title">AKASH-X</h1>
        <p className="hero-line">AI-powered autonomous search &amp; rescue</p>

        <p className="hero-support">
          An edge-AI drone platform designed to help rescue teams find people and understand
          disaster environments faster.
        </p>

        <div className="hero-actions">
          <button className="btn btn-primary" onClick={() => go('#system')}>Explore the system</button>
          <button className="btn" onClick={() => go('#simulation')}>View the simulation</button>
        </div>

        <div className="hero-tags">
          <span>SIH26177</span>
          <span>ROBOTICS &amp; DRONES</span>
          <span>HARDWARE</span>
        </div>
      </div>
    </section>
  );
}
