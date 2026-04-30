import React, { useEffect, useState } from 'react';
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, LabelList,
} from 'recharts';
import { getMoodMap } from '../api';

const COLORS = ['#1db954','#4fc3f7','#ffb400','#ce93d8','#ff6b6b','#80cbc4','#ffcc02','#f48fb1'];

const TOOLTIP_STYLE = {
  backgroundColor: '#1a1a1a',
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: 8,
  color: '#f0f0f0',
  fontSize: 13,
};

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div style={{ ...TOOLTIP_STYLE, padding: '10px 14px' }}>
      <p style={{ fontWeight: 600, marginBottom: 4 }}>{d.genre_group}</p>
      <p style={{ color: '#888', fontSize: 12 }}>Energy: <span style={{ color: '#f0f0f0' }}>{Number(d.avg_energy).toFixed(3)}</span></p>
      <p style={{ color: '#888', fontSize: 12 }}>Valence: <span style={{ color: '#f0f0f0' }}>{Number(d.avg_valence).toFixed(3)}</span></p>
      <p style={{ color: '#888', fontSize: 12 }}>Tracks: <span style={{ color: '#1db954' }}>{Number(d.track_count).toLocaleString()}</span></p>
    </div>
  );
};

export default function MoodMap() {
  const [data,    setData]    = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);

  useEffect(() => {
    getMoodMap()
      .then(d => { setData(d); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, []);

  if (loading) return <div className="loading"><div className="spinner" />Loading mood map...</div>;
  if (error)   return <div className="error">❌ {error} — make sure the API is running on localhost:8000</div>;

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Mood <span>Map</span></h1>
        <p className="page-sub">Energy vs valence — where each genre lives emotionally</p>
      </div>

      <div className="chart-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
          <div className="chart-title">Energy × Valence scatter</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 16px', fontSize: 11, color: '#888' }}>
            <span>← Low energy</span><span style={{ textAlign: 'right' }}>High energy →</span>
            <span>↓ Negative mood</span><span style={{ textAlign: 'right' }}>Positive mood ↑</span>
          </div>
        </div>

        <ResponsiveContainer width="100%" height={380}>
          <ScatterChart margin={{ top: 20, right: 30, bottom: 20, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis
              dataKey="avg_energy"
              type="number"
              domain={[0, 1]}
              name="Energy"
              tick={{ fill: '#888', fontSize: 12 }}
              label={{ value: 'Energy →', position: 'insideBottom', offset: -8, fill: '#555', fontSize: 12 }}
            />
            <YAxis
              dataKey="avg_valence"
              type="number"
              domain={[0, 1]}
              name="Valence"
              tick={{ fill: '#888', fontSize: 12 }}
              label={{ value: 'Valence →', angle: -90, position: 'insideLeft', fill: '#555', fontSize: 12 }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Scatter data={data} shape="circle">
              {data.map((entry, i) => (
                <Cell key={entry.genre_group} fill={COLORS[i % COLORS.length]} />
              ))}
              <LabelList
                dataKey="genre_group"
                position="top"
                style={{ fill: '#aaa', fontSize: 11 }}
              />
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
        {data.map((d, i) => (
          <div key={d.genre_group} className="card" style={{ borderLeft: `3px solid ${COLORS[i % COLORS.length]}` }}>
            <div style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: 15, marginBottom: 8 }}>
              {d.genre_group}
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: '#888', marginBottom: 4 }}>
              <span>Energy</span>
              <span style={{ color: COLORS[i % COLORS.length] }}>{Number(d.avg_energy).toFixed(3)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: '#888', marginBottom: 4 }}>
              <span>Valence</span>
              <span style={{ color: COLORS[i % COLORS.length] }}>{Number(d.avg_valence).toFixed(3)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: '#888' }}>
              <span>Tracks</span>
              <span style={{ color: '#f0f0f0' }}>{Number(d.track_count).toLocaleString()}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}