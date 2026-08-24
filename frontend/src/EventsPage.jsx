import { useState, useEffect } from 'react';
import { getEvents, createEvent } from './api';

export default function EventsPage({ addToast }) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ name: '', date: '', location: '' });
  const [saving, setSaving] = useState(false);

  const load = () => {
    getEvents().then(r => { setEvents(r.data); setLoading(false); }).catch(() => setLoading(false));
  };

  useEffect(load, []);

  const handleCreate = async () => {
    if (!form.name || !form.date || !form.location) {
      addToast('All fields are required.', 'error'); return;
    }
    setSaving(true);
    try {
      const res = await createEvent(form);
      setEvents(prev => [res.data, ...prev]);
      setForm({ name: '', date: '', location: '' });
      addToast(`Event "${res.data.name}" created!`, 'success');
    } catch {
      addToast('Failed to create event.', 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Events</h1>
        <p className="page-subtitle">Manage concerts, festivals, or any audience events.</p>
      </div>

      <div className="events-grid">

        {/* Events list */}
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          {loading ? (
            <div className="empty-state" style={{ padding: 60 }}><span className="spinner" /></div>
          ) : events.length === 0 ? (
            <div className="empty-state" style={{ padding: 60 }}>
              <div className="empty-state-icon">🎤</div>
              <div className="empty-state-title">No events yet</div>
              <div className="empty-state-text">Create your first event using the form.</div>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="video-table">
                <thead>
                  <tr>
                    <th>ID</th><th>Event Name</th><th>Date</th><th>Location</th><th>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map(ev => (
                    <tr key={ev.id}>
                      <td style={{ color: 'var(--text-muted)' }}>#{ev.id}</td>
                      <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{ev.name}</td>
                      <td>{ev.date}</td>
                      <td>{ev.location}</td>
                      <td>{new Date(ev.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Create event form */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Create Event</span>
          </div>
          <div className="form-group">
            <label className="form-label">Event Name</label>
            <input id="event-name-input" className="form-input" placeholder="e.g. Glastonbury 2025"
              value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} />
          </div>
          <div className="form-group">
            <label className="form-label">Date</label>
            <input id="event-date-input" className="form-input" type="date"
              value={form.date} onChange={e => setForm(p => ({ ...p, date: e.target.value }))} />
          </div>
          <div className="form-group">
            <label className="form-label">Location</label>
            <input id="event-location-input" className="form-input" placeholder="e.g. Somerset, UK"
              value={form.location} onChange={e => setForm(p => ({ ...p, location: e.target.value }))} />
          </div>
          <button id="create-event-btn" className="btn btn-primary"
            style={{ width: '100%', justifyContent: 'center', marginTop: 8 }}
            onClick={handleCreate} disabled={saving}>
            {saving ? <><span className="spinner" /> Saving…</> : '🎤 Create Event'}
          </button>
        </div>
      </div>
    </div>
  );
}
