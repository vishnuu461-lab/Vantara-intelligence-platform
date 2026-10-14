// ============================================================
// CLVPage.jsx — Customer Lifetime Value Predictions
// ============================================================
// Clicking a row opens a CLV-specific detail drawer within
// this page. Navigation to /customers/:id is only via the
// explicit "View Full Customer Profile" button in the drawer.
// ============================================================

import { useState, useEffect } from 'react';
import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts';

import Navbar from '../components/layout/Navbar';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorMessage from '../components/common/ErrorMessage';
import DetailDrawer from '../components/common/DetailDrawer';
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

// ── CLV Drawer Content ─────────────────────────────────────

function CLVDrawerContent({ row }) {
  if (!row) return null;
  const cfg = getTierCfg(row.tier);

  return (
    <>
      {/* CLV hero */}
      <div style={{
        background: cfg.color + '12',
        border: `1px solid ${cfg.color}30`,
        borderRadius: 12, padding: '24px 20px', marginBottom: 20,
        textAlign: 'center',
      }}>
        <div style={{ fontSize: 13, color: cfg.color, fontWeight: 700, marginBottom: 8 }}>
          {cfg.icon} {row.tier} TIER
        </div>
        <div style={{ fontSize: 46, fontWeight: 900, color: cfg.color, lineHeight: 1 }}>
          {formatRupee(row.predicted_clv)}
        </div>
        <div style={{ fontSize: 13, color: '#64748b', marginTop: 6 }}>
          Estimated Customer Lifetime Value
        </div>
        <div style={{
          fontSize: 11, color: '#94a3b8', marginTop: 4,
          fontStyle: 'italic'
        }}>
          * Analytical estimate — not a guaranteed revenue figure
        </div>
      </div>

      {/* Metrics grid */}
      <div className="drawer-metrics">
        <div className="drawer-metric">
          <div className="drawer-metric-label">Current Spend</div>
          <div className="drawer-metric-value" style={{ color: '#10b981' }}>
            {formatRupee(row.total_spend)}
          </div>
        </div>
        <div className="drawer-metric">
          <div className="drawer-metric-label">Total Orders</div>
          <div className="drawer-metric-value">{row.total_orders ?? '—'}</div>
        </div>
        <div className="drawer-metric">
          <div className="drawer-metric-label">Avg Order Value</div>
          <div className="drawer-metric-value">{formatRupee(row.average_order_value)}</div>
        </div>
        <div className="drawer-metric">
          <div className="drawer-metric-label">Last Purchase</div>
          <div className="drawer-metric-value" style={{ fontSize: 13 }}>
            {formatDate(row.last_purchase_date)}
          </div>
        </div>
      </div>

      {/* CLV context factors */}
      {row.context && Object.keys(row.context).length > 0 && (
        <>
          <div className="drawer-section-title">📊 CLV Factors</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 20 }}>
            {row.context.orders_per_year != null && (
              <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '8px 12px', background: '#f8fafc', borderRadius: 8,
                fontSize: 13, border: '1px solid #e2e8f0',
              }}>
                <span style={{ color: '#475569' }}>📦 Orders per year</span>
                <strong>{Number(row.context.orders_per_year).toFixed(1)}</strong>
              </div>
            )}
            {row.context.lifetime_estimate_years != null && (
              <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '8px 12px', background: '#f8fafc', borderRadius: 8,
                fontSize: 13, border: '1px solid #e2e8f0',
              }}>
                <span style={{ color: '#475569' }}>⏳ Estimated lifetime</span>
                <strong>{row.context.lifetime_estimate_years} years</strong>
              </div>
            )}
            {row.context.recency_factor != null && (
              <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '8px 12px', background: '#f8fafc', borderRadius: 8,
                fontSize: 13, border: '1px solid #e2e8f0',
              }}>
                <span style={{ color: '#475569' }}>🕐 Recency factor</span>
                <strong style={{ color: row.context.recency_factor >= 1 ? '#10b981' : '#f59e0b' }}>
                  ×{row.context.recency_factor}
                </strong>
              </div>
            )}
            {row.context.current_spend_vs_average && (
              <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '8px 12px', background: '#f8fafc', borderRadius: 8,
                fontSize: 13, border: '1px solid #e2e8f0',
              }}>
                <span style={{ color: '#475569' }}>📈 vs Portfolio avg</span>
                <strong style={{ fontSize: 12 }}>{row.context.current_spend_vs_average}</strong>
              </div>
            )}
            {row.context.days_since_last_purchase != null && (
              <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '8px 12px', background: '#f8fafc', borderRadius: 8,
                fontSize: 13, border: '1px solid #e2e8f0',
              }}>
                <span style={{ color: '#475569' }}>📅 Days since purchase</span>
                <strong style={{
                  color: row.context.days_since_last_purchase > 180 ? '#ef4444' :
                    row.context.days_since_last_purchase > 60 ? '#f59e0b' : '#10b981'
                }}>
                  {row.context.days_since_last_purchase}d
                </strong>
              </div>
            )}
          </div>
        </>
      )}

      {/* Recommended action */}
      {row.action && (
        <>
          <div className="drawer-section-title">💡 Recommended Action</div>
          <div style={{
            background: cfg.color + '10',
            border: `1px solid ${cfg.color}30`,
            borderRadius: 8, padding: '14px 16px',
            fontSize: 13, color: '#1e293b', lineHeight: 1.6,
          }}>
            {row.action}
          </div>
        </>
      )}

      {/* Subscription status */}
      <div style={{ marginTop: 16, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <span className={`badge ${row.subscription_status === 'Premium' ? 'badge-indigo' :
            row.subscription_status === 'Active' ? 'badge-green' :
              row.subscription_status === 'Inactive' ? 'badge-amber' : 'badge-red'
          }`}>
          {row.subscription_status}
        </span>
        {row.location && <span className="badge badge-gray">📍 {row.location}</span>}
      </div>
    </>
  );
}

// ── Main Component ─────────────────────────────────────────

export default function CLVPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState('');
  const [error, setError] = useState(null);
  const [filterTier, setFilterTier] = useState('');

  // Drawer state
  const [selectedRow, setSelectedRow] = useState(null);

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
          formatted: clv?.predicted_clv_formatted ?? '—',
          tier: clv?.clv_tier ?? clv?.tier ?? 'Unknown',
          action: clv?.recommended_action ?? clv?.action ?? '',
          context: clv?.context ?? {},
        };
      });

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

  const total = rows.length;
  const totalCLV = rows.reduce((s, r) => s + (r.predicted_clv ?? 0), 0);
  const avgCLV = total > 0 ? totalCLV / total : 0;

  const tierCounts = {};
  rows.forEach(r => { tierCounts[r.tier] = (tierCounts[r.tier] || 0) + 1; });

  const pieData = Object.entries(tierCounts).map(([tier, count]) => ({
    name: tier, value: count, color: getTierCfg(tier).color,
  }));

  const barData = rows.slice(0, 10).map(r => ({
    name: r.name?.split(' ')[0] || r.customer_id,
    clv: Math.round((r.predicted_clv ?? 0) / 1000),
    tier: r.tier,
  }));

  const displayedRows = filterTier ? rows.filter(r => r.tier === filterTier) : rows;

  return (
    <>
      <Navbar
        pageTitle="Customer Value"
        pageSubtitle={`${total} customers · Portfolio CLV: ${formatRupee(totalCLV)} · Avg: ${formatRupee(avgCLV)}`}
      />

      <div className="page-body">

        {/* Page Header */}
        <div className="page-header">
          <div>
            <h1>Customer Lifetime Value</h1>
            <p>Analytical RFM model estimating 12-month revenue per customer</p>
          </div>
          <button className="btn btn-outline btn-sm" onClick={fetchAll}>🔄 Refresh</button>
        </div>

        {/* TIER STAT CARDS */}
        <div className="stats-grid" style={{ marginBottom: 24 }}>
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
          <div className="stat-card">
            <div className="stat-icon green">💰</div>
            <div className="stat-info">
              <div className="stat-label">Portfolio CLV</div>
              <div className="stat-value">{formatRupee(totalCLV)}</div>
              <div className="stat-sub">Avg {formatRupee(avgCLV)} per customer</div>
            </div>
          </div>
        </div>

        {/* CHARTS */}
        <div className="grid-2" style={{ marginBottom: 24 }}>
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

          <div className="card">
            <div className="card-header">
              <div>
                <div className="card-title">Top 10 Highest Value Customers</div>
                <div className="card-subtitle">Predicted CLV in ₹K · Click a row for details</div>
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

        {/* TABLE */}
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
              <div className="card-subtitle">
                Click any row to view CLV details · Sorted by highest predicted value first
              </div>
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
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {displayedRows.map((r, index) => {
                  const cfg = getTierCfg(r.tier);
                  const maxCLV = rows[0]?.predicted_clv || 1;
                  const barPct = Math.round(((r.predicted_clv ?? 0) / maxCLV) * 100);

                  return (
                    <tr key={r.customer_id}
                      style={{
                        cursor: 'pointer',
                        background: selectedRow?.customer_id === r.customer_id
                          ? cfg.color + '0d' : undefined,
                      }}
                      onClick={() => setSelectedRow(r)}
                    >
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
                      <td>
                        <button
                          className="btn btn-primary btn-sm"
                          onClick={(e) => { e.stopPropagation(); setSelectedRow(r); }}
                        >
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
            <span>Analytical CLV Formula (RFM-based) · Flask backend</span>
          </div>
        </div>

      </div>

      {/* CLV Detail Drawer */}
      <DetailDrawer
        open={!!selectedRow}
        onClose={() => setSelectedRow(null)}
        title={selectedRow?.name || ''}
        subtitle={`Customer Lifetime Value · ${selectedRow?.customer_id}`}
        customerId={selectedRow?.customer_id}
      >
        <CLVDrawerContent row={selectedRow} />
      </DetailDrawer>
    </>
  );
}
