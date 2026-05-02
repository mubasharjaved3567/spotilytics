import React, { useState, useCallback } from 'react';
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  ResponsiveContainer, Tooltip,
} from 'recharts';
import axios from 'axios';

const API = axios.create({ baseURL: 'http://localhost:8000' });

const TOOLTIP_STYLE = {
  backgroundColor: '#1a1a1a',
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: 8,
  color: '#f0f0f0',
  fontSize: 13,
};

const COLORS = ['#1db954', '#4fc3f7', '#ffb400', '#ce93d8', '#ff6b6b'];

function AudioBar({ label, value, max = 1, color = '#1db954' }) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
        <span style={{ color: '#888' }}>{label}</span>
        <span style={{ color, fontWeight: 500 }}>{value}</span>
      </div>
      <div style={{ height: 5, background: 'rgba(255,255,255,0.06)', borderRadius: 3, overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: 3, transition: '0.6s ease' }} />
      </div>
    </div>
  );
}

export default function ArtistExplorer() {
  const [query,    setQuery]    = useState('');
  const [results,  setResults]  = useState([]);
  const [selected, setSelected] = useState(null);
  const [insight,  setInsight]  = useState(null);
  const [searching, setSearching] = useState(false);
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState(null);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setSearching(true);
    setError(null);
    setSelected(null);
    setInsight(null);
    try {
      const res = await API.get(`/artist/search?q=${encodeURIComponent(query)}`);
      setResults(res.data);
      if (res.data.length === 0) setError('No artists found. Try a different name.');
    } catch (e) {
      setError(e.message);
    } finally {
      setSearching(false);
    }
  };

  const handleSelect = async (artist) => {
    setSelected(artist);
    setInsight(null);
    setLoading(true);
    setError(null);
    try {
      const res = await API.get(`/artist/insight?name=${encodeURIComponent(artist.artist_name)}`);
      setInsight(res.data);
    } catch (e) {
      setError('Could not load artist insights: ' + e.message);
    } finally {
      setLoading(false);
    }
  };

  const radarData = insight ? [
    { metric: 'Danceability', value: Number(insight.avg_danceability) },
    { metric: 'Energy',       value: Number(insight.avg_energy) },
    { metric: 'Valence',      value: Number(insight.avg_valence) },
    { metric: 'Acousticness', value: Number(insight.avg_acousticness) },
    { metric: 'Speechiness',  value: Number(insight.avg_speechiness || 0) },
  ] : [];

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <h1 className="page-title">Artist <span>Explorer</span></h1>
        <p className="page-sub">
          Search any artist — real Spotify data + AI-powered insights
        </p>
      </div>

      {/* Search bar */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', gap: 10 }}>
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
            placeholder="Search artist name... (e.g. Drake, Adele, BTS)"
            style={{
              flex: 1,
              padding: '12px 16px',
              background: 'var(--bg3)',
              border: '1px solid var(--border)',
              borderRadius: 10,
              color: 'var(--text)',
              fontSize: 14,
              fontFamily: 'DM Sans, sans-serif',
              outline: 'none',
            }}
          />
          <button
            onClick={handleSearch}
            disabled={searching}
            style={{
              padding: '12px 24px',
              background: 'var(--green)',
              color: '#000',
              border: 'none',
              borderRadius: 10,
              fontFamily: 'Syne, sans-serif',
              fontWeight: 700,
              fontSize: 14,
              cursor: searching ? 'not-allowed' : 'pointer',
              opacity: searching ? 0.7 : 1,
              transition: '0.2s',
            }}
          >
            {searching ? 'Searching...' : '🔍 Search'}
          </button>
        </div>

        {/* Search results */}
        {results.length > 0 && !selected && (
          <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 6 }}>
            {results.map((a, i) => (
              <div
                key={a.artist_name}
                onClick={() => handleSelect(a)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 14px',
                  background: 'var(--bg3)',
                  borderRadius: 8,
                  cursor: 'pointer',
                  border: '1px solid transparent',
                  transition: '0.2s',
                }}
                onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--green)'}
                onMouseLeave={e => e.currentTarget.style.borderColor = 'transparent'}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{
                    width: 36, height: 36, borderRadius: '50%',
                    background: `${COLORS[i % COLORS.length]}22`,
                    border: `2px solid ${COLORS[i % COLORS.length]}`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 14, fontWeight: 700, color: COLORS[i % COLORS.length],
                    fontFamily: 'Syne, sans-serif',
                  }}>
                    {a.artist_name[0].toUpperCase()}
                  </div>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 14 }}>{a.artist_name}</div>
                    <div style={{ fontSize: 12, color: '#888' }}>{a.genre_group} · {a.track_count} tracks</div>
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ color: 'var(--green)', fontFamily: 'Syne, sans-serif', fontWeight: 700 }}>
                    {a.avg_popularity}
                  </div>
                  <div style={{ fontSize: 11, color: '#888' }}>avg popularity</div>
                </div>
              </div>
            ))}
          </div>
        )}

        {error && <div className="error" style={{ marginTop: 12 }}>❌ {error}</div>}
      </div>

      {/* Loading */}
      {loading && (
        <div className="loading">
          <div className="spinner" />
          Generating AI insights for {selected?.artist_name}...
        </div>
      )}

      {/* Artist insight card */}
      {insight && !loading && (
        <div style={{ animation: 'fadeUp 0.4s ease' }}>

          {/* Top section — identity */}
          <div className="card" style={{
            marginBottom: '1.5rem',
            borderLeft: '4px solid var(--green)',
            position: 'relative',
            overflow: 'hidden',
          }}>
            <div style={{
              position: 'absolute', top: 0, right: 0,
              width: 120, height: 120,
              background: 'radial-gradient(circle, rgba(29,185,84,0.08) 0%, transparent 70%)',
              borderRadius: '50%',
            }} />

            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 20, marginBottom: 16 }}>
              {/* Avatar */}
              <div style={{
                width: 72, height: 72, borderRadius: '50%', flexShrink: 0,
                background: 'rgba(29,185,84,0.12)',
                border: '2px solid var(--green)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 28, fontWeight: 800, color: 'var(--green)',
                fontFamily: 'Syne, sans-serif',
              }}>
                {insight.artist_name[0].toUpperCase()}
              </div>

              <div style={{ flex: 1 }}>
                <div style={{
                  fontFamily: 'Syne, sans-serif', fontSize: '1.8rem',
                  fontWeight: 800, letterSpacing: '-1px', marginBottom: 4,
                }}>
                  {insight.artist_name}
                </div>
                <div style={{ fontSize: 13, color: '#888', marginBottom: 8 }}>
                  🌍 {insight.origin_country} &nbsp;·&nbsp;
                  🎵 {insight.genre_group} &nbsp;·&nbsp;
                  📅 Active {insight.first_year}–{insight.last_year}
                </div>
                <div style={{
                  display: 'inline-block',
                  padding: '4px 12px',
                  background: 'rgba(29,185,84,0.1)',
                  border: '1px solid rgba(29,185,84,0.3)',
                  borderRadius: 20,
                  color: 'var(--green)',
                  fontSize: 12,
                  fontWeight: 500,
                }}>
                  🎸 {insight.signature_sound}
                </div>
              </div>
            </div>

            {/* Stats row */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
              {[
                { label: 'Avg Popularity', value: `${insight.avg_popularity}/100` },
                { label: 'Peak Popularity', value: `${insight.peak_popularity}/100` },
                { label: 'Total Tracks', value: insight.track_count },
                { label: 'Career Start', value: insight.career_start },
              ].map(s => (
                <div key={s.label} style={{
                  background: 'var(--bg3)', borderRadius: 8, padding: '10px 12px', textAlign: 'center',
                }}>
                  <div style={{ fontSize: 11, color: '#888', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 4 }}>
                    {s.label}
                  </div>
                  <div style={{ fontFamily: 'Syne, sans-serif', fontSize: '1.1rem', fontWeight: 700, color: 'var(--green)' }}>
                    {s.value}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Middle section — audio DNA + radar */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: '1.5rem' }}>

            {/* Audio fingerprint */}
            <div className="card">
              <div className="card-title" style={{
                fontFamily: 'Syne, sans-serif', fontSize: 12, fontWeight: 700,
                textTransform: 'uppercase', letterSpacing: 1, color: '#888', marginBottom: '1rem',
              }}>
                🎛️ Audio Fingerprint
              </div>
              <AudioBar label="Danceability" value={insight.avg_danceability} color="#1db954" />
              <AudioBar label="Energy"       value={insight.avg_energy}       color="#4fc3f7" />
              <AudioBar label="Valence"      value={insight.avg_valence}       color="#ffb400" />
              <AudioBar label="Acousticness" value={insight.avg_acousticness}  color="#ce93d8" />
              <AudioBar label="Tempo"        value={insight.avg_tempo} max={220} color="#ff6b6b" />
            </div>

            {/* Radar */}
            <div className="card">
              <div className="card-title" style={{
                fontFamily: 'Syne, sans-serif', fontSize: 12, fontWeight: 700,
                textTransform: 'uppercase', letterSpacing: 1, color: '#888', marginBottom: '1rem',
              }}>
                🕸️ Audio Radar
              </div>
              <ResponsiveContainer width="100%" height={200}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="rgba(255,255,255,0.08)" />
                  <PolarAngleAxis dataKey="metric" tick={{ fill: '#888', fontSize: 11 }} />
                  <Radar dataKey="value" stroke="#1db954" fill="#1db954" fillOpacity={0.25} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} formatter={v => Number(v).toFixed(3)} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* AI Insights */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: '1.5rem' }}>

            <div className="card">
              <div style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, color: '#888', marginBottom: 10 }}>
                🤖 AI Style Analysis
              </div>
              <p style={{ fontSize: 13, color: 'var(--text)', lineHeight: 1.7, marginBottom: 12 }}>
                {insight.style_description}
              </p>
              <p style={{ fontSize: 13, color: '#aaa', lineHeight: 1.7 }}>
                {insight.audio_analysis}
              </p>
            </div>

            <div className="card">
              <div style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, color: '#888', marginBottom: 10 }}>
                📈 Career Insight
              </div>
              <p style={{ fontSize: 13, color: 'var(--text)', lineHeight: 1.7, marginBottom: 16 }}>
                {insight.career_insight}
              </p>
              <div style={{
                padding: '10px 14px',
                background: 'rgba(255,180,0,0.08)',
                border: '1px solid rgba(255,180,0,0.2)',
                borderRadius: 8,
                fontSize: 13, color: '#ffb400',
              }}>
                💡 {insight.fun_fact}
              </div>
            </div>
          </div>

          {/* Top tracks + similar artists */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>

            {/* Top tracks */}
            <div className="card">
              <div style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, color: '#888', marginBottom: 10 }}>
                🏆 Top Tracks
              </div>
              {insight.top_tracks.map((t, i) => (
                <div key={t.track_name} style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  padding: '8px 0',
                  borderBottom: i < insight.top_tracks.length - 1 ? '1px solid var(--border)' : 'none',
                }}>
                  <div style={{
                    width: 24, height: 24, borderRadius: '50%',
                    background: `${COLORS[i % COLORS.length]}22`,
                    color: COLORS[i % COLORS.length],
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 11, fontWeight: 700, flexShrink: 0,
                  }}>
                    {i + 1}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: 500 }}>{t.track_name}</div>
                    <div style={{ fontSize: 11, color: '#888' }}>{t.year}</div>
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--green)', fontWeight: 600 }}>
                    {t.popularity}
                  </div>
                </div>
              ))}
            </div>

            {/* Similar artists */}
            <div className="card">
              <div style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, color: '#888', marginBottom: 10 }}>
                🎯 Similar Artists (AI suggested)
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {insight.similar_artists.map((a, i) => (
                  <div
                    key={a}
                    onClick={() => { setQuery(a); setResults([]); setSelected(null); setInsight(null); }}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 10,
                      padding: '8px 12px',
                      background: 'var(--bg3)',
                      borderRadius: 8,
                      cursor: 'pointer',
                      border: '1px solid transparent',
                      transition: '0.2s',
                    }}
                    onMouseEnter={e => e.currentTarget.style.borderColor = COLORS[i % COLORS.length]}
                    onMouseLeave={e => e.currentTarget.style.borderColor = 'transparent'}
                  >
                    <div style={{
                      width: 28, height: 28, borderRadius: '50%',
                      background: `${COLORS[i % COLORS.length]}22`,
                      color: COLORS[i % COLORS.length],
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 12, fontWeight: 700, flexShrink: 0,
                    }}>
                      {a[0].toUpperCase()}
                    </div>
                    <span style={{ fontSize: 13, flex: 1 }}>{a}</span>
                    <span style={{ fontSize: 11, color: '#888' }}>→ explore</span>
                  </div>
                ))}
              </div>
              <button
                onClick={() => { setSelected(null); setInsight(null); setResults([]); setQuery(''); }}
                style={{
                  marginTop: 16, width: '100%',
                  padding: '10px',
                  background: 'transparent',
                  border: '1px solid var(--border)',
                  borderRadius: 8,
                  color: '#888',
                  cursor: 'pointer',
                  fontSize: 13,
                  fontFamily: 'DM Sans, sans-serif',
                  transition: '0.2s',
                }}
              >
                ← Search another artist
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(12px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        .card-title { 
          font-family: Syne, sans-serif; font-size: 12px; font-weight: 700;
          text-transform: uppercase; letter-spacing: 1px; color: #888; margin-bottom: 1rem;
        }
      `}</style>
    </div>
  );
}