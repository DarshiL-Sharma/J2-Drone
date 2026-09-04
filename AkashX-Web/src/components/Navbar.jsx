import { useEffect, useState } from 'react';
import './navbar.css';

const LINKS = [
  { href: '#system', label: 'System' },
  { href: '#simulation', label: 'Simulation' },
  { href: '#vision', label: 'Computer Vision' },
  { href: '#roadmap', label: 'Roadmap' },
  { href: '#team', label: 'Team' },
];

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const go = (href) => {
    setOpen(false);
    document.querySelector(href)?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <header className={`navbar ${scrolled ? 'is-scrolled' : ''}`}>
      <div className="navbar-inner container">
        <a href="#top" className="navbar-brand" onClick={(e) => { e.preventDefault(); go('#top'); }}>
          <span className="navbar-mark" aria-hidden="true" />
          AKASH-X
        </a>

        <nav className="navbar-links">
          {LINKS.map((l) => (
            <a key={l.href} href={l.href} onClick={(e) => { e.preventDefault(); go(l.href); }}>
              {l.label}
            </a>
          ))}
        </nav>

        <button className="btn btn-primary navbar-cta" onClick={() => go('#simulation')}>
          Launch simulation
        </button>

        <button className="navbar-toggle" aria-label="Toggle menu" onClick={() => setOpen((v) => !v)}>
          <span />
          <span />
        </button>
      </div>

      {open && (
        <div className="navbar-mobile">
          {LINKS.map((l) => (
            <a key={l.href} href={l.href} onClick={(e) => { e.preventDefault(); go(l.href); }}>
              {l.label}
            </a>
          ))}
          <button className="btn btn-primary" onClick={() => go('#simulation')}>
            Launch simulation
          </button>
        </div>
      )}
    </header>
  );
}
