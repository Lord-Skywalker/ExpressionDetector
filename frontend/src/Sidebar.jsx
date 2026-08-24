import { NavLink } from 'react-router-dom';

const links = [
  { to: '/',        icon: '📊', label: 'Dashboard' },
  { to: '/upload',  icon: '⬆️',  label: 'Upload Video' },
  { to: '/videos',  icon: '🎬', label: 'Video Assets' },
  { to: '/events',  icon: '🎤', label: 'Events' },
  { to: '/live',    icon: '📹', label: 'Live Cam' },
];

export default function Sidebar() {
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
        <div className="status-dot">
          <div className="dot" />
          ML Pipeline Ready
        </div>
      </div>
    </aside>
  );
}
