// ============================================================
// Sidebar.jsx — Left navigation panel
// ============================================================
// This component shows the brand logo and navigation links.
// It stays fixed on the left side of every page.
//
// useLocation() tells us which page we're on, so we can
// highlight the correct menu item as "active".
// ============================================================

import { NavLink, useLocation } from 'react-router-dom';

// Each nav item: path = URL, label = display name, icon = emoji
const NAV_ITEMS = [
  { path: '/', label: 'Dashboard', icon: '📊' },
  { path: '/customers', label: 'Customers', icon: '👥' },
  { path: '/churn', label: 'Churn Prediction', icon: '⚠️' },
  { path: '/clv', label: 'Customer Value', icon: '💎' },
  { path: '/behavior', label: 'Purchase Behavior', icon: '🛒' },
  { path: '/segments', label: 'Segments', icon: '🗂️' },
  { path: '/insights', label: 'Insights', icon: '🧠' },
  { path: '/upload', label: 'Data Upload', icon: '📤' },
];

export default function Sidebar() {
  const location = useLocation();

  return (
    <aside className="sidebar">

      {/* Brand Logo */}
      <div className="sidebar-logo">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
          <img
            src="/logo.svg"
            alt="Vantara Logo"
            style={{ height: 38, width: 'auto', flexShrink: 0 }}
          />
          <div className="brand-name">VANTARA</div>
        </div>
        <div className="brand-sub">Customer Intelligence</div>
      </div>

      {/* Navigation Links */}
      <nav className="sidebar-nav">
        <div className="nav-section-label">Main Menu</div>

        {NAV_ITEMS.map((item) => {
          // Check if this link is the current page
          const isActive =
            item.path === '/'
              ? location.pathname === '/'
              : location.pathname.startsWith(item.path);

          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={`nav-item ${isActive ? 'active' : ''}`}
            >
              <span className="nav-icon">{item.icon}</span>
              {item.label}
            </NavLink>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="sidebar-footer">
        v1.0.0 · Backend: localhost:5000
      </div>

    </aside>
  );
}
