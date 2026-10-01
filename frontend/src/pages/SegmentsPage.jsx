// ============================================================
// SegmentsPage.jsx — Customer Segmentation Analytics
// ============================================================
// Calls GET /api/segments
// API response structure:
//   segmentation.customers_by_segment = {
//     "High Risk":   { count: 8, customers: [...] },
//     "High Value":  { count: 6, customers: [...] },
//     "Regular":     { count: X, customers: [...] },
//     "New":         { count: X, customers: [...] },
//     "Inactive":    { count: X, customers: [...] },
//   }
//   segmentation.total_customers = 27
// ============================================================

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

import Navbar from '../components/layout/Navbar';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorMessage from '../components/common/ErrorMessage';
import { getAllSegments } from '../api/predictionApi';

// ── Segment configuration ─────────────────────────────────

const SEGMENT_CONFIG = {
  'High Value': {
    color: '#4f46e5', badgeClass: 'badge-indigo', icon: '🏆',
    desc: 'Top spenders with high order frequency and strong loyalty.',
  },
  'Regular': {
    color: '#3b82f6', badgeClass: 'badge-blue', icon: '👤',
    desc: 'Consistent buyers with moderate spend — key revenue base.',
  },
  'New': {
    color: '#10b981', badgeClass: 'badge-green', icon: '🆕',
    desc: 'Recently joined customers — focus on onboarding and retention.',
  },
  'Inactive': {
    color: '#f59e0b', badgeClass: 'badge-amber', icon: '😴',
    desc: 'Low/no recent activity — re-engagement campaigns needed.',
  },
  'High Risk': {
    color: '#ef4444', badgeClass: 'badge-red', icon: '⚠️',
    desc: 'High churn probability — urgent retention action required.',
  },
};

// fallback for unknown segment names
function getSegConfig(name) {
  return SEGMENT_CONFIG[name] || {
    color: '#94a3b8', badgeClass: 'badge-gray', icon: '📂',
    desc: 'Customer group.',
  };
}

// ── Helpers ────────────────────────────────────────────────

function formatRupee(v) {
  if (!v && v !== 0) return '—';
  if (v >= 100000) return `₹${(v / 100000).toFixed(1)}L`;
  if (v >= 1000) return `₹${(v / 1000).toFixed(1)}K`;
  return `₹${Math.round(v)}`;
}

function formatDate(d) {
  if (!d) return '—';
  return new Date(d).toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric'
  });
}

// ── Main Component ─────────────────────────────────────────

export default function SegmentsPage() {
  const navigate = useNavigate();

  const [segData, setSegData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState(null); // set after data loads

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getAllSegments();
      if (res.success) {
        setSegData(res.segmentation);
        // Default tab = first segment returned
        const firstKey = Object.keys(res.segmentation.customers_by_segment || {})[0];
        setActiveTab(prev => prev || firstKey || 'High Value');
      } else {
        setError('Segmentation data unavailable.');
      }
    } catch (err) {
      setError(err.message || 'Could not connect to backend.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  if (loading) return (
    <>
      <Navbar pageTitle="Segments" pageSubtitle="Customer groups and categories" />
      <div className="page-body"><LoadingSpinner message="Running segmentation..." /></div>
    </>
  );

  if (error) return (
    <>
      <Navbar pageTitle="Segments" pageSubtitle="Customer groups and categories" />
      <div className="page-body"><ErrorMessage message={error} onRetry={fetchData} /></div>
    </>
  );

  // ── Extract data ───────────────────────────────────────
  //  bySegment = { "High Risk": { count: 8, customers: [...] }, ... }
  const bySegment = segData.customers_by_segment || {};
  const total = segData.total_customers || 0;
  const segNames = Object.keys(bySegment);

  // Pie chart data
  const pieData = segNames.map(name => ({
    name,
    value: bySegment[name]?.count || 0,
    color: getSegConfig(name).color,
  }));

  // Customers in the active tab
  const activeInfo = bySegment[activeTab] || {};
  const activeCustomers = activeInfo.customers || [];
  const activeCount = activeInfo.count || 0;

  // ── Render ─────────────────────────────────────────────
  return (
    <>
      <Navbar
        pageTitle="Segments"
        pageSubtitle={`${total} customers across ${segNames.length} segments`}
      />

      <div className="page-body">

        {/* Header */}
        <div className="page-header">
          <div>
            <h1>Customer Segments</h1>
            <p>Rule-based grouping by value, activity, and risk level</p>
          </div>
          <button className="btn btn-outline btn-sm" onClick={fetchData}>🔄 Refresh</button>
        </div>

        {/* ── SUMMARY CARDS ── */}
        <div className="stats-grid" style={{ marginBottom: 24 }}>
          {segNames.map(name => {
            const cfg = getSegConfig(name);
            const count = bySegment[name]?.count || 0;
            const pct = total > 0 ? ((count / total) * 100).toFixed(0) : 0;
            return (
              <div
                key={name}
                className="stat-card"
                style={{
                  cursor: 'pointer',
                  borderBottom: activeTab === name
                    ? `3px solid ${cfg.color}` : '3px solid transparent',
                }}
                onClick={() => setActiveTab(name)}
              >
                <div className="stat-icon" style={{ background: cfg.color + '20', fontSize: 22 }}>
                  {cfg.icon}
                </div>
                <div className="stat-info">
                  <div className="stat-label">{name}</div>
                  <div className="stat-value">{count}</div>
                  <div className="stat-sub">{pct}% of customers</div>
                </div>
              </div>
            );
          })}
        </div>

        {/* ── CHART + DEFINITIONS ── */}
        <div className="grid-2" style={{ marginBottom: 24 }}>

          {/* Pie chart */}
          <div className="card">
            <div className="card-header">
              <div>
                <div className="card-title">Segment Distribution</div>
                <div className="card-subtitle">{total} customers total</div>
              </div>
            </div>
            <div className="card-body">
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%" cy="50%"
                    outerRadius={100} innerRadius={55}
                    paddingAngle={3} dataKey="value"
                  >
                    {pieData.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v, n) => [`${v} customers`, n]} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Segment definitions */}
          <div className="card">
            <div className="card-header">
              <div className="card-title">Segment Definitions</div>
            </div>
            <div className="card-body">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {segNames.map(name => {
                  const cfg = getSegConfig(name);
                  const count = bySegment[name]?.count || 0;
                  return (
                    <div
                      key={name}
                      onClick={() => setActiveTab(name)}
                      style={{
                        display: 'flex', alignItems: 'flex-start', gap: 12,
                        padding: '10px 12px', borderRadius: 'var(--radius)',
                        background: activeTab === name ? cfg.color + '15' : 'transparent',
                        cursor: 'pointer', transition: 'background 0.15s',
                      }}
                    >
                      <span style={{ fontSize: 20, flexShrink: 0 }}>{cfg.icon}</span>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <span style={{ fontWeight: 600, fontSize: 13 }}>{name}</span>
                          <span className={`badge ${cfg.badgeClass}`}>{count}</span>
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>
                          {cfg.desc}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

        </div>

        {/* ── CUSTOMER TABLE ── */}
        <div className="card">

          {/* Tab pills */}
          <div style={{
            display: 'flex', gap: 4, padding: '12px 16px',
            borderBottom: '1px solid var(--border)', overflowX: 'auto',
          }}>
            {segNames.map(name => {
              const cfg = getSegConfig(name);
              const isActive = activeTab === name;
              return (
                <button key={name} onClick={() => setActiveTab(name)} style={{
                  padding: '6px 14px', borderRadius: 999, border: 'none',
                  fontSize: 12, fontWeight: 600, cursor: 'pointer', whiteSpace: 'nowrap',
                  background: isActive ? cfg.color : 'transparent',
                  color: isActive ? 'white' : 'var(--text-secondary)',
                  transition: 'all 0.15s',
                }}>
                  {cfg.icon} {name} ({bySegment[name]?.count || 0})
                </button>
              );
            })}
          </div>

          {/* Active segment description banner */}
          <div style={{
            padding: '8px 20px', fontSize: 12, color: 'var(--text-secondary)',
            background: getSegConfig(activeTab).color + '0d',
            borderBottom: '1px solid var(--border)',
          }}>
            {getSegConfig(activeTab).desc}
          </div>

          {/* Table */}
          {activeCustomers.length === 0 ? (
            <div className="state-center" style={{ padding: '40px 0' }}>
              <div className="state-icon">👥</div>
              <div className="state-title">No customers in this segment</div>
            </div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Customer ID</th>
                    <th>Name</th>
                    <th>Location</th>
                    <th>Status</th>
                    <th>Orders</th>
                    <th>Total Spend</th>
                    <th>Last Purchase</th>
                    <th>Complaints</th>
                    <th>Reason</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {activeCustomers.map(c => (
                    <tr key={c.customer_id}>
                      <td>
                        <span className="badge badge-gray" style={{ fontFamily: 'monospace', fontSize: 12 }}>
                          {c.customer_id}
                        </span>
                      </td>
                      <td style={{ fontWeight: 600 }}>{c.name}</td>
                      <td className="td-muted">📍 {c.location || '—'}</td>
                      <td>
                        <span className={`badge ${c.subscription_status === 'Premium' ? 'badge-indigo' :
                            c.subscription_status === 'Active' ? 'badge-green' :
                              c.subscription_status === 'Inactive' ? 'badge-amber' :
                                'badge-red'
                          }`}>
                          {c.subscription_status}
                        </span>
                      </td>
                      <td style={{ textAlign: 'center', fontWeight: 600 }}>
                        {c.total_orders ?? '—'}
                      </td>
                      <td style={{ fontWeight: 600, color: 'var(--success)' }}>
                        {formatRupee(c.total_spend)}
                      </td>
                      <td className="td-muted">{formatDate(c.last_purchase_date)}</td>
                      <td style={{ textAlign: 'center' }}>
                        {c.complaints > 0
                          ? <span style={{ color: 'var(--danger)', fontWeight: 600 }}>⚠ {c.complaints}</span>
                          : <span style={{ color: 'var(--text-muted)' }}>0</span>
                        }
                      </td>
                      <td style={{ fontSize: 11, color: 'var(--text-secondary)', maxWidth: 180 }}>
                        {c.segment_reason || '—'}
                      </td>
                      <td>
                        <button
                          className="btn btn-primary btn-sm"
                          onClick={() => navigate(`/customers/${c.customer_id}`)}
                        >
                          View →
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Footer */}
          <div style={{
            padding: '12px 20px', borderTop: '1px solid var(--border)',
            fontSize: 12, color: 'var(--text-muted)',
            display: 'flex', justifyContent: 'space-between',
          }}>
            <span>Showing {activeCount} customer{activeCount !== 1 ? 's' : ''} in <strong>{activeTab}</strong></span>
            <span>Rule-based segmentation · Flask + MySQL</span>
          </div>

        </div>
      </div>
    </>
  );
}
