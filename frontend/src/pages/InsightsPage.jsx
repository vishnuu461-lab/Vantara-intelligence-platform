// ============================================================
// InsightsPage.jsx — Fleet-Level AI Intelligence Dashboard
// ============================================================
// Strategy:
//   1. GET /api/customers?per_page=100  → all customer IDs
//   2. Promise.all( GET /api/customers/:id/insights for each )
//   3. Aggregate health scores, recommendations, risk patterns
//   4. Show individual customer lookup panel
//
// intelligence_report fields:
//   health_score (0-100), health_label, ai_summary,
//   predictions.churn, predictions.clv, predictions.segment,
//   behavior_summary, recommendations[], report_generated
// ============================================================

import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, Cell,
} from 'recharts';

import Navbar from '../components/layout/Navbar';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorMessage from '../components/common/ErrorMessage';
import { getCustomers, getInsights } from '../api/customerApi';

// ── Helpers ────────────────────────────────────────────────

function healthColor(score) {
  if (score >= 80) return '#10b981';
  if (score >= 60) return '#3b82f6';
  if (score >= 40) return '#f59e0b';
  if (score >= 20) return '#ef4444';
  return '#7f1d1d';
}

function formatRupee(v) {
  if (!v && v !== 0) return '—';
  if (v >= 100000) return `₹${(v / 100000).toFixed(1)}L`;
  if (v >= 1000) return `₹${(v / 1000).toFixed(1)}K`;
  return `₹${Math.round(v)}`;
}

function priorityStyle(p = '') {
  if (p.includes('URGENT') || p.includes('CRITICAL'))
    return { bg: '#fef2f2', border: '#ef4444', color: '#dc2626', dot: '🔴' };
  if (p.includes('OPPORTUNITY'))
    return { bg: '#f0fdf4', border: '#10b981', color: '#059669', dot: '🟢' };
  return { bg: '#eff6ff', border: '#3b82f6', color: '#2563eb', dot: '🔵' };
}

// Gauge ring for a single number
function ScoreGauge({ score, size = 80 }) {
  const color = healthColor(score);
  return (
    <div style={{
      width: size, height: size, borderRadius: '50%',
      border: `${size / 14}px solid ${color}`,
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', flexShrink: 0,
    }}>
      <span style={{ fontSize: size * 0.3, fontWeight: 800, color }}>{score}</span>
      <span style={{ fontSize: size * 0.12, color: 'var(--text-muted)' }}>/ 100</span>
    </div>
  );
}

// ── Health label badge ────────────────────────────────────

const HEALTH_BADGE = {
  Excellent: 'badge-green',
  Good: 'badge-blue',
  Fair: 'badge-amber',
  Poor: 'badge-red',
  Critical: 'badge-red',
};

// ── Main Component ─────────────────────────────────────────

export default function InsightsPage() {
  const navigate = useNavigate();

  const [allReports, setAllReports] = useState([]);  // { customer_id, name, report }
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState('');
  const [error, setError] = useState(null);

  // Individual lookup
  const [selectedId, setSelectedId] = useState('');
  const [lookupLoading, setLookupLoading] = useState(false);
  const [lookupReport, setLookupReport] = useState(null);

  // ── Fetch all ──────────────────────────────────────────
  const fetchAll = async () => {
    setLoading(true);
    setError(null);
    setAllReports([]);
    try {
      setProgress('Loading customer list...');
      const custRes = await getCustomers({ page: 1, perPage: 100 });
      if (!custRes.success) throw new Error('Failed to load customers');

      const customers = custRes.customers;
      setProgress(`Running AI intelligence for ${customers.length} customers...`);

      const results = await Promise.all(
        customers.map(c =>
          getInsights(c.customer_id)
            .then(res => res.success ? {
              customer_id: c.customer_id,
              name: c.name,
              report: res.intelligence_report,
            } : null)
            .catch(() => null)
        )
      );

      setAllReports(results.filter(Boolean));
    } catch (err) {
      setError(err.message || 'Failed to load insights.');
    } finally {
      setLoading(false);
      setProgress('');
    }
  };

  useEffect(() => { fetchAll(); }, []);

  // ── Load individual lookup ─────────────────────────────
  const handleLookup = async (id) => {
    if (!id) { setLookupReport(null); return; }
    setLookupLoading(true);
    try {
      const res = await getInsights(id);
      if (res.success) setLookupReport(res.intelligence_report);
    } catch { /* ignore */ }
    finally { setLookupLoading(false); }
  };

  // ── Derived aggregates ─────────────────────────────────
  const aggregates = useMemo(() => {
    if (!allReports.length) return null;

    const reports = allReports.map(r => r.report);

    // Average health score
    const avgHealth = Math.round(
      reports.reduce((s, r) => s + (r.health_score ?? 0), 0) / reports.length
    );

    // Health label distribution
    const healthDist = {};
    reports.forEach(r => {
      healthDist[r.health_label] = (healthDist[r.health_label] || 0) + 1;
    });

    // Sorted by health score
    const sorted = [...allReports].sort(
      (a, b) => (b.report.health_score ?? 0) - (a.report.health_score ?? 0)
    );
    const topAssets = sorted.slice(0, 5);
    const topRisks = sorted.slice(-5).reverse();

    // Collect all recommendations + count urgent
    let urgentCount = 0;
    let oppCount = 0;
    const recs = [];
    reports.forEach((r, i) => {
      (r.recommendations || []).forEach(rec => {
        const p = rec.priority || '';
        if (p.includes('URGENT') || p.includes('CRITICAL')) urgentCount++;
        if (p.includes('OPPORTUNITY')) oppCount++;
        recs.push({ ...rec, customer: allReports[i]?.name });
      });
    });

    // Churn risk counts
    const churnHigh = reports.filter(r =>
      r.predictions?.churn?.risk_level === 'High').length;
    const churnLow = reports.filter(r =>
      r.predictions?.churn?.risk_level === 'Low').length;

    // Health bar chart for Recharts
    const healthBar = Object.entries(healthDist).map(([label, count]) => ({
      label, count,
    }));

    // Segment distribution
    const segDist = {};
    reports.forEach(r => {
      const seg = r.predictions?.segment?.name || 'Unknown';
      segDist[seg] = (segDist[seg] || 0) + 1;
    });

    return {
      avgHealth, healthDist, healthBar,
      topAssets, topRisks,
      urgentCount, oppCount,
      totalRecs: recs.length,
      urgentRecs: recs.filter(r => {
        const p = r.priority || '';
        return p.includes('URGENT') || p.includes('CRITICAL');
      }).slice(0, 8),
      segDist,
      churnHigh, churnLow,
    };
  }, [allReports]);

  // ── Loading & Error ────────────────────────────────────

  if (loading) return (
    <>
      <Navbar pageTitle="Insights" pageSubtitle="Fleet-level AI intelligence" />
      <div className="page-body">
        <LoadingSpinner message={progress || 'Running AI analysis...'} />
      </div>
    </>
  );

  if (error) return (
    <>
      <Navbar pageTitle="Insights" pageSubtitle="Fleet-level AI intelligence" />
      <div className="page-body"><ErrorMessage message={error} onRetry={fetchAll} /></div>
    </>
  );

  const total = allReports.length;
  const agg = aggregates;

  // ── Empty state (no customers in DB yet) ───────────────
  if (!agg) return (
    <>
      <Navbar pageTitle="Insights" pageSubtitle="Fleet-level AI intelligence" />
      <div className="page-body">
        <div className="page-header">
          <div>
            <h1>AI Business Insights</h1>
            <p>Fleet-level intelligence combining ML predictions, RFM analysis, and rule-based recommendations</p>
          </div>
          <button className="btn btn-outline btn-sm" onClick={fetchAll}>🔄 Refresh</button>
        </div>
        <div className="card" style={{ textAlign: 'center', padding: '60px 24px' }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>📊</div>
          <h2 style={{ marginBottom: 8, color: 'var(--text-primary)' }}>No Customer Data Yet</h2>
          <p style={{ color: 'var(--text-secondary)', maxWidth: 420, margin: '0 auto 24px' }}>
            The database is empty. Upload your customer data via the <strong>Data Upload</strong> page
            or seed the database to see AI-powered insights.
          </p>
          <button className="btn btn-primary" onClick={() => window.location.href = '/upload'}>
            📁 Go to Data Upload
          </button>
        </div>
      </div>
    </>
  );

  // ── Render ─────────────────────────────────────────────
  return (
    <>
      <Navbar
        pageTitle="Insights"
        pageSubtitle={`${total} customers · Avg health: ${agg?.avgHealth}/100 · ${agg?.urgentCount} urgent actions`}
      />

      <div className="page-body">

        {/* Header */}

        <div className="page-header">
          <div>
            <h1>AI Business Insights</h1>
            <p>Fleet-level intelligence combining ML predictions, RFM analysis, and rule-based recommendations</p>
          </div>
          <button className="btn btn-outline btn-sm" onClick={fetchAll}>🔄 Refresh</button>
        </div>

        {/* ── FLEET HEALTH CARDS ── */}
        <div className="stats-grid" style={{ marginBottom: 24 }}>
          {/* Avg Health Score */}
          <div className="stat-card">
            <div style={{ flexShrink: 0 }}>
              <ScoreGauge score={agg.avgHealth} size={64} />
            </div>
            <div className="stat-info">
              <div className="stat-label">Fleet Health Score</div>
              <div className="stat-value" style={{ color: healthColor(agg.avgHealth) }}>
                {agg.avgHealth}
              </div>
              <div className="stat-sub">avg across {total} customers</div>
            </div>
          </div>

          {/* Urgent actions */}
          <div className="stat-card">
            <div className="stat-icon red">🚨</div>
            <div className="stat-info">
              <div className="stat-label">Urgent Actions</div>
              <div className="stat-value" style={{ color: '#ef4444' }}>{agg.urgentCount}</div>
              <div className="stat-sub">require immediate attention</div>
            </div>
          </div>

          {/* Opportunities */}
          <div className="stat-card">
            <div className="stat-icon green">💡</div>
            <div className="stat-info">
              <div className="stat-label">Opportunities</div>
              <div className="stat-value" style={{ color: '#10b981' }}>{agg.oppCount}</div>
              <div className="stat-sub">revenue growth actions</div>
            </div>
          </div>

          {/* High churn risk */}
          <div className="stat-card">
            <div className="stat-icon amber">⚠️</div>
            <div className="stat-info">
              <div className="stat-label">High Churn Risk</div>
              <div className="stat-value" style={{ color: '#f59e0b' }}>{agg.churnHigh}</div>
              <div className="stat-sub">of {total} customers at risk</div>
            </div>
          </div>

          {/* Healthy customers */}
          <div className="stat-card">
            <div className="stat-icon green">✅</div>
            <div className="stat-info">
              <div className="stat-label">Low Churn Risk</div>
              <div className="stat-value" style={{ color: '#10b981' }}>{agg.churnLow}</div>
              <div className="stat-sub">stable, retained customers</div>
            </div>
          </div>
        </div>

        {/* ── ROW 1: Health bars + Urgent Recommendations ── */}
        <div className="grid-2" style={{ marginBottom: 24 }}>

          {/* Health label distribution */}
          <div className="card">
            <div className="card-header">
              <div>
                <div className="card-title">Health Score Distribution</div>
                <div className="card-subtitle">How many customers in each health tier</div>
              </div>
            </div>
            <div className="card-body">
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={agg.healthBar}
                  margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="label" tick={{ fontSize: 12, fill: '#64748b' }} />
                  <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
                  <Tooltip formatter={(v) => [v, 'customers']} />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {agg.healthBar.map((e, i) => {
                      const colorMap = {
                        Excellent: '#10b981', Good: '#3b82f6',
                        Fair: '#f59e0b', Poor: '#ef4444', Critical: '#7f1d1d'
                      };
                      return <Cell key={i} fill={colorMap[e.label] || '#94a3b8'} />;
                    })}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Top urgent recommendations */}
          <div className="card">
            <div className="card-header">
              <div>
                <div className="card-title">🚨 Urgent Actions Required</div>
                <div className="card-subtitle">
                  {agg.urgentCount} critical recommendations across all customers
                </div>
              </div>
            </div>
            <div className="card-body">
              {agg.urgentRecs.length === 0 ? (
                <div style={{
                  textAlign: 'center', padding: '24px 0',
                  color: 'var(--success)', fontWeight: 600
                }}>
                  ✅ No urgent actions! Your customer base looks healthy.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 200, overflowY: 'auto' }}>
                  {agg.urgentRecs.map((rec, i) => {
                    const ps = priorityStyle(rec.priority);
                    return (
                      <div key={i} style={{
                        padding: '10px 14px', borderRadius: 'var(--radius)',
                        background: ps.bg, borderLeft: `3px solid ${ps.border}`,
                      }}>
                        <div style={{ fontSize: 12, fontWeight: 700, color: ps.color }}>
                          {rec.priority} — {rec.customer}
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>
                          {rec.action} · {rec.detail}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

        </div>

        {/* ── ROW 2: Top Assets + Top Risks ── */}
        <div className="grid-2" style={{ marginBottom: 24 }}>

          {/* Top 5 assets */}
          <div className="card">
            <div className="card-header">
              <div className="card-title">🏆 Top Customer Assets</div>
              <div className="card-subtitle">Highest health score — protect & grow</div>
            </div>
            <div className="card-body">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                {agg.topAssets.map(({ customer_id, name, report }) => (
                  <div key={customer_id} style={{
                    display: 'flex', alignItems: 'center', gap: 14,
                    padding: '10px 0', borderBottom: '1px solid var(--border)',
                  }}>
                    <ScoreGauge score={report.health_score} size={52} />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 700, fontSize: 14 }}>{name}</div>
                      <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                        {customer_id} · {report.predictions?.segment?.name} ·
                        CLV {report.predictions?.clv?.formatted}
                      </div>
                      <span className={`badge ${HEALTH_BADGE[report.health_label] || 'badge-gray'}`}
                        style={{ fontSize: 10, marginTop: 4 }}>
                        {report.health_label}
                      </span>
                    </div>
                    <button className="btn btn-primary btn-sm"
                      onClick={() => navigate(`/customers/${customer_id}`)}>
                      View →
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Top 5 risks */}
          <div className="card">
            <div className="card-header">
              <div className="card-title">⚠️ Customers Needing Attention</div>
              <div className="card-subtitle">Lowest health score — urgent intervention</div>
            </div>
            <div className="card-body">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                {agg.topRisks.map(({ customer_id, name, report }) => (
                  <div key={customer_id} style={{
                    display: 'flex', alignItems: 'center', gap: 14,
                    padding: '10px 0', borderBottom: '1px solid var(--border)',
                  }}>
                    <ScoreGauge score={report.health_score} size={52} />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 700, fontSize: 14 }}>{name}</div>
                      <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                        {customer_id} · Churn {report.predictions?.churn?.percentage} ·
                        {report.predictions?.churn?.risk_level} Risk
                      </div>
                      <span className={`badge ${HEALTH_BADGE[report.health_label] || 'badge-red'}`}
                        style={{ fontSize: 10, marginTop: 4 }}>
                        {report.health_label}
                      </span>
                    </div>
                    <button className="btn btn-primary btn-sm"
                      onClick={() => navigate(`/customers/${customer_id}`)}>
                      View →
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>

        </div>

        {/* ── INDIVIDUAL INSIGHT LOOKUP ── */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">🔍 Individual Customer Intelligence Lookup</div>
              <div className="card-subtitle">Select any customer to view their full AI report</div>
            </div>
          </div>
          <div className="card-body">

            {/* Customer selector */}
            <div style={{ display: 'flex', gap: 12, marginBottom: 20, alignItems: 'center' }}>
              <select className="select" style={{ flex: 1, maxWidth: 340 }}
                value={selectedId}
                onChange={e => {
                  setSelectedId(e.target.value);
                  handleLookup(e.target.value);
                }}>
                <option value="">— Select a customer —</option>
                {allReports.map(r => (
                  <option key={r.customer_id} value={r.customer_id}>
                    {r.name} ({r.customer_id})
                  </option>
                ))}
              </select>
              {selectedId && (
                <button className="btn btn-outline btn-sm"
                  onClick={() => navigate(`/customers/${selectedId}`)}>
                  Open Full Profile →
                </button>
              )}
            </div>

            {/* Lookup result */}
            {lookupLoading && <LoadingSpinner message="Loading insight report..." />}

            {!lookupLoading && lookupReport && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

                {/* Profile banner */}
                <div style={{
                  display: 'flex', gap: 20, alignItems: 'center',
                  padding: '16px 20px', borderRadius: 'var(--radius)',
                  background: 'var(--bg-secondary)', flexWrap: 'wrap',
                }}>
                  {/* Avatar */}
                  <div style={{
                    width: 52, height: 52, borderRadius: '50%',
                    background: 'var(--primary)', color: 'white',
                    fontWeight: 700, fontSize: 20,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    flexShrink: 0,
                  }}>
                    {lookupReport.name?.[0] || '?'}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 700, fontSize: 16 }}>{lookupReport.name}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                      {lookupReport.customer_id} · 📍 {lookupReport.location} ·
                      {lookupReport.subscription} · {lookupReport.predictions?.segment?.name}
                    </div>
                  </div>
                  <ScoreGauge score={lookupReport.health_score} size={64} />
                </div>

                {/* AI Summary */}
                <div style={{
                  padding: '14px 18px',
                  borderRadius: 'var(--radius)',
                  background: '#f8faff',
                  borderLeft: '3px solid var(--primary)',
                  fontSize: 13.5, lineHeight: 1.8,
                  color: 'var(--text-primary)',
                }}>
                  🧠 <strong>AI Summary:</strong> {lookupReport.ai_summary}
                </div>

                {/* 3-column prediction pills */}
                <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                  <div style={{
                    flex: 1, minWidth: 140, padding: '14px 16px',
                    borderRadius: 'var(--radius)', background: '#fef2f2',
                    border: '1px solid #fecaca', textAlign: 'center',
                  }}>
                    <div style={{ fontSize: 11, color: '#dc2626', fontWeight: 600 }}>CHURN RISK</div>
                    <div style={{ fontSize: 22, fontWeight: 800, color: '#dc2626', marginTop: 4 }}>
                      {lookupReport.predictions?.churn?.percentage}
                    </div>
                    <span className={`badge ${lookupReport.predictions?.churn?.risk_level === 'High' ? 'badge-red' :
                      lookupReport.predictions?.churn?.risk_level === 'Medium' ? 'badge-amber' :
                        'badge-green'
                      }`} style={{ marginTop: 4 }}>
                      {lookupReport.predictions?.churn?.risk_level} Risk
                    </span>
                  </div>

                  <div style={{
                    flex: 1, minWidth: 140, padding: '14px 16px',
                    borderRadius: 'var(--radius)', background: '#f0fdf4',
                    border: '1px solid #bbf7d0', textAlign: 'center',
                  }}>
                    <div style={{ fontSize: 11, color: '#059669', fontWeight: 600 }}>PREDICTED CLV</div>
                    <div style={{ fontSize: 22, fontWeight: 800, color: '#059669', marginTop: 4 }}>
                      {lookupReport.predictions?.clv?.formatted}
                    </div>
                    <span className="badge badge-green" style={{ marginTop: 4 }}>
                      {lookupReport.predictions?.clv?.tier} Tier
                    </span>
                  </div>

                  <div style={{
                    flex: 1, minWidth: 140, padding: '14px 16px',
                    borderRadius: 'var(--radius)', background: '#eff6ff',
                    border: '1px solid #bfdbfe', textAlign: 'center',
                  }}>
                    <div style={{ fontSize: 11, color: '#2563eb', fontWeight: 600 }}>SEGMENT</div>
                    <div style={{ fontSize: 18, fontWeight: 800, color: '#2563eb', marginTop: 4 }}>
                      {lookupReport.predictions?.segment?.name}
                    </div>
                    <div style={{ fontSize: 10, color: '#64748b', marginTop: 4 }}>
                      {lookupReport.predictions?.segment?.reason?.slice(0, 50)}…
                    </div>
                  </div>
                </div>

                {/* Recommendations */}
                {lookupReport.recommendations?.length > 0 && (
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>
                      💡 Recommended Actions
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      {lookupReport.recommendations.map((rec, i) => {
                        const ps = priorityStyle(rec.priority);
                        return (
                          <div key={i} style={{
                            padding: '10px 14px', borderRadius: 'var(--radius)',
                            background: ps.bg, borderLeft: `3px solid ${ps.border}`,
                          }}>
                            <div style={{ fontWeight: 600, fontSize: 12, color: ps.color }}>
                              {rec.priority} — {rec.action}
                            </div>
                            <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>
                              {rec.detail}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                    <div style={{
                      fontSize: 11, color: 'var(--text-muted)', marginTop: 8,
                      fontStyle: 'italic'
                    }}>
                      {lookupReport.disclaimer}
                    </div>
                  </div>
                )}
              </div>
            )}

            {!lookupLoading && !lookupReport && (
              <div className="state-center" style={{ padding: '24px 0' }}>
                <div className="state-icon">🔍</div>
                <div className="state-desc">Select a customer above to view their AI intelligence report</div>
              </div>
            )}

          </div>
        </div>

      </div>
    </>
  );
}
