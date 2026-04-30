import React, { useState } from 'react';
import { predictTrack } from '../api';

const GENRES = ['Pop','Rock','Hip-Hop','Acoustic','Electronic','Metal','Gospel','Other'];

const SLIDERS = [
  { key: 'danceability',     label: 'Danceability',     min: 0,       max: 1,       step: 0.01, default: 0.5  },
  { key: 'energy',           label: 'Energy',           min: 0,       max: 1,       step: 0.01, default: 0.5  },
  { key: 'valence',          label: 'Valence (mood)',   min: 0,       max: 1,       step: 0.01, default: 0.5  },
  { key: 'acousticness',     label: 'Acousticness',     min: 0,       max: 1,       step: 0.01, default: 0.3  },
  { key: 'speechiness',      label: 'Speechiness',      min: 0,       max: 1,       step: 0.01, default: 0.05 },
  { key: 'instrumentalness', label: 'Instrumentalness', min: 0,       max: 1,       step: 0.01, default: 0.0  },
  { key: 'liveness',         label: 'Liveness',         min: 0,       max: 1,       step: 0.01, default: 0.1  },
  { key: 'loudness',         label: 'Loudness (dB)',    min: -60,     max: 0,       step: 0.5,  default: -8.0 },
  { key: 'tempo',            label: 'Tempo (BPM)',      min: 40,      max: 220,     step: 1,    default: 120  },
  { key: 'duration_ms',      label: 'Duration (ms)',    min: 30000,   max: 600000,  step: 1000, default: 200000 },
  { key: 'year',             label: 'Year',             min: 2000,    max: 2023,    step: 1,    default: 2023 },
];

const initialValues = () =>
  Object.fromEntries(SLIDERS.map(s => [s.key, s.default]));

export default function BopOrFlop() {
  const [values,  setValues]  = useState(initialValues());
  const [genre,   setGenre]   = useState('Pop');
  const [result,  setResult]  = useState(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(null);

  const handleSlider = (key, val) =>
    setValues(prev => ({ ...prev, [key]: parseFloat(val) }));

  const handlePredict = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await predictTrack({ ...values, genre_group: genre });
      setResult(res);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setValues(initialValues());
    setGenre('Pop');
    setResult(null);
    setError(null);
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Bop <span>Or Flop?</span></h1>
        <p className="page-sub">Tune the audio features and predict whether your track will be a hit</p>
      </div>

      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div style={{ marginBottom: '1.2rem' }}>
          <label style={{ display: 'block', fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.5px', color: '#888', marginBottom: 6 }}>
            Genre
          </label>
          <select
            className="genre-select"
            value={genre}
            onChange={e => setGenre(e.target.value)}
          >
            {GENRES.map(g => <option key={g} value={g}>{g}</option>)}
          </select>
        </div>

        <div className="slider-grid">
          {SLIDERS.map(s => (
            <div className="slider-row" key={s.key}>
              <div className="slider-label">
                <span>{s.label}</span>
                <span className="slider-val">
                  {s.key === 'duration_ms'
                    ? `${Math.round(values[s.key] / 1000)}s`
                    : values[s.key]}
                </span>
              </div>
              <input
                type="range"
                min={s.min}
                max={s.max}
                step={s.step}
                value={values[s.key]}
                onChange={e => handleSlider(s.key, e.target.value)}
              />
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', gap: 10 }}>
          <button
            className="predict-btn"
            onClick={handlePredict}
            disabled={loading}
            style={{ flex: 1 }}
          >
            {loading ? 'Predicting...' : '🎵 Predict'}
          </button>
          <button
            onClick={handleReset}
            style={{
              padding: '14px 20px',
              background: 'transparent',
              border: '1px solid rgba(255,255,255,0.12)',
              borderRadius: 12,
              color: '#888',
              cursor: 'pointer',
              fontSize: 13,
              fontFamily: 'DM Sans, sans-serif',
              transition: '0.2s',
            }}
          >
            Reset
          </button>
        </div>

        {error && (
          <div className="error" style={{ marginTop: '1rem' }}>
            ❌ {error}
          </div>
        )}
      </div>

      {result && (
        <div className={`result-card ${result.popularity_tier}`}>
          <div className="result-tier">{result.popularity_tier}</div>
          <div className="result-message">{result.message}</div>
          <div className="result-confidence">Confidence: {result.confidence}%</div>

          <div className="prob-bars">
            {['High', 'Mid', 'Low'].map(tier => (
              <div className="prob-bar-wrap" key={tier}>
                <div className="prob-bar-label">{tier}</div>
                <div className="prob-bar-track">
                  <div
                    className={`prob-bar-fill ${tier}`}
                    style={{ width: `${result.probabilities[tier]}%` }}
                  />
                </div>
                <div className="prob-bar-pct">{result.probabilities[tier]}%</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}