import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import MusicTrends    from './pages/MusicTrends';
import GenreBattle    from './pages/GenreBattle';
import MoodMap        from './pages/MoodMap';
import BopOrFlop      from './pages/BopOrFlop';
import ArtistExplorer from './pages/ArtistExplorer';
import './styles/global.css';

// ── Loading screen ─────────────────────────────────────────────────────────
function LoadingScreen({ onDone }) {
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const t1 = setTimeout(() => setPhase(1), 800);
    const t2 = setTimeout(() => setPhase(2), 2400);
    const t3 = setTimeout(() => {
      onDone();
    }, 3000);
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); };
  }, [onDone]);

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9999,
      background: 'radial-gradient(ellipse at center, #0f0f0f 0%, #050505 100%)',
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      gap: 28,
      opacity: phase === 2 ? 0 : 1,
      transition: 'opacity 0.6s ease',
    }}>

      {/* Floating music notes background */}
      {['♪','♫','♩','♬','♭'].map((note, i) => (
        <div key={i} style={{
          position: 'absolute',
          left: `${15 + i * 18}%`,
          top: `${20 + (i % 3) * 20}%`,
          fontSize: 20 + i * 4,
          color: 'rgba(29,185,84,0.08)',
          animation: `floatNote${i} ${3 + i * 0.5}s ease-in-out infinite`,
          pointerEvents: 'none',
        }}>{note}</div>
      ))}

      {/* Headphone */}
      <div style={{
        animation: 'headphonePop 0.8s cubic-bezier(0.34,1.56,0.64,1) forwards',
        opacity: 0,
        filter: 'drop-shadow(0 0 30px rgba(29,185,84,0.4))',
      }}>
        <svg width="130" height="130" viewBox="0 0 130 130" fill="none">
          <circle cx="65" cy="65" r="62" fill="rgba(29,185,84,0.05)" stroke="rgba(29,185,84,0.15)" strokeWidth="1"/>
          <circle cx="65" cy="65" r="48" fill="rgba(29,185,84,0.03)" stroke="rgba(29,185,84,0.08)" strokeWidth="1"/>
          <path d="M22 66 C22 40 40 22 65 22 C90 22 108 40 108 66" stroke="#1db954" strokeWidth="5.5" strokeLinecap="round" fill="none"/>
          <rect x="12" y="62" width="20" height="32" rx="10" fill="#1db954"/>
          <rect x="98" y="62" width="20" height="32" rx="10" fill="#1db954"/>
          <circle cx="22" cy="78" r="6" fill="rgba(0,0,0,0.3)"/>
          <circle cx="108" cy="78" r="6" fill="rgba(0,0,0,0.3)"/>
          {[0,1,2].map(i => (
            <path key={i}
              d={`M${6-i*5} ${60+i*6} C${2-i*5} ${68+i*4} ${2-i*5} ${78+i*4} ${6-i*5} ${86+i*6}`}
              stroke="#1db954" strokeWidth={2-i*0.3} strokeLinecap="round" fill="none"
              opacity={0.6 - i * 0.15}
              style={{ animation: `waveLeft 1.4s ease-in-out infinite`, animationDelay: `${i*0.2}s` }}
            />
          ))}
          {[0,1,2].map(i => (
            <path key={i}
              d={`M${124+i*5} ${60+i*6} C${128+i*5} ${68+i*4} ${128+i*5} ${78+i*4} ${124+i*5} ${86+i*6}`}
              stroke="#1db954" strokeWidth={2-i*0.3} strokeLinecap="round" fill="none"
              opacity={0.6 - i * 0.15}
              style={{ animation: `waveRight 1.4s ease-in-out infinite`, animationDelay: `${i*0.2}s` }}
            />
          ))}
          <text x="65" y="58" textAnchor="middle" fontSize="22" fill="#1db954" fontFamily="serif"
            style={{ animation: 'noteBounce 0.8s ease-in-out infinite alternate' }}>♪</text>
        </svg>
      </div>

      {/* Title */}
      <div style={{
        textAlign: 'center',
        opacity: phase >= 1 ? 1 : 0,
        transform: phase >= 1 ? 'translateY(0)' : 'translateY(20px)',
        transition: 'all 0.7s cubic-bezier(0.34,1.56,0.64,1)',
      }}>
        <div style={{
          fontFamily: 'Syne, sans-serif',
          fontSize: '2.8rem',
          fontWeight: 800,
          letterSpacing: '-1.5px',
          background: 'linear-gradient(135deg, #f0f0f0 0%, #1db954 60%, #f0f0f0 100%)',
          backgroundSize: '200%',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text',
          animation: phase >= 1 ? 'shimmerText 2s ease infinite' : 'none',
        }}>
          Spotilytics
        </div>
        <div style={{
          fontSize: 12,
          color: '#555',
          marginTop: 8,
          letterSpacing: '3px',
          textTransform: 'uppercase',
        }}>
          Where Spotify Meets Analytics
        </div>
      </div>

      {/* Equalizer */}
      <div style={{
        display: 'flex', gap: 5, alignItems: 'flex-end', height: 36,
        opacity: phase >= 1 ? 1 : 0,
        transition: 'opacity 0.4s ease 0.4s',
      }}>
        {[18,28,14,32,20,26,16,30,22].map((h, i) => (
          <div key={i} style={{
            width: 5,
            height: h,
            background: `linear-gradient(to top, #1db954, #25d467)`,
            borderRadius: 3,
            animation: `eqBar 0.${5+i%4}s ease-in-out infinite alternate`,
            animationDelay: `${i * 0.08}s`,
            boxShadow: '0 0 6px rgba(29,185,84,0.4)',
          }} />
        ))}
      </div>

      {/* Group label */}
      <div style={{
        fontSize: 11, color: '#333',
        letterSpacing: '2px',
        textTransform: 'uppercase',
        opacity: phase >= 1 ? 1 : 0,
        transition: 'opacity 0.4s ease 0.6s',
      }}>
        AI-620 · Group 6
      </div>

      <style>{`
        @keyframes headphonePop {
          0%   { opacity:0; transform: scale(0.3) rotate(-20deg); }
          70%  { transform: scale(1.1) rotate(3deg); }
          100% { opacity:1; transform: scale(1) rotate(0deg); }
        }
        @keyframes waveLeft {
          0%,100% { opacity:0.2; transform: scaleX(0.8); }
          50%     { opacity:0.7; transform: scaleX(1); }
        }
        @keyframes waveRight {
          0%,100% { opacity:0.2; transform: scaleX(0.8); }
          50%     { opacity:0.7; transform: scaleX(1); }
        }
        @keyframes noteBounce {
          from { transform: translateY(0) scale(1); }
          to   { transform: translateY(-5px) scale(1.1); }
        }
        @keyframes eqBar {
          from { transform: scaleY(0.3); opacity:0.5; }
          to   { transform: scaleY(1);   opacity:1; }
        }
        @keyframes shimmerText {
          0%   { background-position: 0% 50%; }
          100% { background-position: 200% 50%; }
        }
        @keyframes floatNote0 { 0%,100%{transform:translateY(0) rotate(0deg)} 50%{transform:translateY(-20px) rotate(10deg)} }
        @keyframes floatNote1 { 0%,100%{transform:translateY(0) rotate(0deg)} 50%{transform:translateY(-15px) rotate(-8deg)} }
        @keyframes floatNote2 { 0%,100%{transform:translateY(0) rotate(0deg)} 50%{transform:translateY(-25px) rotate(12deg)} }
        @keyframes floatNote3 { 0%,100%{transform:translateY(0) rotate(0deg)} 50%{transform:translateY(-18px) rotate(-6deg)} }
        @keyframes floatNote4 { 0%,100%{transform:translateY(0) rotate(0deg)} 50%{transform:translateY(-22px) rotate(9deg)} }
      `}</style>
    </div>
  );
}

// ── Nav ────────────────────────────────────────────────────────────────────
function Nav() {
  return (
    <nav className="nav">
      <div className="nav-brand">
        <span className="nav-logo">♪</span>
        <span className="nav-title">Spotilytics</span>
      </div>
      <div className="nav-links">
        <NavLink to="/"                className={({isActive}) => isActive ? 'nav-link active' : 'nav-link'}>Music Trends</NavLink>
        <NavLink to="/genre-battle"    className={({isActive}) => isActive ? 'nav-link active' : 'nav-link'}>Genre Battle</NavLink>
        <NavLink to="/mood-map"        className={({isActive}) => isActive ? 'nav-link active' : 'nav-link'}>Mood Map</NavLink>
        <NavLink to="/artist-explorer" className={({isActive}) => isActive ? 'nav-link active' : 'nav-link'}>Artist Explorer</NavLink>
        <NavLink to="/bop-or-flop"     className={({isActive}) => isActive ? 'nav-link active' : 'nav-link'}>BopOrFlop</NavLink>
      </div>
    </nav>
  );
}

// ── App ────────────────────────────────────────────────────────────────────
export default function App() {
  const [loading, setLoading] = useState(true);

  return (
    <>
      {loading && <LoadingScreen onDone={() => setLoading(false)} />}
      <BrowserRouter>
        <div className="app" style={{
          opacity: loading ? 0 : 1,
          transition: 'opacity 0.5s ease',
        }}>
          <Nav />
          <main className="main">
            <Routes>
              <Route path="/"                element={<MusicTrends />} />
              <Route path="/genre-battle"    element={<GenreBattle />} />
              <Route path="/mood-map"        element={<MoodMap />} />
              <Route path="/artist-explorer" element={<ArtistExplorer />} />
              <Route path="/bop-or-flop"     element={<BopOrFlop />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </>
  );
}