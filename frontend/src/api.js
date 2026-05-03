import axios from 'axios';

const API = axios.create({ 
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000' 
});

export const getMusicTrends = () => API.get('/analytics/music-trends').then(r => r.data);
export const getGenreBattle = () => API.get('/analytics/genre-battle').then(r => r.data);
export const getMoodMap     = () => API.get('/analytics/mood-map').then(r => r.data);

export const predictTrack = (features) =>
  API.post('/predict', features).then(r => r.data);