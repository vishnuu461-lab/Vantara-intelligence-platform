// ============================================================
// BehaviorPage.jsx — Purchase Behavior Analytics
// ============================================================
// Strategy:
//   Step 1: GET /api/analysis/summary    → aggregate stats
//   Step 2: GET /api/customers?per_page=100
//   Step 3: Promise.all( GET /api/customers/:id/behavior )
//
// behavior_analysis fields:
//   customer_id, name, total_orders, total_spend,
//   average_order_value, days_since_last_purchase,
//   recency_label, frequency_label, spending_level,
//   favorite_category, website_visits, complaints,
//   purchases_per_month, insight, recent_purchases[]
// ============================================================

import { useState, useEffect } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts';

import Navbar from '../components/layout/Navbar';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorMessage from '../components/common/ErrorMessage';
import DetailDrawer from '../components/common/DetailDrawer';
import { getCustomers, getBehavior } from '../api/customerApi';
import { getAnalysisSummary } from '../api/predictionApi';

// ── Config ─────────────────────────────────────────────────

const CATEGORY_COLORS = {
  Electronics: '#4f46e5',
  Clothing: '#ec4899',
  Furniture: '#f59e0b',
  Books: '#10b981',
  Beauty: '#8b5cf6',
  Sports: '#3b82f6',
  Food: '#ef4444',
  Travel: '#06b6d4',
};

function catColor(cat) {
  return CATEGORY_COLORS[cat] || '#94a3b8';
}

const SPENDING_CONFIG = {
  'Premium Spender': { badgeClass: 'badge-indigo', icon: '💎' },
  'High Spender': { badgeClass: 'badge-blue', icon: '💰' },
  'Medium Spender': { badgeClass: 'badge-green', icon: '🛒' },
  'Low Spender': { badgeClass: 'badge-amber', icon: '📦' },
  'Minimal Spender': { badgeClass: 'badge-gray', icon: '🔰' },
};

const RECENCY_CONFIG = {
  'Recent': { badgeClass: 'badge-green', icon: '✅' },
  'Active': { badgeClass: 'badge-blue', icon: '🔵' },
  'Moderate': { badgeClass: 'badge-amber', icon: '🟡' },
  'Lapsing': { badgeClass: 'badge-amber', icon: '⏳' },
  'Inactive': { badgeClass: 'badge-red', icon: '🔴' },
  'Long Inactive': { badgeClass: 'badge-red', icon: '💤' },
};

function spendCfg(level) {
  return SPENDING_CONFIG[level] || { badgeClass: 'badge-gray', icon: '📦' };
}

function recencyCfg(label) {
  return RECENCY_CONFIG[label] || { badgeClass: 'badge-gray', icon: '❓' };
}

// ── Helpers ────────────────────────────────────────────────

function formatRupee(v) {
  if (!v && v !== 0) return '—';
  if (v >= 100000) return `₹${(v / 100000).toFixed(1)}L`;
  if (v >= 1000) return `₹${(v / 1000).toFixed(1)}K`;
  return `₹${Math.round(v)}`;
}

// ── Main Component ─────────────────────────────────────────

// ── Behavior Drawer Content ───────────────────────────────

const CATEGORY_DOT = {
  Electronics: '#4f46e5', Clothing: '#ec4899', Furniture: '#f59e0b',
  Books: '#10b981', Beauty: '#8b5cf6', Sports: '#3b82f6',
  Food: '#ef4444', Travel: '#06b6d4',
};

function BehaviorDrawerContent({ row }) {
  if (!row) return null;
  const spendColor = CATEGORY_DOT[row.favorite_category] || '#94a3b8';
  return (
    <>
      {/* Spending badge hero */}
      <div style={{
        background: '#f8fafc', border: '1px solid #e2e8f0',
        borderRadius: 12, padding: '18px 20px', marginBottom: 20,
        display: 'flex', gap: 16, alignItems: 'center',
      }}>
        <div style={{ fontSize: 36 }}>
          {row.spending_level?.includes('Premium') ? '💎' :
            row.spending_level?.includes('High') ? '💰' :
              row.spending_level?.includes('Medium') ? '🛒' : '📦'}
        </div>
        <div>
          <div style={{ fontWeight: 700, fontSize: 16 }}>{row.spending_level || '—'}</div>
          <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>
            {row.frequency_label} · {row.recency_label}
          </div>
        </div>
      </div>

      {/* Metrics */}
      <div className="drawer-metrics">
        <div className="drawer-metric">
          <div className="drawer-metric-label">Total Spend</div>
          <div className="drawer-metric-value" style={{ color: '#10b981' }}>
            ₹{(row.total_spend / 1000).toFixed(1)}K
          </div>
        </div>
        <div className="drawer-metric">
          <div className="drawer-metric-label">Total Orders</div>
          <div className="drawer-metric-value">{row.total_orders ?? '—'}</div>
        </div>
        <div className="drawer-metric">
          <div className="drawer-metric-label">Avg Order Value</div>
          <div className="drawer-metric-value">
            {row.average_order_value >= 1000
              ? `₹${(row.average_order_value / 1000).toFixed(1)}K`
              : `₹${Math.round(row.average_order_value)}`}
          </div>
        </div>
        <div className="drawer-metric">
          <div className="drawer-metric-label">Orders / Month</div>
          <div className="drawer-metric-value">{row.purchases_per_month?.toFixed(2) ?? '—'}</div>
        </div>
        <div className="drawer-metric">
          <div className="drawer-metric-label">Days Inactive</div>
          <div className="drawer-metric-value" style={{
            color: row.days_since_last > 365 ? '#ef4444' :
              row.days_since_last > 90 ? '#f59e0b' : '#10b981'
          }}>
            {row.days_since_last != null ? `${row.days_since_last}d` : '—'}
          </div>
        </div>
        <div className="drawer-metric">
          <div className="drawer-metric-label">Site Visits</div>
          <div className="drawer-metric-value">{row.website_visits ?? '—'}</div>
        </div>
      </div>

      {/* Favourite category */}
      <div className="drawer-section-title">🛍️ Favourite Category</div>
      <div style={{
        display: 'inline-flex', alignItems: 'center', gap: 10,
        padding: '10px 16px', borderRadius: 10, marginBottom: 16,
        background: spendColor + '18', border: `1px solid ${spendColor}30`,
      }}>
        <span style={{
          width: 10, height: 10, borderRadius: '50%', background: spendColor, flexShrink: 0
        }} />
        <span style={{ fontWeight: 700, fontSize: 14, color: spendColor }}>
          {row.favorite_category || '—'}
        </span>
      </div>

      {/* Insight */}
      {row.insight && (
        <>
          <div className="drawer-section-title">💡 Behavioral Insight</div>
          <div style={{
            background: '#eff6ff', border: '1px solid #bfdbfe',
            borderRadius: 8, padding: '14px 16px',
            fontSize: 13, color: '#1e40af', lineHeight: 1.6,
          }}>
            {row.insight}
          </div>
        </>
      )}

      {/* Tags */}
      <div style={{ marginTop: 16, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <span className={`badge ${row.subscription_status === 'Premium' ? 'badge-indigo' :
          row.subscription_status === 'Active' ? 'badge-green' :
            row.subscription_status === 'Inactive' ? 'badge-amber' : 'badge-red'
          }`}>{row.subscription_status}</span>
        {row.complaints > 0 && (
          <span className="badge badge-red">⚠ {row.complaints} complaint{row.complaints > 1 ? 's' : ''}</span>
        )}
        {row.location && <span className="badge badge-gray">📍 {row.location}</span>}
      </div>
    </>
  );
}

export default function BehaviorPage() {
  const [summary, setSummary] = useState(null);   // aggregate stats
  const [rows, setRows] = useState([]);     // per-customer behavior
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState('');
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [filterSpend, setFilterSpend] = useState('');
  const [selectedRow, setSelectedRow] = useState(null);

  const fetchAll = async () => {
    setLoading(true);
    setError(null);
    setRows([]);
    try {
      setProgress('Loading summary...');
      const [summaryRes, custRes] = await Promise.all([
        getAnalysisSummary(),
        getCustomers({ page: 1, perPage: 100 }),
      ]);

      if (summaryRes.success) setSummary(summaryRes.summary);
      if (!custRes.success) throw new Error('Failed to load customers');

      const customers = custRes.customers;

      setProgress(`Analysing behavior for ${customers.length} customers...`);
      const behResults = await Promise.all(
        customers.map(c =>
          getBehavior(c.customer_id)
            .then(res => res.success ? res.behavior_analysis : null)
            .catch(() => null)
        )
      );

      // Merge
      const merged = customers.map((c, i) => {
        const b = behResults[i];
        return {
          customer_id: c.customer_id,
          name: c.name,
          location: c.location,
          subscription_status: c.subscription_status,
          total_orders: b?.total_orders ?? c.total_orders,
          total_spend: b?.total_spend ?? c.total_spend,
          average_order_value: b?.average_order_value ?? c.average_order_value,
          days_since_last: b?.days_since_last_purchase ?? null,
          recency_label: b?.recency_label ?? '—',
          frequency_label: b?.frequency_label ?? '—',
          spending_level: b?.spending_level ?? '—',
          favorite_category: b?.favorite_category ?? '—',
          website_visits: b?.website_visits ?? c.website_visits,
          complaints: b?.complaints ?? c.complaints,
          purchases_per_month: b?.purchases_per_month ?? 0,
          insight: b?.insight ?? '',
        };
      });

      // Sort: highest spender first
      merged.sort((a, b) => (b.total_spend ?? 0) - (a.total_spend ?? 0));
      setRows(merged);
    } catch (err) {
      setError(err.message || 'Failed to load behavior data.');
    } finally {
      setLoading(false);
      setProgress('');
    }
  };

  useEffect(() => { fetchAll(); }, []);

  if (loading) return (
    <>
      <Navbar pageTitle="Purchase Behavior" pageSubtitle="Customer behavior analytics" />
      <div className="page-body">
        <LoadingSpinner message={progress || 'Analysing purchase behavior...'} />
      </div>
    </>
  );

  if (error) return (
    <>
      <Navbar pageTitle="Purchase Behavior" pageSubtitle="Customer behavior analytics" />
      <div className="page-body"><ErrorMessage message={error} onRetry={fetchAll} /></div>
    </>
  );

  // ── Chart data ──────────────────────────────────────────

  // Category breakdown (favorite_category distribution)
  const catCounts = {};
  rows.forEach(r => {
    if (r.favorite_category && r.favorite_category !== '—')
      catCounts[r.favorite_category] = (catCounts[r.favorite_category] || 0) + 1;
  });
  const catData = Object.entries(catCounts)
    .map(([name, value]) => ({ name, value, color: catColor(name) }))
    .sort((a, b) => b.value - a.value);

  // Recency breakdown
  const recCounts = {};
  rows.forEach(r => {
    if (r.recency_label && r.recency_label !== '—')
      recCounts[r.recency_label] = (recCounts[r.recency_label] || 0) + 1;
  });
  const recData = Object.entries(recCounts)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);

  // Top 10 by orders (bar chart)
  const topByOrders = [...rows]
    .sort((a, b) => (b.total_orders ?? 0) - (a.total_orders ?? 0))
    .slice(0, 10)
    .map(r => ({
      name: r.name?.split(' ')[0],
      orders: r.total_orders,
    }));

  // Spending level breakdown
  const spendCounts = {};
  rows.forEach(r => {
    if (r.spending_level && r.spending_level !== '—')
      spendCounts[r.spending_level] = (spendCounts[r.spending_level] || 0) + 1;
  });

  // Filter & search
  const displayedRows = rows.filter(r => {
    const matchSearch = !search.trim()
      || r.name?.toLowerCase().includes(search.toLowerCase())
      || r.customer_id?.toLowerCase().includes(search.toLowerCase());
    const matchSpend = !filterSpend || r.spending_level === filterSpend;
    return matchSearch && matchSpend;
  });

  const total = rows.length;

  // ── Render ──────────────────────────────────────────────
  return (
    <>
      <Navbar
        pageTitle="Purchase Behavior"
        pageSubtitle={`${total} customers · Avg spend: ${formatRupee(summary?.average_spend_per_customer)} · Avg orders: ${summary?.average_orders_per_customer?.toFixed(1)}`}
      />

      <div className="page-body">

        {/* Header */}
        <div className="page-header">
          <div>
            <h1>Purchase Behavior Analytics</h1>
            <p>RFM analysis — Recency, Frequency, and Monetary patterns across all customers</p>
          </div>
          <button className="btn btn-outline btn-sm" onClick={fetchAll}>🔄 Refresh</button>
        </div>

        {/* ── AGGREGATE CARDS ── */}
        {summary && (
          <div className="stats-grid" style={{ marginBottom: 24 }}>
            <div className="stat-card">
              <div className="stat-icon indigo">📦</div>
              <div className="stat-info">
                <div className="stat-label">Total Revenue</div>
                <div className="stat-value">{formatRupee(summary.total_revenue)}</div>
                <div className="stat-sub">{summary.total_customers_analyzed} customers</div>
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-icon green">🛒</div>
              <div className="stat-info">
                <div className="stat-label">Avg Orders / Customer</div>
                <div className="stat-value">{summary.average_orders_per_customer?.toFixed(1)}</div>
                <div className="stat-sub">orders per customer</div>
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-icon blue">💰</div>
              <div className="stat-info">
                <div className="stat-label">Avg Spend / Customer</div>
                <div className="stat-value">{formatRupee(summary.average_spend_per_customer)}</div>
                <div className="stat-sub">lifetime spend</div>
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-icon amber">📅</div>
              <div className="stat-info">
                <div className="stat-label">Avg Days Inactive</div>
                <div className="stat-value">{Math.round(summary.average_days_since_last_purchase)}</div>
                <div className="stat-sub">since last purchase</div>
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-icon red">⚠</div>
              <div className="stat-info">
                <div className="stat-label">Customers w/ Complaints</div>
                <div className="stat-value">{summary.customers_with_complaints}</div>
                <div className="stat-sub">of {summary.total_customers_analyzed} total</div>
              </div>
            </div>
          </div>
        )}

        {/* ── CHARTS ROW 1: Category + Recency ── */}
        <div className="grid-2" style={{ marginBottom: 24 }}>

          {/* Favourite Category pie */}
          <div className="card">
            <div className="card-header">
              <div>
                <div className="card-title">Favourite Product Category</div>
                <div className="card-subtitle">Most purchased category per customer</div>
              </div>
            </div>
            <div className="card-body">
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie data={catData} cx="50%" cy="50%"
                    outerRadius={90} innerRadius={50}
                    paddingAngle={3} dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                    {catData.map((e, i) => <Cell key={i} fill={e.color} />)}
                  </Pie>
                  <Tooltip formatter={(v, n) => [`${v} customers`, n]} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Top 10 by orders bar */}
          <div className="card">
            <div className="card-header">
              <div>
                <div className="card-title">Top 10 Most Active Customers</div>
                <div className="card-subtitle">By total number of orders</div>
              </div>
            </div>
            <div className="card-body">
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={topByOrders} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#64748b' }} />
                  <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
                  <Tooltip formatter={(v) => [v, 'Orders']} />
                  <Bar dataKey="orders" fill="#4f46e5" radius={[4, 4, 0, 0]}>
                    {topByOrders.map((e, i) => (
                      <Cell key={i} fill={`hsl(${240 - i * 10}, 70%, ${50 + i * 3}%)`} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

        </div>

        {/* ── CHARTS ROW 2: Recency + Spending Level ── */}
        <div className="grid-2" style={{ marginBottom: 24 }}>

          {/* Recency bar chart */}
          <div className="card">
            <div className="card-header">
              <div className="card-title">Purchase Recency Distribution</div>
              <div className="card-subtitle">How recently customers last purchased</div>
            </div>
            <div className="card-body">
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={recData} layout="vertical"
                  margin={{ top: 4, right: 24, left: 60, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 11, fill: '#64748b' }} />
                  <YAxis dataKey="name" type="category" tick={{ fontSize: 11, fill: '#64748b' }} width={90} />
                  <Tooltip formatter={(v) => [v, 'Customers']} />
                  <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                    {recData.map((e, i) => {
                      const colors = ['#10b981', '#3b82f6', '#f59e0b', '#f59e0b', '#ef4444', '#ef4444'];
                      return <Cell key={i} fill={colors[i] || '#94a3b8'} />;
                    })}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Spending level breakdown */}
          <div className="card">
            <div className="card-header">
              <div className="card-title">Spending Level Breakdown</div>
              <div className="card-subtitle">Customer distribution by spend tier</div>
            </div>
            <div className="card-body">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12, paddingTop: 8 }}>
                {Object.entries(spendCounts)
                  .sort((a, b) => b[1] - a[1])
                  .map(([level, count]) => {
                    const cfg = spendCfg(level);
                    const pct = Math.round((count / total) * 100);
                    return (
                      <div key={level} style={{ cursor: 'pointer' }}
                        onClick={() => setFilterSpend(filterSpend === level ? '' : level)}>
                        <div style={{
                          display: 'flex', justifyContent: 'space-between',
                          alignItems: 'center', marginBottom: 4
                        }}>
                          <span style={{ fontSize: 13, fontWeight: 600 }}>
                            {cfg.icon} {level}
                          </span>
                          <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                            {count} customers ({pct}%)
                          </span>
                        </div>
                        <div style={{
                          background: 'var(--border)', borderRadius: 999,
                          height: 8, overflow: 'hidden'
                        }}>
                          <div style={{
                            width: `${pct}%`, height: '100%',
                            background: filterSpend === level ? '#4f46e5' : '#94a3b8',
                            borderRadius: 999, transition: 'all 0.3s'
                          }} />
                        </div>
                      </div>
                    );
                  })}
                {filterSpend && (
                  <button className="btn btn-outline btn-sm" style={{ alignSelf: 'flex-start' }}
                    onClick={() => setFilterSpend('')}>
                    ✕ Clear filter
                  </button>
                )}
              </div>
            </div>
          </div>

        </div>

        {/* ── TABLE ── */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">
                All Customers — Behavior Analysis
                {filterSpend && (
                  <span className="badge badge-indigo" style={{ marginLeft: 10, fontSize: 12 }}>
                    {filterSpend} ({displayedRows.length})
                  </span>
                )}
              </div>
              <div className="card-subtitle">Sorted by highest total spend</div>
            </div>

            {/* Search + filter controls */}
            <div style={{ display: 'flex', gap: 8 }}>
              <input className="input" placeholder="Search name..." style={{ width: 180 }}
                value={search} onChange={e => setSearch(e.target.value)} />
              {(search || filterSpend) && (
                <button className="btn btn-outline btn-sm"
                  onClick={() => { setSearch(''); setFilterSpend(''); }}>
                  ✕ Clear
                </button>
              )}
            </div>
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Customer</th>
                  <th>Category</th>
                  <th>Spending</th>
                  <th>Recency</th>
                  <th>Frequency</th>
                  <th>Orders/Mo</th>
                  <th>Total Spend</th>
                  <th>Avg Order</th>
                  <th>Days Inactive</th>
                  <th>Visits</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {displayedRows.map(r => (
                  <tr key={r.customer_id}
                    style={{ cursor: 'pointer', background: selectedRow?.customer_id === r.customer_id ? '#f8fafc' : undefined }}
                    onClick={() => setSelectedRow(r)}
                  >

                    <td>
                      <div style={{ fontWeight: 600 }}>{r.name}</div>
                      <div className="td-muted" style={{ fontSize: 11 }}>
                        {r.customer_id} · 📍 {r.location}
                      </div>
                    </td>

                    <td>
                      <span style={{
                        display: 'inline-block', padding: '3px 10px',
                        borderRadius: 999, fontSize: 11, fontWeight: 600,
                        background: catColor(r.favorite_category) + '20',
                        color: catColor(r.favorite_category),
                      }}>
                        {r.favorite_category}
                      </span>
                    </td>

                    <td>
                      <span className={`badge ${spendCfg(r.spending_level).badgeClass}`}>
                        {spendCfg(r.spending_level).icon} {r.spending_level}
                      </span>
                    </td>

                    <td>
                      <span className={`badge ${recencyCfg(r.recency_label).badgeClass}`}>
                        {recencyCfg(r.recency_label).icon} {r.recency_label}
                      </span>
                    </td>

                    <td>
                      <span className="badge badge-blue">{r.frequency_label}</span>
                    </td>

                    <td style={{ textAlign: 'center', fontWeight: 600 }}>
                      {r.purchases_per_month?.toFixed(2)}
                    </td>

                    <td style={{ fontWeight: 600, color: 'var(--success)' }}>
                      {formatRupee(r.total_spend)}
                    </td>

                    <td className="td-muted">
                      {formatRupee(r.average_order_value)}
                    </td>

                    <td style={{ textAlign: 'center' }}>
                      {r.days_since_last != null
                        ? <span style={{
                          fontWeight: 600,
                          color: r.days_since_last > 365 ? 'var(--danger)'
                            : r.days_since_last > 90 ? 'var(--warning)'
                              : 'var(--success)'
                        }}>
                          {r.days_since_last}d
                        </span>
                        : '—'
                      }
                    </td>

                    <td style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
                      {r.website_visits ?? '—'}
                    </td>

                    <td>
                      <button className="btn btn-primary btn-sm"
                        onClick={(e) => { e.stopPropagation(); setSelectedRow(r); }}>
                        View →
                      </button>
                    </td>

                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div style={{
            padding: '12px 20px', borderTop: '1px solid var(--border)',
            fontSize: 12, color: 'var(--text-muted)',
            display: 'flex', justifyContent: 'space-between',
          }}>
            <span>Showing {displayedRows.length} of {total} customers</span>
            <span>RFM Analysis · Flask analytics backend</span>
          </div>
        </div>

      </div>

      {/* Behavior Detail Drawer */}
      <DetailDrawer
        open={!!selectedRow}
        onClose={() => setSelectedRow(null)}
        title={selectedRow?.name || ''}
        subtitle={`Purchase Behavior · ${selectedRow?.customer_id}`}
        customerId={selectedRow?.customer_id}
      >
        <BehaviorDrawerContent row={selectedRow} />
      </DetailDrawer>
    </>
  );
}
