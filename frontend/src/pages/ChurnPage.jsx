// ============================================================
// ChurnPage.jsx — ML Churn Risk Predictions for All Customers
// ============================================================
// Strategy:
//   Step 1: GET /api/customers?per_page=100  → all customer IDs
//   Step 2: Promise.all( GET /api/customers/:id/churn for each )
//   This runs all predictions simultaneously (parallel), not one
//   by one, so it completes in ~2-3 seconds for 27 customers.
//
// Churn API response per customer:
//   { success, customer_id, churn_probability, percentage,
//     risk_level, model_used, factors }
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
import { getCustomers, getChurnPrediction } from '../api/customerApi';

// ── Config ─────────────────────────────────────────────────

const RISK_CONFIG = {
  High: { color: '#ef4444', badgeClass: 'badge-red', icon: '🔴', bg: 'var(--danger-light)', text: '#dc2626' },
  Medium: { color: '#f59e0b', badgeClass: 'badge-amber', icon: '🟡', bg: 'var(--warning-light)', text: '#d97706' },
  Low: { color: '#10b981', badgeClass: 'badge-green', icon: '🟢', bg: 'var(--success-light)', text: '#059669' },
};

function getRiskCfg(level) {
  return RISK_CONFIG[level] || RISK_CONFIG.Low;
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

export default function ChurnPage() {
  const navigate = useNavigate();

  const [rows, setRows] = useState([]);   // merged customer + churn data
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState('');   // status message while loading
  const [error, setError] = useState(null);
  const [filterRisk, setFilterRisk] = useState(''); // 'High' | 'Medium' | 'Low' | ''

  const fetchAll = async () => {
    setLoading(true);
    setError(null);
    setRows([]);

    try {
      // ── Step 1: Load all customers ──────────────────────
      setProgress('Loading customer list...');
      const custRes = await getCustomers({ page: 1, perPage: 100 });
      if (!custRes.success) throw new Error('Failed to load customers');

      const customers = custRes.customers;

      // ── Step 2: Run churn predictions in parallel ───────
      setProgress(`Running churn ML model for ${customers.length} customers...`);

      const churnResults = await Promise.all(
        customers.map(c =>
          getChurnPrediction(c.customer_id)
            .then(res => res.success ? res : null)
            .catch(() => null)   // don't fail all if one errors
        )
      );

      // ── Step 3: Merge customer + churn data ─────────────
      const merged = customers.map((c, i) => {
        const churn = churnResults[i];
        return {
          ...c,
          churn_probability: churn?.churn_probability ?? null,
          percentage: churn?.percentage ?? '—',
          risk_level: churn?.risk_level ?? 'Unknown',
          factors: churn?.factors ?? [],
        };
      });

      // Sort: High risk first, then by churn_probability descending
      merged.sort((a, b) => {
        const order = { High: 0, Medium: 1, Low: 2, Unknown: 3 };
        const diff = (order[a.risk_level] ?? 3) - (order[b.risk_level] ?? 3);
        if (diff !== 0) return diff;
        return (b.churn_probability ?? 0) - (a.churn_probability ?? 0);
      });

      setRows(merged);
    } catch (err) {
      setError(err.message || 'Failed to load churn predictions.');
    } finally {
      setLoading(false);
      setProgress('');
    }
  };

  useEffect(() => { fetchAll(); }, []);

  // ── Loading ──────────────────────────────────────────────
  if (loading) return (
    <>
      <Navbar pageTitle="Churn Prediction" pageSubtitle="ML-based churn risk analysis" />
      <div className="page-body">
        <LoadingSpinner message={progress || 'Running churn predictions...'} />
      </div>
    </>
  );

  // ── Error ────────────────────────────────────────────────
  if (error) return (
    <>
      <Navbar pageTitle="Churn Prediction" pageSubtitle="ML-based churn risk analysis" />
      <div className="page-body">
        <ErrorMessage message={error} onRetry={fetchAll} />
      </div>
    </>
  );

  // ── Derived stats ────────────────────────────────────────

  const highCount = rows.filter(r => r.risk_level === 'High').length;
  const medCount = rows.filter(r => r.risk_level === 'Medium').length;
  const lowCount = rows.filter(r => r.risk_level === 'Low').length;
  const total = rows.length;

  const avgChurn = total > 0
    ? (rows.reduce((s, r) => s + (r.churn_probability ?? 0), 0) / total * 100).toFixed(1)
    : '—';

  // Pie chart data
  const pieData = [
    { name: 'High Risk', value: highCount, color: '#ef4444' },
    { name: 'Medium Risk', value: medCount, color: '#f59e0b' },
    { name: 'Low Risk', value: lowCount, color: '#10b981' },
  ].filter(d => d.value > 0);

  // Bar chart — top 10 by churn probability
  const barData = rows.slice(0, 10).map(r => ({
    name: r.name?.split(' ')[0] || r.customer_id,  // first name only
    pct: r.churn_probability != null
      ? Math.round(r.churn_probability * 100) : 0,
  }));

  // Filtered table rows
  const displayedRows = filterRisk
    ? rows.filter(r => r.risk_level === filterRisk)
    : rows;

  // ── Render ───────────────────────────────────────────────
  return (
    <>
      <Navbar
        pageTitle="Churn Prediction"
        pageSubtitle={`${total} customers analysed · Avg churn risk: ${avgChurn}%`}
      />

      <div className="page-body">

        {/* ── Page Header ── */}
        <div className="page-header">
          <div>
            <h1>Churn Risk Analysis</h1>
            <p>Random Forest ML model predicting likelihood of customer churn</p>
          </div>
          <button className="btn btn-outline btn-sm" onClick={fetchAll}>
            🔄 Refresh
          </button>
        </div>

        {/* ── STAT CARDS ── */}
        <div className="stats-grid" style={{ marginBottom: 24 }}>
          <div className="stat-card" style={{ cursor: 'pointer' }}
            onClick={() => setFilterRisk(filterRisk === 'High' ? '' : 'High')}>
            <div className="stat-icon red">🔴</div>
            <div className="stat-info">
              <div className="stat-label">High Risk</div>
              <div className="stat-value" style={{ color: '#ef4444' }}>{highCount}</div>
              <div className="stat-sub">Immediate action needed</div>
            </div>
          </div>

          <div className="stat-card" style={{ cursor: 'pointer' }}
            onClick={() => setFilterRisk(filterRisk === 'Medium' ? '' : 'Medium')}>
            <div className="stat-icon amber">🟡</div>
            <div className="stat-info">
              <div className="stat-label">Medium Risk</div>
              <div className="stat-value" style={{ color: '#f59e0b' }}>{medCount}</div>
              <div className="stat-sub">Monitor closely</div>
            </div>
          </div>

          <div className="stat-card" style={{ cursor: 'pointer' }}
            onClick={() => setFilterRisk(filterRisk === 'Low' ? '' : 'Low')}>
            <div className="stat-icon green">🟢</div>
            <div className="stat-info">
              <div className="stat-label">Low Risk</div>
              <div className="stat-value" style={{ color: '#10b981' }}>{lowCount}</div>
              <div className="stat-sub">Healthy customers</div>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon indigo">📊</div>
            <div className="stat-info">
              <div className="stat-label">Avg Churn Risk</div>
              <div className="stat-value">{avgChurn}%</div>
              <div className="stat-sub">Across all {total} customers</div>
            </div>
          </div>
        </div>

        {/* ── CHARTS ROW ── */}
        <div className="grid-2" style={{ marginBottom: 24 }}>

          {/* Pie: Risk distribution */}
          <div className="card">
            <div className="card-header">
              <div>
                <div className="card-title">Risk Distribution</div>
                <div className="card-subtitle">Click a stat card above to filter the table</div>
              </div>
            </div>
            <div className="card-body">
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie
                    data={pieData} cx="50%" cy="50%"
                    outerRadius={95} innerRadius={55}
                    paddingAngle={3} dataKey="value"
                    label={({ name, percent }) =>
                      `${name} ${(percent * 100).toFixed(0)}%`
                    }
                  >
                    {pieData.map((e, i) => <Cell key={i} fill={e.color} />)}
                  </Pie>
                  <Tooltip formatter={(v) => [`${v} customers`]} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Bar: Top 10 highest risk */}
          <div className="card">
            <div className="card-header">
              <div>
                <div className="card-title">Top 10 Highest Churn Risk</div>
                <div className="card-subtitle">Churn probability (%)</div>
              </div>
            </div>
            <div className="card-body">
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={barData} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#64748b' }} />
                  <YAxis domain={[0, 100]} tickFormatter={v => `${v}%`}
                    tick={{ fontSize: 11, fill: '#64748b' }} />
                  <Tooltip formatter={(v) => [`${v}%`, 'Churn Risk']} />
                  <Bar dataKey="pct" radius={[4, 4, 0, 0]}>
                    {barData.map((entry, i) => (
                      <Cell key={i}
                        fill={entry.pct >= 60 ? '#ef4444' :
                          entry.pct >= 35 ? '#f59e0b' : '#10b981'} />
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
                All Customers — Churn Predictions
                {filterRisk && (
                  <span className={`badge ${getRiskCfg(filterRisk).badgeClass}`}
                    style={{ marginLeft: 10, fontSize: 12 }}>
                    Filtered: {filterRisk} Risk ({displayedRows.length})
                  </span>
                )}
              </div>
              <div className="card-subtitle">Sorted by highest risk first</div>
            </div>
            {filterRisk && (
              <button className="btn btn-outline btn-sm"
                onClick={() => setFilterRisk('')}>
                ✕ Clear filter
              </button>
            )}
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Customer</th>
                  <th>Location</th>
                  <th>Status</th>
                  <th>Churn %</th>
                  <th>Risk Level</th>
                  <th>Risk Bar</th>
                  <th>Total Spend</th>
                  <th>Last Purchase</th>
                  <th>Complaints</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {displayedRows.map(r => {
                  const cfg = getRiskCfg(r.risk_level);
                  const pctNum = r.churn_probability != null
                    ? Math.round(r.churn_probability * 100) : 0;

                  return (
                    <tr key={r.customer_id}>
                      <td>
                        <div style={{ fontWeight: 600 }}>{r.name}</div>
                        <div className="td-muted" style={{ fontSize: 11 }}>
                          {r.customer_id}
                        </div>
                      </td>

                      <td className="td-muted">📍 {r.location || '—'}</td>

                      <td>
                        <span className={`badge ${r.subscription_status === 'Premium' ? 'badge-indigo' :
                            r.subscription_status === 'Active' ? 'badge-green' :
                              r.subscription_status === 'Inactive' ? 'badge-amber' :
                                'badge-red'
                          }`}>
                          {r.subscription_status}
                        </span>
                      </td>

                      <td>
                        <span style={{
                          fontSize: 18, fontWeight: 800, color: cfg.color
                        }}>
                          {r.percentage}
                        </span>
                      </td>

                      <td>
                        <span className={`badge ${cfg.badgeClass}`}>
                          {cfg.icon} {r.risk_level}
                        </span>
                      </td>

                      {/* Visual risk bar */}
                      <td style={{ minWidth: 100 }}>
                        <div style={{
                          background: 'var(--border)', borderRadius: 999,
                          height: 8, overflow: 'hidden'
                        }}>
                          <div style={{
                            width: `${pctNum}%`, height: '100%',
                            background: cfg.color, borderRadius: 999,
                            transition: 'width 0.4s ease'
                          }} />
                        </div>
                        <div style={{
                          fontSize: 10, color: 'var(--text-muted)',
                          marginTop: 2, textAlign: 'center'
                        }}>
                          {pctNum}%
                        </div>
                      </td>

                      <td style={{ fontWeight: 600, color: 'var(--success)' }}>
                        {formatRupee(r.total_spend)}
                      </td>

                      <td className="td-muted">{formatDate(r.last_purchase_date)}</td>

                      <td style={{ textAlign: 'center' }}>
                        {r.complaints > 0
                          ? <span style={{ color: 'var(--danger)', fontWeight: 600 }}>
                            ⚠ {r.complaints}
                          </span>
                          : <span style={{ color: 'var(--text-muted)' }}>0</span>
                        }
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
              {filterRisk ? ` · Filtered to ${filterRisk} risk` : ''}
            </span>
            <span>Random Forest model · Flask ML backend</span>
          </div>
        </div>

      </div>
    </>
  );
}
