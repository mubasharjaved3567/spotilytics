import React, { useEffect, useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import { getMusicTrends } from '../api';

const LINES = [
  { key: 'avg_energy',       color: '#1db954', label: 'Energy' },
  { key: 'avg_danceability', color: '#4fc3f7', label: 'Danceability' },
  { key: 'avg_valence',      color: '#ffb400', label: 'Valence' },
  { key: 'avg_acousticness', color: '#ce93d8', label: 'Acousticness' },
];

const TOOLTIP_STYLE = {
  backgroundColor: '#1a1a1a',
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: 8,
  color: '#f0f0f0',
  fontSize: 13,
};

export default function MusicTrends() {
  const [data,    setData]    = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);
  const [active,  setActive]  = useState('avg_energy');

  useEffect(() => {
    getMusicTrends()
      .then(d => { setData(d); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, []);

  if (loading) return <div className="loading"><div className="spinner" />Loading music trends...</div>;
  if (error)   return <div className="error">❌ {error} — make sure the API is running on localhost:8000</div>;

  const latest   = data[data.length - 1] || {};
  const earliest = data[0] || {};

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Music <span>Trends</span></h1>
        <p className="page-sub">How audio features evolved across 23 years of Spotify data</p>
      </div>

      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-label">Years covered</div>
          <div className="stat-value">{data.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Latest year</div>
          <div className="stat-value">{latest.year || '—'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Avg popularity {latest.year}</div>
          <div className="stat-value">{latest.avg_popularity ? latest.avg_popularity.toFixed(1) : '—'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Total tracks</div>
          <div className="stat-value">
            {data.reduce((s, r) => s + (r.track_count || 0), 0).toLocaleString()}
          </div>
        </div>
      </div>

      <div className="chart-card">
        <div className="chart-title">Audio features over time</div>
        <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
          {LINES.map(l => (
            <button
              key={l.key}
              onClick={() => setActive(l.key)}
              style={{
                padding: '4px 12px',
                borderRadius: 20,
                border: `1px solid ${active === l.key ? l.color : 'rgba(255,255,255,0.08)'}`,
                background: active === l.key ? `${l.color}22` : 'transparent',
                color: active === l.key ? l.color : '#888',
                fontSize: 12,
                cursor: 'pointer',
                fontFamily: 'DM Sans, sans-serif',
                transition: '0.2s',
              }}
            >
              {l.label}
            </button>
          ))}
        </div>
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={data} margin={{ top: 4, right: 12, bottom: 0, left: -10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="year" tick={{ fill: '#888', fontSize: 12 }} />
            <YAxis domain={[0, 1]} tick={{ fill: '#888', fontSize: 12 }} />
            <Tooltip contentStyle={TOOLTIP_STYLE} formatter={v => v.toFixed(3)} />
            {LINES.map(l => (
              <Line
                key={l.key}
                type="monotone"
                dataKey={l.key}
                stroke={l.color}
                strokeWidth={active === l.key ? 2.5 : 1}
                dot={false}
                opacity={active === l.key ? 1 : 0.25}
                name={l.label}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="chart-card">
        <div className="chart-title">Track count per year</div>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data} margin={{ top: 4, right: 12, bottom: 0, left: -10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="year" tick={{ fill: '#888', fontSize: 12 }} />
            <YAxis tick={{ fill: '#888', fontSize: 12 }} />
            <Tooltip contentStyle={TOOLTIP_STYLE} formatter={v => v.toLocaleString()} />
            <Line type="monotone" dataKey="track_count" stroke="#1db954" strokeWidth={2} dot={false} name="Tracks" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}