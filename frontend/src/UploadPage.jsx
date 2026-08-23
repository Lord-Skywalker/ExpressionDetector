import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import { uploadVideo, getEvents, createEvent } from './api';

export default function UploadPage({ addToast }) {
  const navigate = useNavigate();
  const [file, setFile]         = useState(null);
  const [events, setEvents]     = useState([]);
  const [eventId, setEventId]   = useState('');
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);

  // New event form
  const [showNewEvent, setShowNewEvent] = useState(false);
  const [newEvent, setNewEvent] = useState({ name: '', date: '', location: '' });

  useEffect(() => {
    getEvents().then(r => setEvents(r.data)).catch(() => {});
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: { 'video/*': ['.mp4', '.mov', '.avi', '.mkv'] },
    maxFiles: 1,
    onDrop: accepted => {
      if (accepted.length) setFile(accepted[0]);
    },
  });

  const handleCreateEvent = async () => {
    if (!newEvent.name || !newEvent.date || !newEvent.location) {
      addToast('Fill all event fields.', 'error'); return;
    }
    try {
      const res = await createEvent(newEvent);
      setEvents(prev => [...prev, res.data]);
      setEventId(String(res.data.id));
      setShowNewEvent(false);
      setNewEvent({ name: '', date: '', location: '' });
      addToast(`Event "${res.data.name}" created!`, 'success');
    } catch {
      addToast('Failed to create event.', 'error');
    }
  };

  const handleUpload = async () => {
    if (!file) { addToast('Please select a video file.', 'error'); return; }
    if (!eventId) { addToast('Please select an event.', 'error'); return; }

    setUploading(true);
    setProgress(0);

    const fd = new FormData();
    fd.append('file_path', file);
    fd.append('event', eventId);

    try {
      // Simulated chunked progress
      const interval = setInterval(() => setProgress(p => Math.min(p + 6, 85)), 300);
      const res = await uploadVideo(fd);
      clearInterval(interval);
      setProgress(100);
      addToast('Video uploaded! Processing queued.', 'success');
      setTimeout(() => navigate(`/videos/${res.data.video_asset.id}`), 1000);
    } catch (e) {
      addToast('Upload failed. Is the Django server running?', 'error');
      setUploading(false);
      setProgress(0);
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Upload Event Video</h1>
        <p className="page-subtitle">
          Upload a recorded video. Our ML pipeline will process it asynchronously.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 24 }}>

        {/* Drop zone */}
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div
            {...getRootProps()}
            className={`upload-zone ${isDragActive ? 'drag-over' : ''}`}
            style={{ borderRadius: 'var(--radius)', minHeight: 340 }}
          >
            <input {...getInputProps()} />
            {file ? (
              <div style={{ position: 'relative', zIndex: 1 }}>
                <span className="upload-icon">🎬</span>
                <div className="upload-title">{file.name}</div>
                <div className="upload-subtitle">
                  {(file.size / 1024 / 1024).toFixed(1)} MB &nbsp;·&nbsp;
                  {file.type || 'video'}
                </div>
                <div style={{ marginTop: 16 }}>
                  <span className="status-badge status-PENDING">Ready to Upload</span>
                </div>
              </div>
            ) : (
              <div style={{ position: 'relative', zIndex: 1 }}>
                <span className="upload-icon">📁</span>
                <div className="upload-title">
                  {isDragActive ? 'Drop it here!' : 'Drag & drop your video'}
                </div>
                <div className="upload-subtitle">
                  Or click to browse your files
                </div>
                <div className="upload-hint">Supports .mp4, .mov, .avi, .mkv</div>
              </div>
            )}
          </div>

          {uploading && (
            <div style={{ padding: '0 24px 24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 12, color: 'var(--text-muted)' }}>
                <span>Uploading...</span><span>{progress}%</span>
              </div>
              <div className="progress-bar-wrap">
                <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
              </div>
            </div>
          )}
        </div>

        {/* Settings panel */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Job Settings</span>
          </div>

          <div className="form-group">
            <label className="form-label">Event</label>
            <select
              className="form-select"
              value={eventId}
              onChange={e => setEventId(e.target.value)}
              disabled={uploading}
            >
              <option value="">Select an event…</option>
              {events.map(ev => (
                <option key={ev.id} value={ev.id}>{ev.name}</option>
              ))}
            </select>
            <div style={{ marginTop: 8 }}>
              <button className="btn btn-ghost" style={{ fontSize: 12, padding: '6px 12px' }}
                onClick={() => setShowNewEvent(v => !v)}>
                {showNewEvent ? '− Cancel' : '+ New Event'}
              </button>
            </div>
          </div>

          {showNewEvent && (
            <div style={{ background: 'rgba(255,255,255,0.03)', borderRadius: 8, padding: 16, marginBottom: 20 }}>
              <div className="form-group">
                <label className="form-label">Event Name</label>
                <input className="form-input" placeholder="e.g. Glastonbury 2025"
                  value={newEvent.name} onChange={e => setNewEvent(p => ({ ...p, name: e.target.value }))} />
              </div>
              <div className="form-group">
                <label className="form-label">Date</label>
                <input className="form-input" type="date"
                  value={newEvent.date} onChange={e => setNewEvent(p => ({ ...p, date: e.target.value }))} />
              </div>
              <div className="form-group" style={{ marginBottom: 12 }}>
                <label className="form-label">Location</label>
                <input className="form-input" placeholder="e.g. Somerset, UK"
                  value={newEvent.location} onChange={e => setNewEvent(p => ({ ...p, location: e.target.value }))} />
              </div>
              <button className="btn btn-primary" onClick={handleCreateEvent}>
                ✓ Create Event
              </button>
            </div>
          )}

          <div className="form-group">
            <label className="form-label">Processing Rate</label>
            <select className="form-select" defaultValue="1" disabled>
              <option value="1">1 FPS — Max Accuracy</option>
              <option value="2">2 FPS — Balanced</option>
            </select>
            <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>
              1 FPS extracts 1 frame per second of video for maximum accuracy.
            </p>
          </div>

          <div style={{ marginTop: 24 }}>
            <button
              id="upload-submit-btn"
              className="btn btn-primary"
              style={{ width: '100%', justifyContent: 'center' }}
              onClick={handleUpload}
              disabled={uploading || !file}
            >
              {uploading ? <><span className="spinner" />Processing…</> : '🚀 Upload & Queue Job'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
