import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getVideos } from './api';

export default function VideosPage() {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    getVideos().then(r => { setVideos(r.data); setLoading(false); }).catch(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const statusDot = { PENDING: '🟡', PROCESSING: '🔵', COMPLETED: '🟢', FAILED: '🔴' };

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 className="page-title">Video Assets</h1>
          <p className="page-subtitle">All uploaded videos and their processing status.</p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button className="btn btn-ghost" onClick={load}>↻ Refresh</button>
          <Link to="/upload" className="btn btn-primary">⬆ Upload New</Link>
        </div>
      </div>

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        {loading ? (
          <div className="empty-state"><span className="spinner" /></div>
        ) : videos.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">🎬</div>
            <div className="empty-state-title">No videos yet</div>
            <div className="empty-state-text">Upload your first event video to get started.</div>
            <Link to="/upload" className="btn btn-primary" style={{ marginTop: 20 }}>Upload Now</Link>
          </div>
        ) : (
          <table className="video-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Event</th>
                <th>File</th>
                <th>Uploaded</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {videos.map(v => (
                <tr key={v.id}>
                  <td style={{ color: 'var(--text-muted)' }}>#{v.id}</td>
                  <td>{v.event}</td>
                  <td style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {v.file_path?.split('/').pop() ?? '—'}
                  </td>
                  <td>{new Date(v.uploaded_at).toLocaleString()}</td>
                  <td><span className={`status-badge status-${v.status}`}>{statusDot[v.status]} {v.status}</span></td>
                  <td>
                    <Link to={`/videos/${v.id}`} className="btn btn-ghost" style={{ fontSize: 12, padding: '5px 12px' }}>
                      {v.status === 'COMPLETED' ? '📊 View Analytics' : '👁 View Status'}
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
