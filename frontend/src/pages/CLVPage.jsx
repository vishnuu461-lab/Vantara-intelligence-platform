// ============================================================
// CLVPage.jsx — Customer Lifetime Value Predictions
// ============================================================
// Strategy: Same parallel fetch as ChurnPage
//   Step 1: GET /api/customers?per_page=100
//   Step 2: Promise.all( GET /api/customers/:id/clv for each )
//
// CLV Tiers: Platinum > Gold > Silver > Bronze > Entry
// ============================================================

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts';

import Navbar from '../components/layout/Navbar';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorMessage from '../components/common/ErrorMessage';
import { getCustomers, getCLVPrediction } from '../api/customerApi';

// ── Tier Config ────────────────────────────────────────────

const TIER_CONFIG = {
  Platinum: { color: '#7c3aed', badgeClass: 'badge-indigo', icon: '💎', label: 'Platinum' },
  Gold: { color: '#d97706', badgeClass: 'badge-gold', icon: '🥇', label: 'Gold' },
  Silver: { color: '#64748b', badgeClass: 'badge-gray', icon: '🥈', label: 'Silver' },
  Bronze: { color: '#92400e', badgeClass: 'badge-amber', icon: '🥉', label: 'Bronze' },
  Entry: { color: '#94a3b8', badgeClass: 'badge-gray', icon: '🔰', label: 'Entry' },
};

function getTierCfg(tier) {
  return TIER_CONFIG[tier] || { color: '#94a3b8', badgeClass: 'badge-gray', icon: '📊', label: tier || '—' };
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

export default function CLVPage() {
  const navigate = useNavigate();

  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState('');
  const [error, setError] = useState(null);
  const [filterTier, setFilterTier] = useState('');

  const fetchAll = async () => {
    setLoading(true);
    setError(null);
    setRows([]);
    try {
      setProgress('Loading customer list...');
      const custRes = await getCustomers({ page: 1, perPage: 100 });
      if (!custRes.success) throw new Error('Failed to load customers');

      const customers = custRes.customers;

      setProgress(`Running CLV model for ${customers.length} customers...`);
      const clvResults = await Promise.all(
        customers.map(c =>
          getCLVPrediction(c.customer_id)
            .then(res => res.success ? res : null)
            .catch(() => null)
        )
      );

      const merged = customers.map((c, i) => {
        const clv = clvResults[i];
        return {
          ...c,
          predicted_clv: clv?.predicted_clv ?? null,
          formatted: clv?.formatted ?? '—',
          tier: clv?.tier ?? 'Unknown',
          action: clv?.action ?? '',
          context: clv?.context ?? {},
        };
      });

      // Sort: Highest CLV first
      merged.sort((a, b) => (b.predicted_clv ?? 0) - (a.predicted_clv ?? 0));
      setRows(merged);
    } catch (err) {
      setError(err.message || 'Failed to load CLV data.');
    } finally {
      setLoading(false);
      setProgress('');
    }
  };

  useEffect(() => { fetchAll(); }, []);

  // ── Loading / Error ─────────────────────────────────────
  if (loading) return (
    <>
      <Navbar pageTitle="Customer Value" pageSubtitle="Predicted lifetime value" />
      <div className="page-body">
        <LoadingSpinner message={progress || 'Running CLV model...'} />
      </div>
    </>
  );

  if (error) return (
    <>
      <Navbar pageTitle="Customer Value" pageSubtitle="Predicted lifetime value" />
      <div className="page-body"><ErrorMessage message={error} onRetry={fetchAll} /></div>
    </>
  );

  // ── Derived stats ────────────────────────────────────────

  const total = rows.length;
  const totalCLV = rows.reduce((s, r) => s + (r.predicted_clv ?? 0), 0);
  const avgCLV = total > 0 ? totalCLV / total : 0;

  // Count per tier
  const tierCounts = {};
  rows.forEach(r => {
    tierCounts[r.tier] = (tierCounts[r.tier] || 0) + 1;
  });

  // Pie chart
  const pieData = Object.entries(tierCounts).map(([tier, count]) => ({
    name: tier, value: count, color: getTierCfg(tier).color,
  }));

  // Bar chart — top 10 by CLV
  const barData = rows.slice(0, 10).map(r => ({
    name: r.name?.split(' ')[0] || r.customer_id,
    clv: Math.round((r.predicted_clv ?? 0) / 1000),   // in ₹K
    tier: r.tier,
  }));

  // Filtered rows
  const displayedRows = filterTier
    ? rows.filter(r => r.tier === filterTier)
    : rows;

  // ── Render ───────────────────────────────────────────────
  return (
    <>
      <Navbar
        pageTitle="Customer Value"
        pageSubtitle={`${total} customers · Total portfolio CLV: ${formatRupee(totalCLV)} · Avg: ${formatRupee(avgCLV)}`}
      />

      <div className="page-body">

        {/* Page Header */}
        <div className="page-header">
          <div>
            <h1>Customer Lifetime Value</h1>
            <p>Random Forest ML model predicting 12-month revenue per customer</p>
          </div>
          <button className="btn btn-outline btn-sm" onClick={fetchAll}>🔄 Refresh</button>
        </div>

        {/* ── TIER STAT CARDS ── */}
        <div className="stats-grid" style={{ marginBottom: 24 }}>

          {/* Tier cards — clickable to filter */}
          {Object.keys(TIER_CONFIG).map(tier => {
            const cfg = getTierCfg(tier);
            const count = tierCounts[tier] || 0;
            return (
              <div key={tier} className="stat-card" style={{
                cursor: 'pointer',
                borderBottom: filterTier === tier ? `3px solid ${cfg.color}` : '3px solid transparent'
              }}
                onClick={() => setFilterTier(filterTier === tier ? '' : tier)}>
                <div className="stat-icon" style={{ background: cfg.color + '20', fontSize: 22 }}>
                  {cfg.icon}
                </div>
                <div className="stat-info">
                  <div className="stat-label">{tier}</div>
                  <div className="stat-value" style={{ color: cfg.color }}>{count}</div>
                  <div className="stat-sub">customers</div>
                </div>
              </div>
            );
          })}

          {/* Total portfolio CLV */}
          <div className="stat-card">
            <div className="stat-icon green">💰</div>
            <div className="stat-info">
              <div className="stat-label">Portfolio CLV</div>
              <div className="stat-value">{formatRupee(totalCLV)}</div>
              <div className="stat-sub">Avg {formatRupee(avgCLV)} per customer</div>
            </div>
          </div>
        </div>

        {/* ── CHARTS ── */}
        <div className="grid-2" style={{ marginBottom: 24 }}>

          {/* Pie: Tier distribution */}
          <div className="card">
            <div className="card-header">
              <div>
                <div className="card-title">CLV Tier Distribution</div>
                <div className="card-subtitle">Click a tier card above to filter the table</div>
              </div>
            </div>
            <div className="card-body">
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%"
                    outerRadius={95} innerRadius={55}
                    paddingAngle={3} dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                    {pieData.map((e, i) => <Cell key={i} fill={e.color} />)}
                  </Pie>
                  <Tooltip formatter={(v) => [`${v} customers`]} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Bar: Top 10 by CLV */}
          <div className="card">
            <div className="card-header">
              <div>
                <div className="card-title">Top 10 Highest Value Customers</div>
                <div className="card-subtitle">Predicted CLV in ₹K (thousands)</div>
              </div>
            </div>
            <div className="card-body">
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={barData} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#64748b' }} />
                  <YAxis tickFormatter={v => `₹${v}K`} tick={{ fontSize: 11, fill: '#64748b' }} />
                  <Tooltip formatter={(v) => [`₹${v}K`, 'Predicted CLV']} />
                  <Bar dataKey="clv" radius={[4, 4, 0, 0]}>
                    {barData.map((entry, i) => (
                      <Cell key={i} fill={getTierCfg(entry.tier).color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

        </div>

        {/* ── TABLE ── */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">
                All Customers — CLV Predictions
                {filterTier && (
                  <span className={`badge ${getTierCfg(filterTier).badgeClass}`}
                    style={{ marginLeft: 10, fontSize: 12 }}>
                    Filtered: {filterTier} ({displayedRows.length})
                  </span>
                )}
              </div>
              <div className="card-subtitle">Sorted by highest predicted value first</div>
            </div>
            {filterTier && (
              <button className="btn btn-outline btn-sm" onClick={() => setFilterTier('')}>
                ✕ Clear filter
              </button>
            )}
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Customer</th>
                  <th>Location</th>
                  <th>Status</th>
                  <th>Predicted CLV</th>
                  <th>Tier</th>
                  <th>Current Spend</th>
                  <th>Orders</th>
                  <th>Last Purchase</th>
                  <th>Recommended Action</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {displayedRows.map((r, index) => {
                  const cfg = getTierCfg(r.tier);
                  const maxCLV = rows[0]?.predicted_clv || 1;
                  const barPct = Math.round(((r.predicted_clv ?? 0) / maxCLV) * 100);

                  return (
                    <tr key={r.customer_id}>

                      <td style={{ color: 'var(--text-muted)', fontWeight: 600, fontSize: 13 }}>
                        {index + 1}
                      </td>

                      <td>
                        <div style={{ fontWeight: 600 }}>{r.name}</div>
                        <div className="td-muted" style={{ fontSize: 11 }}>{r.customer_id}</div>
                      </td>

                      <td className="td-muted">📍 {r.location || '—'}</td>

                      <td>
                        <span className={`badge ${r.subscription_status === 'Premium' ? 'badge-indigo' :
                            r.subscription_status === 'Active' ? 'badge-green' :
                              r.subscription_status === 'Inactive' ? 'badge-amber' : 'badge-red'
                          }`}>
                          {r.subscription_status}
                        </span>
                      </td>

                      <td>
                        <div style={{ fontSize: 16, fontWeight: 800, color: cfg.color }}>
                          {formatRupee(r.predicted_clv)}
                        </div>
                        {/* CLV bar relative to highest */}
                        <div style={{
                          background: 'var(--border)', borderRadius: 999,
                          height: 4, width: 80, marginTop: 4, overflow: 'hidden'
                        }}>
                          <div style={{
                            width: `${barPct}%`, height: '100%',
                            background: cfg.color, borderRadius: 999
                          }} />
                        </div>
                      </td>

                      <td>
                        <span className={`badge ${cfg.badgeClass}`} style={{ fontSize: 13 }}>
                          {cfg.icon} {r.tier}
                        </span>
                      </td>

                      <td style={{ fontWeight: 600, color: 'var(--success)' }}>
                        {formatRupee(r.total_spend)}
                      </td>

                      <td style={{ textAlign: 'center', fontWeight: 600 }}>
                        {r.total_orders ?? '—'}
                      </td>

                      <td className="td-muted">{formatDate(r.last_purchase_date)}</td>

                      <td style={{
                        fontSize: 11, color: 'var(--text-secondary)',
                        maxWidth: 200, lineHeight: 1.4
                      }}>
                        {r.action || '—'}
                      </td>

                      <td>
                        <button className="btn btn-primary btn-sm"
                          onClick={() => navigate(`/customers/${r.customer_id}`)}>
                          View →
                        </button>
                      </td>

                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div style={{
            padding: '12px 20px', borderTop: '1px solid var(--border)',
            fontSize: 12, color: 'var(--text-muted)',
            display: 'flex', justifyContent: 'space-between',
          }}>
            <span>
              Showing {displayedRows.length} of {total} customers
              {filterTier ? ` · Filtered: ${filterTier} tier` : ''}
            </span>
            <span>Random Forest Regressor · 12-month CLV estimate · Flask ML backend</span>
          </div>
        </div>

      </div>
    </>
  );
}
