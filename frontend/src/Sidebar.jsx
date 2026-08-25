import { NavLink } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { checkMLWorkerStatus } from './api';

const links = [
  { to: '/',        icon: '📊', label: 'Dashboard' },
  { to: '/upload',  icon: '⬆️',  label: 'Upload Video' },
  { to: '/videos',  icon: '🎬', label: 'Video Assets' },
  { to: '/events',  icon: '🎤', label: 'Events' },
  { to: '/live',    icon: '📹', label: 'Live Cam' },
];

export default function Sidebar() {
  const [pipelineStatus, setPipelineStatus] = useState('Checking...');
  const [statusClass, setStatusClass] = useState('warning');

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const res = await checkMLWorkerStatus();
        if (res.status === 'ok') {
          if (res.warming) {
            setPipelineStatus('Warming Up...');
            setStatusClass('warning');
          } else {
            setPipelineStatus('ML Pipeline Ready');
            setStatusClass(''); // Default green
          }
        } else {
          setPipelineStatus('Offline');
          setStatusClass('danger');
        }
      } catch (err) {
        setPipelineStatus('Offline');
        setStatusClass('danger');
      }
    };
    
    checkStatus();
    // Poll every 10 seconds globally
    const interval = setInterval(checkStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">🧠</div>
        <div>
          <div className="sidebar-logo-text">CrowdySense</div>
          <div className="sidebar-logo-sub">AI ANALYTICS</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        {links.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <span className="nav-item-icon">{icon}</span>
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: 'var(--text-secondary)', fontWeight: 500 }}>
          <div className={`status-dot ${statusClass}`} />
          {pipelineStatus}
        </div>
      </div>
    </aside>
  );
}
