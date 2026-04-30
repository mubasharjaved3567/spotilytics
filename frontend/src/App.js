import React from 'react';
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import MusicTrends from './pages/MusicTrends';
import GenreBattle from './pages/GenreBattle';
import MoodMap     from './pages/MoodMap';
import BopOrFlop   from './pages/BopOrFlop';
import './styles/global.css';

function Nav() {
  return (
    <nav className="nav">
      <div className="nav-brand">
        <span className="nav-logo">♪</span>
        <span className="nav-title">Spotilytics</span>
      </div>
      <div className="nav-links">
        <NavLink to="/"            className={({isActive}) => isActive ? 'nav-link active' : 'nav-link'}>Music Trends</NavLink>
        <NavLink to="/genre-battle" className={({isActive}) => isActive ? 'nav-link active' : 'nav-link'}>Genre Battle</NavLink>
        <NavLink to="/mood-map"    className={({isActive}) => isActive ? 'nav-link active' : 'nav-link'}>Mood Map</NavLink>
        <NavLink to="/bop-or-flop" className={({isActive}) => isActive ? 'nav-link active' : 'nav-link'}>BopOrFlop</NavLink>
      </div>
    </nav>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <Nav />
        <main className="main">
          <Routes>
            <Route path="/"             element={<MusicTrends />} />
            <Route path="/genre-battle" element={<GenreBattle />} />
            <Route path="/mood-map"     element={<MoodMap />} />
            <Route path="/bop-or-flop"  element={<BopOrFlop />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}