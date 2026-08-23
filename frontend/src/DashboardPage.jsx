import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getVideos, getEvents } from './api';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from 'recharts';

export default function DashboardPage() {
  const [videos, setVideos]   = useState([]);
  const [events, setEvents]   = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getVideos(), getEvents()])
      .then(([vRes, eRes]) => { setVideos(vRes.data); setEvents(eRes.data); })
      .finally(() => setLoading(false));
  }, []);

  const completed   = videos.filter(v => v.status === 'COMPLETED').length;
  const processing  = videos.filter(v => v.status === 'PROCESSING').length;
  const pending     = videos.filter(v => v.status === 'PENDING').length;
  const failed      = videos.filter(v => v.status === 'FAILED').length;

  // Mock throughput data for visual richness (real data would aggregate analytics)
  const throughputData = Array.from({ length: 12 }, (_, i) => ({
    hour: `${i * 2}h`,
    videos: Math.floor(Math.random() * 8 + 1),
    faces: Math.floor(Math.random() * 2000 + 500),
  }));

  const stats = [
    { icon: '🎤', value: events.length,  label: 'Events',         gradient: 'linear-gradient(135deg,#9f7aea,#6b46c1)' },
    { icon: '🎬', value: videos.length,  label: 'Total Videos',   gradient: 'linear-gradient(135deg,#63b3ed,#4299e1)' },
    { icon: '✅', value: completed,       label: 'Completed',      gradient: 'linear-gradient(135deg,#68d391,#38a169)' },
    { icon: '⚙️', value: processing + pending, label: 'In Queue', gradient: 'linear-gradient(135deg,#f6ad55,#dd6b20)' },
  ];

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Analytics Dashboard</h1>
        <p className="page-subtitle">
          Real-time overview of your crowd emotion processing pipeline.
        </p>
      </div>

      {/* Stats */}
      <div className="stats-grid">
        {stats.map((s, i) => (
          <div key={i} className="stat-card" style={{ '--gradient': s.gradient }}>
            <div className="stat-icon">{s.icon}</div>
            <div className="stat-value">{loading ? '—' : s.value}</div>
            <div className="stat-label">{s.label}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: 20, marginBottom: 20 }}>

        {/* Activity chart */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Pipeline Activity (24h)</span>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Simulated Demo Data</span>
          </div>
          <div className="chart-container" style={{ height: 200 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={throughputData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="gv" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#9f7aea" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#9f7aea" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="hour" stroke="var(--text-muted)" fontSize={11} />
                <YAxis stroke="var(--text-muted)" fontSize={11} />
                <Tooltip contentStyle={{ background: 'rgba(15,19,32,0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 12 }} />
                <Area type="monotone" dataKey="videos" stroke="#9f7aea" strokeWidth={2} fill="url(#gv)" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Quick actions */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Quick Actions</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <Link to="/upload" id="dash-upload-btn" className="btn btn-primary" style={{ justifyContent: 'center' }}>
              ⬆️ Upload New Video
            </Link>
            <Link to="/videos" className="btn btn-ghost" style={{ justifyContent: 'center' }}>
              🎬 Browse All Videos
            </Link>
            <Link to="/events" className="btn btn-ghost" style={{ justifyContent: 'center' }}>
              🎤 Manage Events
            </Link>
          </div>

          <div style={{ marginTop: 24, borderTop: '1px solid var(--border)', paddingTop: 20 }}>
            <div className="card-title" style={{ marginBottom: 14 }}>Status Overview</div>
            {[
              { label: 'Completed', count: completed, color: 'var(--accent-green)' },
              { label: 'Processing', count: processing, color: 'var(--accent-blue)' },
              { label: 'Pending',   count: pending,    color: 'var(--accent-yellow)' },
              { label: 'Failed',    count: failed,     color: 'var(--accent-red)' },
            ].map(s => (
              <div key={s.label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{s.label}</span>
                <span style={{ fontSize: 13, fontWeight: 600, color: s.color }}>{loading ? '—' : s.count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent videos */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '20px 24px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)' }}>
          <span className="card-title">Recent Videos</span>
          <Link to="/videos" style={{ fontSize: 12, color: 'var(--accent-blue)', textDecoration: 'none' }}>View all →</Link>
        </div>
        {loading ? (
          <div className="empty-state" style={{ padding: 40 }}><span className="spinner" /></div>
        ) : videos.length === 0 ? (
          <div className="empty-state" style={{ padding: 40 }}>
            <div className="empty-state-icon">🎬</div>
            <div className="empty-state-title">No videos uploaded yet</div>
            <Link to="/upload" className="btn btn-primary" style={{ marginTop: 16 }}>Upload Now</Link>
          </div>
        ) : (
          <table className="video-table">
            <thead>
              <tr>
                <th>ID</th><th>Event</th><th>Uploaded</th><th>Status</th><th></th>
              </tr>
            </thead>
            <tbody>
              {videos.slice(0, 5).map(v => (
                <tr key={v.id}>
                  <td style={{ color: 'var(--text-muted)' }}>#{v.id}</td>
                  <td>{v.event}</td>
                  <td>{new Date(v.uploaded_at).toLocaleString()}</td>
                  <td><span className={`status-badge status-${v.status}`}>{v.status}</span></td>
                  <td>
                    <Link to={`/videos/${v.id}`} style={{ fontSize: 12, color: 'var(--accent-blue)', textDecoration: 'none' }}>
                      {v.status === 'COMPLETED' ? 'View Analytics →' : 'Track →'}
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
