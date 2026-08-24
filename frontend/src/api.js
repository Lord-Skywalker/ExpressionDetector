import axios from 'axios';

// Django API (Render.com in production, localhost:8000 in local dev)
const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
});

// Cloud Run (ML Worker for live detection)
// In production: set VITE_ML_WORKER_URL to your Cloud Run URL.
// In local dev: falls back to Django API (which handles live detection locally).
export const ML_WORKER_URL = import.meta.env.VITE_ML_WORKER_URL || "http://localhost:7860";

// Silently pings the ML worker and Django API to pre-warm the servers
export const wakeUpServers = () => {
  if (import.meta.env.PROD) {
    if (import.meta.env.VITE_ML_WORKER_URL) {
      fetch(`${import.meta.env.VITE_ML_WORKER_URL}/health`).catch(() => {});
    }
    // Ping the Django API to wake up Render instances
    API.get('/events/').catch(() => {});
  }
};

// Checks the health status of the ML worker
export const checkMLWorkerStatus = () => {
  const url = import.meta.env.VITE_ML_WORKER_URL 
    ? `${import.meta.env.VITE_ML_WORKER_URL}/health` 
    : 'http://localhost:7860/health';
  return fetch(url).then(r => r.json());
};

const ML_API = import.meta.env.VITE_ML_WORKER_URL
  ? axios.create({ baseURL: import.meta.env.VITE_ML_WORKER_URL })
  : null;

// ── Video processing & analytics (always via Django API) ─────────────────────
export const getEvents    = ()         => API.get('/events/');
export const createEvent  = (data)     => API.post('/events/', data);
export const getVideos    = (eventId)  => API.get('/videos/', { params: eventId ? { event: eventId } : {} });
export const uploadVideo  = (formData) => API.post('/videos/upload/', formData, {
  headers: { 'Content-Type': 'multipart/form-data' },
});
export const uploadVideoChunk = (formData) => API.post('/videos/chunk-upload/', formData, {
  headers: { 'Content-Type': 'multipart/form-data' },
});
export const getVideoStatus  = (id) => API.get(`/videos/${id}/status/`);
export const getAnalytics    = (id) => API.get(`/analytics/${id}/`);

// ── Live detection (Cloud Run in production, Django locally) ──────────────────
export const detectLiveEmotion = (data) =>
  ML_API
    ? ML_API.post('/live/detect', data)       // Production: calls Cloud Run directly
    : API.post('/live/detect/', data);         // Local dev: calls Django

export const classifyLiveEmotion = (data) =>
  ML_API
    ? ML_API.post('/live/classify', data)     // Production: calls Cloud Run directly
    : API.post('/live/classify/', data);       // Local dev: calls Django
