import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  BarChart, Bar, PieChart, Pie, Cell, ResponsiveContainer, Legend,
} from 'recharts';
import { getVideoStatus } from './api';

const EMOTION_COLORS = {
  happy:    '#68d391',
  neutral:  '#63b3ed',
  sad:      '#9f7aea',
  angry:    '#fc8181',
  fear:     '#f6ad55',
  surprise: '#4fd1c7',
  disgust:  '#f6e05e',
};

const EMOTIONS = Object.keys(EMOTION_COLORS);

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'rgba(15,19,32,0.95)', border: '1px solid rgba(255,255,255,0.1)',
      borderRadius: 10, padding: '12px 16px', fontSize: 12,
    }}>
      <div style={{ color: 'var(--text-muted)', marginBottom: 8 }}>⏱ {label}s</div>
      {payload.map(p => (
        <div key={p.name} style={{ color: EMOTION_COLORS[p.name] || '#fff', marginBottom: 3 }}>
          {p.name.charAt(0).toUpperCase() + p.name.slice(1)}: <strong>{p.value?.toFixed(1)}%</strong>
        </div>
      ))}
    </div>
  );
}

export default function AnalyticsPage() {
  const { id } = useParams();
  const [asset, setAsset] = useState(null);
  const [loading, setLoading] = useState(true);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    let interval;
    if (asset && asset.status === 'PROCESSING') {
      interval = setInterval(() => {
        setElapsed(prev => prev + 1);
      }, 1000);
    } else {
      setElapsed(0);
    }
    return () => clearInterval(interval);
  }, [asset?.status]);

  useEffect(() => {
    let timer;
    const poll = async () => {
      try {
        const res = await getVideoStatus(id);
        setAsset(res.data);
        if (['PENDING', 'PROCESSING'].includes(res.data.status)) {
          timer = setTimeout(poll, 3000);
        } else {
          setLoading(false);
        }
      } catch {
        setLoading(false);
      }
    };
    poll();
    return () => clearTimeout(timer);
  }, [id]);

  if (!asset) return (
    <div className="empty-state" style={{ marginTop: 80 }}>
      <div className="empty-state-icon"><span className="spinner" style={{ width: 40, height: 40, borderWidth: 3 }} /></div>
      <div className="empty-state-title">Loading asset…</div>
    </div>
  );

  const timeline = asset.analytics?.timeline_data ?? [];

  // Build chart data
  const chartData = timeline.map(frame => ({
    ts: frame.timestamp,
    faces: frame.total_faces,
    ...frame.emotions_percentage,
  }));

  // Aggregate totals for pie chart
  const totals = EMOTIONS.reduce((acc, em) => {
    acc[em] = timeline.reduce((s, f) => s + (f.emotions_raw?.[em] || 0), 0);
    return acc;
  }, {});
  const pieData = EMOTIONS
    .map(em => ({ name: em, value: totals[em] }))
    .filter(d => d.value > 0);

  const totalFaces = timeline.reduce((s, f) => s + f.total_faces, 0);
  const avgFaces   = timeline.length ? (totalFaces / timeline.length).toFixed(1) : 0;
  const dominantEmotion = pieData.sort((a, b) => b.value - a.value)[0]?.name ?? '—';
  const peakFaces  = timeline.length ? Math.max(...timeline.map(f => f.total_faces)) : 0;

  const percent = asset?.progress_percent ?? 0;
  let remainingText = '';
  if (asset?.status === 'PROCESSING' && percent > 0) {
    const totalEst = (elapsed / percent) * 100;
    const rem = Math.max(0, Math.ceil(totalEst - elapsed));
    if (rem >= 60) {
      remainingText = ` (~${Math.floor(rem / 60)}m ${rem % 60}s remaining)`;
    } else {
      remainingText = ` (~${rem}s remaining)`;
    }
  }

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ marginBottom: 6 }}>
            <Link to="/videos" style={{ color: 'var(--text-muted)', fontSize: 13, textDecoration: 'none' }}>
              ← Back to Videos
            </Link>
          </div>
          <h1 className="page-title">Crowd Analytics Report</h1>
          <p className="page-subtitle">Video Asset #{id}</p>
        </div>
        <span className={`status-badge status-${asset.status}`}>{asset.status}</span>
      </div>

      {['PENDING', 'PROCESSING'].includes(asset.status) && (
        <div className="card" style={{ textAlign: 'center', padding: '48px 32px', marginBottom: 24 }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', maxWidth: 480, margin: '0 auto' }}>
            <span className="spinner" style={{ width: 40, height: 40, borderWidth: 3 }} />
            
            <div style={{ marginTop: 20, color: 'var(--text-primary)', fontSize: 16, fontWeight: 600 }}>
              {asset.status === 'PENDING' ? 'Queueing ML Pipeline…' : `Processing Video: ${percent}%`}
            </div>
            
            {asset.status === 'PROCESSING' && (
              <>
                <div style={{ width: '100%', height: 8, background: 'rgba(255,255,255,0.06)', borderRadius: 4, marginTop: 16, overflow: 'hidden' }}>
                  <div style={{
                    width: `${percent}%`,
                    height: '100%',
                    background: 'linear-gradient(90deg, #63b3ed, #9f7aea)',
                    borderRadius: 4,
                    transition: 'width 0.4s ease-out'
                  }} />
                </div>
                
                <div style={{ color: 'var(--text-secondary)', fontSize: 13, marginTop: 12 }}>
                  Elapsed: {Math.floor(elapsed / 60)}m {elapsed % 60}s {remainingText}
                </div>
              </>
            )}
            
            <div style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 16 }}>
              RetinaFace + ViT Transformer analysis (1 FPS) · Auto-refreshing every 3s
            </div>
          </div>
        </div>
      )}

      {asset.status === 'FAILED' && (
        <div className="card" style={{ borderColor: 'rgba(252,129,129,0.3)', textAlign: 'center', padding: 40 }}>
          <div style={{ fontSize: 40 }}>⚠️</div>
          <div style={{ color: 'var(--accent-red)', marginTop: 12, fontWeight: 600 }}>Processing Failed</div>
          <div style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 6 }}>
            Check Celery worker logs for details.
          </div>
        </div>
      )}

      {asset.status === 'COMPLETED' && timeline.length > 0 && (
        <>
          {/* Stat cards */}
          <div className="stats-grid">
            {[
              { icon: '🎯', value: timeline.length, label: 'Frames Analysed', gradient: 'linear-gradient(135deg,#63b3ed,#4299e1)' },
              { icon: '👥', value: peakFaces,        label: 'Peak Face Count',  gradient: 'linear-gradient(135deg,#9f7aea,#6b46c1)' },
              { icon: '📈', value: avgFaces,         label: 'Avg Faces / Frame', gradient: 'linear-gradient(135deg,#68d391,#38a169)' },
              { icon: '😊', value: dominantEmotion.toUpperCase(), label: 'Dominant Emotion', gradient: `linear-gradient(135deg,${EMOTION_COLORS[dominantEmotion]},${EMOTION_COLORS[dominantEmotion]}88)` },
            ].map((s, i) => (
              <div key={i} className="stat-card" style={{ '--gradient': s.gradient }}>
                <div className="stat-icon">{s.icon}</div>
                <div className="stat-value" style={{ fontSize: typeof s.value === 'string' ? 18 : 28 }}>{s.value}</div>
                <div className="stat-label">{s.label}</div>
              </div>
            ))}
          </div>

          {/* Time-series area chart */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-header">
              <span className="card-title">Emotion Timeline (% per frame)</span>
            </div>
            <div className="chart-container">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 0, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    {EMOTIONS.map(em => (
                      <linearGradient key={em} id={`grad-${em}`} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%"  stopColor={EMOTION_COLORS[em]} stopOpacity={0.35} />
                        <stop offset="95%" stopColor={EMOTION_COLORS[em]} stopOpacity={0} />
                      </linearGradient>
                    ))}
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="ts" stroke="var(--text-muted)" fontSize={11} tickFormatter={v => `${v}s`} />
                  <YAxis stroke="var(--text-muted)" fontSize={11} tickFormatter={v => `${v}%`} />
                  <Tooltip content={<CustomTooltip />} />
                  {EMOTIONS.map(em => (
                    <Area key={em} type="monotone" dataKey={em}
                      stroke={EMOTION_COLORS[em]} strokeWidth={1.5}
                      fill={`url(#grad-${em})`} dot={false} />
                  ))}
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className="emotion-legend">
              {EMOTIONS.map(em => (
                <div key={em} className="legend-item">
                  <div className="legend-dot" style={{ background: EMOTION_COLORS[em] }} />
                  {em.charAt(0).toUpperCase() + em.slice(1)}
                </div>
              ))}
            </div>
          </div>

          <div className="dashboard-grid responsive-grid-2col" style={{ gridTemplateColumns: 'repeat(2, 1fr)' }}>
            {/* Face count over time */}
            <div className="card">
              <div className="card-header">
                <span className="card-title">Face Count Over Time</span>
              </div>
              <div className="chart-container" style={{ height: 240 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 0, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                    <XAxis dataKey="ts" stroke="var(--text-muted)" fontSize={11} tickFormatter={v => `${v}s`} />
                    <YAxis stroke="var(--text-muted)" fontSize={11} />
                    <Tooltip contentStyle={{ background: 'rgba(15,19,32,0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }} />
                    <Bar dataKey="faces" fill="url(#grad-neutral)" radius={[3, 3, 0, 0]}>
                      {chartData.map((_, i) => <Cell key={i} fill="#63b3ed" />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Aggregate emotion pie */}
            <div className="card">
              <div className="card-header">
                <span className="card-title">Overall Emotion Distribution</span>
              </div>
              <div className="chart-container" style={{ height: 240 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={95}
                      paddingAngle={3} dataKey="value">
                      {pieData.map((entry, i) => (
                        <Cell key={i} fill={EMOTION_COLORS[entry.name]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(v) => [`${v} detections`, '']}
                      contentStyle={{ background: 'rgba(15,19,32,0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }} />
                    <Legend iconType="circle" iconSize={10}
                      formatter={v => v.charAt(0).toUpperCase() + v.slice(1)}
                      wrapperStyle={{ fontSize: 12, color: 'var(--text-secondary)' }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
