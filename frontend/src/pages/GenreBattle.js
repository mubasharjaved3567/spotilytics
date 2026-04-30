import React, { useEffect, useState } from 'react';
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  ResponsiveContainer, Tooltip, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Cell,
} from 'recharts';
import { getGenreBattle } from '../api';

const COLORS = ['#1db954','#4fc3f7','#ffb400','#ce93d8','#ff6b6b','#80cbc4','#ffcc02','#f48fb1'];

const TOOLTIP_STYLE = {
  backgroundColor: '#1a1a1a',
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: 8,
  color: '#f0f0f0',
  fontSize: 13,
};

export default function GenreBattle() {
  const [data,    setData]    = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    getGenreBattle()
      .then(d => { setData(d); setSelected(d[0]?.genre_group || null); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, []);

  if (loading) return <div className="loading"><div className="spinner" />Loading genre data...</div>;
  if (error)   return <div className="error">❌ {error} — make sure the API is running on localhost:8000</div>;

  const selectedData = data.find(d => d.genre_group === selected);

  const radarData = selectedData ? [
    { metric: 'Popularity',   value: (selectedData.avg_popularity   / 100).toFixed(3) },
    { metric: 'Danceability', value: selectedData.avg_danceability.toFixed(3) },
    { metric: 'Energy',       value: selectedData.avg_energy.toFixed(3) },
    { metric: 'Valence',      value: selectedData.avg_valence.toFixed(3) },
  ] : [];

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Genre <span>Battle</span></h1>
        <p className="page-sub">Energy, danceability, and popularity across 8 genre groups</p>
      </div>

      <div className="chart-card">
        <div className="chart-title">Avg popularity by genre</div>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={data} margin={{ top: 4, right: 12, bottom: 20, left: -10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="genre_group" tick={{ fill: '#888', fontSize: 12 }} />
            <YAxis domain={[0, 100]} tick={{ fill: '#888', fontSize: 12 }} />
            <Tooltip contentStyle={TOOLTIP_STYLE} formatter={v => v.toFixed(1)} />
            <Bar dataKey="avg_popularity" radius={[6, 6, 0, 0]} name="Avg popularity">
              {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <div className="chart-card">
          <div className="chart-title">Select genre — radar view</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 16 }}>
            {data.map((d, i) => (
              <button
                key={d.genre_group}
                onClick={() => setSelected(d.genre_group)}
                style={{
                  padding: '4px 12px',
                  borderRadius: 20,
                  border: `1px solid ${selected === d.genre_group ? COLORS[i % COLORS.length] : 'rgba(255,255,255,0.08)'}`,
                  background: selected === d.genre_group ? `${COLORS[i % COLORS.length]}22` : 'transparent',
                  color: selected === d.genre_group ? COLORS[i % COLORS.length] : '#888',
                  fontSize: 12,
                  cursor: 'pointer',
                  fontFamily: 'DM Sans, sans-serif',
                  transition: '0.2s',
                }}
              >
                {d.genre_group}
              </button>
            ))}
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="rgba(255,255,255,0.08)" />
              <PolarAngleAxis dataKey="metric" tick={{ fill: '#888', fontSize: 12 }} />
              <Radar dataKey="value" stroke="#1db954" fill="#1db954" fillOpacity={0.25} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <div className="chart-title">Stats — {selected}</div>
          {selectedData && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginTop: 8 }}>
              {[
                { label: 'Avg popularity',   val: selectedData.avg_popularity.toFixed(1),   max: 100,  raw: selectedData.avg_popularity / 100 },
                { label: 'Avg danceability', val: selectedData.avg_danceability.toFixed(3),  max: 1,    raw: selectedData.avg_danceability },
                { label: 'Avg energy',       val: selectedData.avg_energy.toFixed(3),        max: 1,    raw: selectedData.avg_energy },
                { label: 'Avg valence',      val: selectedData.avg_valence.toFixed(3),       max: 1,    raw: selectedData.avg_valence },
                { label: 'Track count',      val: selectedData.track_count.toLocaleString(), max: null, raw: null },
              ].map(row => (
                <div key={row.label}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
                    <span style={{ color: '#888' }}>{row.label}</span>
                    <span style={{ color: '#1db954', fontWeight: 500 }}>{row.val}</span>
                  </div>
                  {row.raw !== null && (
                    <div style={{ height: 4, background: 'rgba(255,255,255,0.06)', borderRadius: 2, overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${row.raw * 100}%`, background: '#1db954', borderRadius: 2, transition: '0.4s' }} />
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}