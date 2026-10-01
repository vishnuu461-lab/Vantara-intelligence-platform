// ============================================================
// CustomerDetail.jsx — Full AI-powered customer profile
// ============================================================
// Calls APIs in parallel:
//   1. GET /api/customers/:id          → profile + purchases
//   2. GET /api/customers/:id/insights → full AI report
//   3. GET /api/customers/:id/explain/shap  → SHAP explanation
//   4. GET /api/customers/:id/next-purchase → next purchase pred
//   5. GET /api/customers/:id/recommend    → product recommendations
//   6. GET /api/customers/:id/anomaly      → anomaly score
// ============================================================

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Navbar from '../components/layout/Navbar';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorMessage from '../components/common/ErrorMessage';
import { getCustomerById, getInsights } from '../api/customerApi';
import api from '../api/axios';

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

// ── Small Reusable Pieces ──────────────────────────────────

function InfoRow({ label, value }) {
    return (
        <div style={{
            display: 'flex', justifyContent: 'space-between',
            padding: '8px 0', borderBottom: '1px solid var(--border)'
        }}>
            <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{label}</span>
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{value || '—'}</span>
        </div>
    );
}

function SectionCard({ title, icon, children, style }) {
    return (
        <div className="card" style={style}>
            <div className="card-header">
                <div className="card-title">{icon} {title}</div>
            </div>
            <div className="card-body">{children}</div>
        </div>
    );
}

// Health score colour
function healthColor(score) {
    if (score >= 75) return '#10b981';
    if (score >= 50) return '#f59e0b';
    if (score >= 25) return '#ef4444';
    return '#7f1d1d';
}

function churnBadgeClass(level) {
    if (level === 'Low') return 'badge-green';
    if (level === 'Medium') return 'badge-amber';
    return 'badge-red';
}

function clvBadgeClass(tier) {
    const map = {
        Platinum: 'badge-indigo', Gold: 'badge-gold',
        Silver: 'badge-blue', Bronze: 'badge-gray', Entry: 'badge-gray'
    };
    return map[tier] || 'badge-gray';
}

function segmentBadgeClass(code) {
    const map = {
        HIGH_VALUE: 'badge-indigo', REGULAR: 'badge-blue',
        NEW: 'badge-green', INACTIVE: 'badge-amber', HIGH_RISK: 'badge-red'
    };
    return map[code] || 'badge-gray';
}

function priorityStyle(priority = '') {
    if (priority.includes('URGENT') || priority.includes('CRITICAL'))
        return { background: 'var(--danger-light)', borderLeft: '3px solid var(--danger)', color: '#dc2626' };
    if (priority.includes('OPPORTUNITY'))
        return { background: 'var(--success-light)', borderLeft: '3px solid var(--success)', color: '#059669' };
    return { background: 'var(--info-light)', borderLeft: '3px solid var(--info)', color: '#2563eb' };
}

// SHAP bar colour: positive = red (increases churn), negative = green
function shapBarColor(val) {
    return val > 0 ? '#ef4444' : '#10b981';
}

// Anomaly badge
function anomalyBadge(flag) {
    return flag === 'ANOMALY'
        ? { bg: '#fef2f2', color: '#dc2626', border: '#fca5a5', text: '⚠ Anomaly Detected' }
        : { bg: '#f0fdf4', color: '#16a34a', border: '#86efac', text: '✓ Normal Behaviour' };
}

// ── Main Component ─────────────────────────────────────────

export default function CustomerDetail() {
    const { id } = useParams();
    const navigate = useNavigate();

    const [customer, setCustomer] = useState(null);
    const [purchases, setPurchases] = useState([]);
    const [report, setReport] = useState(null);
    const [shapData, setShapData] = useState(null);
    const [nextPurchase, setNextPurchase] = useState(null);
    const [recData, setRecData] = useState(null);
    const [anomalyData, setAnomalyData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchAll = async () => {
        setLoading(true);
        setError(null);
        try {
            // Core data in parallel
            const [custRes, insightRes] = await Promise.all([
                getCustomerById(id),
                getInsights(id),
            ]);

            if (!custRes.success) throw new Error(custRes.error || 'Customer not found');
            if (!insightRes.success) throw new Error(insightRes.error || 'Insights failed');

            setCustomer(custRes.customer);
            setPurchases(custRes.purchase_history || []);
            setReport(insightRes.intelligence_report);

            // New AI panels — fetch in parallel, non-blocking
            const [shapRes, npRes, recRes, anomRes] = await Promise.allSettled([
                api.get(`/api/customers/${id}/explain/shap`),
                api.get(`/api/customers/${id}/next-purchase`),
                api.get(`/api/customers/${id}/recommend`),
                api.get(`/api/customers/${id}/anomaly`),
            ]);

            if (shapRes.status === 'fulfilled') setShapData(shapRes.value.data?.explanation);
            if (npRes.status === 'fulfilled') setNextPurchase(npRes.value.data?.next_purchase);
            if (recRes.status === 'fulfilled') setRecData(recRes.value.data?.recommendations);
            if (anomRes.status === 'fulfilled') setAnomalyData(anomRes.value.data?.anomaly);

        } catch (err) {
            setError(err.message || 'Failed to load customer data.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchAll(); }, [id]);

    // ── Loading ────────────────────────────────────────────
    if (loading) return (
        <>
            <Navbar pageTitle={`Customer: ${id}`} pageSubtitle="Loading intelligence report..." />
            <div className="page-body">
                <LoadingSpinner message="Fetching customer data and running ML predictions..." />
            </div>
        </>
    );

    // ── Error ──────────────────────────────────────────────
    if (error) return (
        <>
            <Navbar pageTitle={`Customer: ${id}`} pageSubtitle="Error" />
            <div className="page-body">
                <button className="btn btn-outline btn-sm" onClick={() => navigate('/customers')}
                    style={{ marginBottom: 20 }}>← Back to Customers</button>
                <ErrorMessage message={error} onRetry={fetchAll} />
            </div>
        </>
    );

    // ── Destructure data ───────────────────────────────────
    const pred = report.predictions || {};
    const churn = pred.churn || {};
    const clv = pred.clv || {};
    const segment = pred.segment || {};
    const beh = report.behavior_summary || {};
    const recs = report.recommendations || [];
    const score = report.health_score ?? 0;
    const color = healthColor(score);

    const statusClass = {
        Premium: 'badge-indigo', Active: 'badge-green',
        Inactive: 'badge-amber', Cancelled: 'badge-red'
    }[customer.subscription_status] || 'badge-gray';

    // ── CSV Export ─────────────────────────────────────────
    const exportCSV = () => {
        const rows = [
            ['Field', 'Value'],
            ['Customer ID', id],
            ['Name', customer.name],
            ['Email', customer.email],
            ['Location', customer.location],
            ['Subscription', customer.subscription_status],
            ['Health Score', score],
            ['Churn Risk', churn.risk_level],
            ['Churn %', churn.percentage],
            ['CLV Tier', clv.tier],
            ['CLV Predicted', clv.formatted],
            ['Segment', segment.name],
            ['Total Orders', beh.total_orders],
            ['Total Spend', beh.total_spend],
            ['Days Since Last Purchase', beh.days_since_purchase],
        ];
        if (shapData) {
            rows.push(['--- SHAP Explanation ---', '']);
            rows.push(['Plain Language', shapData.plain_language_explanation]);
            (shapData.shap_values || []).forEach(s => {
                rows.push([s.feature, `${s.shap_value > 0 ? '+' : ''}${s.shap_value} (${s.direction})`]);
            });
        }
        const csv = rows.map(r => r.map(c => `"${c}"`).join(',')).join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = `${id}_intelligence_report.csv`;
        a.click(); URL.revokeObjectURL(url);
    };

    // ── Render ─────────────────────────────────────────────
    return (
        <>
            <Navbar
                pageTitle={customer.name}
                pageSubtitle={`${id} · ${customer.location || '—'} · ${customer.subscription_status}`}
            />

            <div className="page-body">

                {/* Back + Export */}
                <div style={{ display: 'flex', gap: 12, marginBottom: 20, alignItems: 'center' }}>
                    <button className="btn btn-outline btn-sm" onClick={() => navigate('/customers')}>
                        ← Back to Customers
                    </button>
                    <button className="btn btn-primary btn-sm" onClick={exportCSV}>
                        ⬇ Export CSV Report
                    </button>
                </div>

                {/* ── PROFILE HEADER CARD ── */}
                <div className="card" style={{ marginBottom: 20 }}>
                    <div className="card-body">
                        <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start', flexWrap: 'wrap' }}>

                            {/* Avatar */}
                            <div style={{
                                width: 72, height: 72, borderRadius: '50%',
                                background: 'var(--primary)', color: 'white',
                                fontSize: 26, fontWeight: 700,
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                flexShrink: 0
                            }}>
                                {customer.name?.[0] || '?'}
                            </div>

                            {/* Name + meta */}
                            <div style={{ flex: 1, minWidth: 200 }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                                    <h2 style={{ fontSize: 22, fontWeight: 700 }}>{customer.name}</h2>
                                    <span className={`badge ${statusClass}`}>{customer.subscription_status}</span>
                                    <span className={`badge ${segmentBadgeClass(segment.code)}`}>{segment.name || '—'}</span>
                                </div>
                                <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 6, display: 'flex', gap: 20, flexWrap: 'wrap' }}>
                                    <span>📧 {customer.email || '—'}</span>
                                    <span>📍 {customer.location || '—'}</span>
                                    <span>🎂 {customer.age ? `${customer.age} yrs` : '—'}</span>
                                    <span>⚥ {customer.gender || '—'}</span>
                                </div>
                                <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
                                    🗓️ Last purchase: {formatDate(customer.last_purchase_date)}
                                    &nbsp;·&nbsp; 🌐 {customer.website_visits ?? 0} site visits
                                    &nbsp;·&nbsp; ⚠ {customer.complaints ?? 0} complaint{customer.complaints !== 1 ? 's' : ''}
                                </div>
                            </div>

                            {/* Health Score Gauge */}
                            <div style={{ textAlign: 'center', flexShrink: 0 }}>
                                <div style={{
                                    width: 80, height: 80, borderRadius: '50%',
                                    border: `5px solid ${color}`,
                                    display: 'flex', flexDirection: 'column',
                                    alignItems: 'center', justifyContent: 'center'
                                }}>
                                    <span style={{ fontSize: 22, fontWeight: 800, color }}>{score}</span>
                                    <span style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase' }}>/ 100</span>
                                </div>
                                <div style={{ fontSize: 11, fontWeight: 600, color, marginTop: 6 }}>{report.health_label}</div>
                                <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>Health Score</div>
                            </div>

                        </div>
                    </div>
                </div>

                {/* ── ROW 1: AI Summary + Predictions ── */}
                <div className="grid-2" style={{ marginBottom: 20 }}>

                    <SectionCard title="AI Intelligence Summary" icon="🧠">
                        <p style={{ fontSize: 13.5, lineHeight: 1.8, color: 'var(--text-primary)' }}>
                            {report.ai_summary || 'No summary available.'}
                        </p>
                        <div style={{
                            marginTop: 12, fontSize: 11, color: 'var(--text-muted)',
                            fontStyle: 'italic', borderTop: '1px solid var(--border)', paddingTop: 10
                        }}>
                            📅 Report generated: {report.report_generated}
                        </div>
                    </SectionCard>

                    <SectionCard title="ML Predictions" icon="📊">
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <div>
                                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>CHURN RISK</div>
                                    <div style={{ fontSize: 22, fontWeight: 700 }}>{churn.percentage || '—'}</div>
                                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Probability of churning</div>
                                </div>
                                <span className={`badge ${churnBadgeClass(churn.risk_level)}`} style={{ fontSize: 13, padding: '6px 14px' }}>
                                    {churn.risk_level || '—'} Risk
                                </span>
                            </div>

                            <hr style={{ borderColor: 'var(--border)' }} />

                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <div>
                                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>PREDICTED CLV</div>
                                    <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--success)' }}>{clv.formatted || '—'}</div>
                                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Customer Lifetime Value (est.)</div>
                                </div>
                                <span className={`badge ${clvBadgeClass(clv.tier)}`} style={{ fontSize: 13, padding: '6px 14px' }}>
                                    {clv.tier || '—'} Tier
                                </span>
                            </div>

                            <hr style={{ borderColor: 'var(--border)' }} />

                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <div>
                                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>SEGMENT</div>
                                    <div style={{ fontSize: 18, fontWeight: 700 }}>{segment.name || '—'}</div>
                                    <div style={{ fontSize: 11, color: 'var(--text-muted)', maxWidth: 200 }}>{segment.reason || ''}</div>
                                </div>
                                <span className={`badge ${segmentBadgeClass(segment.code)}`} style={{ fontSize: 13, padding: '6px 14px' }}>
                                    {segment.name || '—'}
                                </span>
                            </div>
                        </div>
                    </SectionCard>

                </div>

                {/* ── ROW 2: Behavior + Account ── */}
                <div className="grid-2" style={{ marginBottom: 20 }}>

                    <SectionCard title="Purchase Behavior" icon="🛒">
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
                            <InfoRow label="Recency (days since last purchase)" value={beh.days_since_purchase ?? '—'} />
                            <InfoRow label="Purchase Frequency" value={beh.frequency || '—'} />
                            <InfoRow label="Spending Level" value={beh.spending_level || '—'} />
                            <InfoRow label="Favorite Category" value={beh.favorite_category || '—'} />
                            <InfoRow label="Total Orders" value={beh.total_orders ?? '—'} />
                            <InfoRow label="Total Spend" value={formatRupee(beh.total_spend)} />
                        </div>
                    </SectionCard>

                    <SectionCard title="Account Details" icon="👤">
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
                            <InfoRow label="Customer ID" value={customer.customer_id} />
                            <InfoRow label="Email" value={customer.email} />
                            <InfoRow label="Age" value={customer.age ? `${customer.age} years` : '—'} />
                            <InfoRow label="Gender" value={customer.gender} />
                            <InfoRow label="Location" value={customer.location} />
                            <InfoRow label="Subscription Status" value={customer.subscription_status} />
                            <InfoRow label="Website Visits" value={customer.website_visits ?? 0} />
                            <InfoRow label="Complaints Filed" value={customer.complaints ?? 0} />
                            <InfoRow label="Avg Order Value" value={formatRupee(customer.average_order_value)} />
                        </div>
                    </SectionCard>

                </div>

                {/* ── NEW: SHAP EXPLANATION PANEL ── */}
                {shapData && !shapData.error && (
                    <SectionCard title="Explainable AI — Why this Churn Prediction?" icon="🔍" style={{ marginBottom: 20 }}>
                        {/* Plain language */}
                        <div style={{
                            background: churn.risk_level === 'High' ? '#fef2f2' : churn.risk_level === 'Low' ? '#f0fdf4' : '#fefce8',
                            border: `1px solid ${churn.risk_level === 'High' ? '#fca5a5' : churn.risk_level === 'Low' ? '#86efac' : '#fde68a'}`,
                            borderRadius: 8, padding: '12px 16px', marginBottom: 16,
                            fontSize: 13.5, lineHeight: 1.8,
                            color: churn.risk_level === 'High' ? '#991b1b' : churn.risk_level === 'Low' ? '#166534' : '#92400e'
                        }}>
                            💬 <strong>Plain-language explanation:</strong><br />
                            {shapData.plain_language_explanation}
                        </div>

                        {/* SHAP bars */}
                        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 10 }}>
                            Feature impact on churn probability (SHAP values) — red = increases risk, green = decreases risk
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                            {(shapData.shap_values || []).map((s, i) => {
                                const barWidth = Math.min(Math.abs(s.shap_value) * 300, 100);
                                const barCol = shapBarColor(s.shap_value);
                                return (
                                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                                        <div style={{ width: 180, fontSize: 12, color: 'var(--text-secondary)', textAlign: 'right', flexShrink: 0 }}>
                                            {s.feature}
                                        </div>
                                        <div style={{ flex: 1, background: 'var(--bg-tertiary)', borderRadius: 4, height: 14, position: 'relative' }}>
                                            <div style={{
                                                width: `${barWidth}%`, height: '100%',
                                                background: barCol, borderRadius: 4,
                                                transition: 'width 0.4s ease',
                                            }} />
                                        </div>
                                        <div style={{ width: 60, fontSize: 11, color: barCol, fontWeight: 600, flexShrink: 0 }}>
                                            {s.shap_value > 0 ? '+' : ''}{s.shap_value?.toFixed(3)}
                                        </div>
                                        <div style={{ fontSize: 11, color: 'var(--text-muted)', width: 120, flexShrink: 0 }}>
                                            val: {s.actual_value ?? '—'}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 12, fontStyle: 'italic' }}>
                            Method: {shapData.method} | Model prediction: {shapData.prediction} ({(shapData.churn_probability * 100).toFixed(1)}%)
                        </div>
                    </SectionCard>
                )}

                {/* ── NEW: NEXT-PURCHASE PREDICTION ── */}
                {nextPurchase && !nextPurchase.error && (
                    <div className="grid-2" style={{ marginBottom: 20 }}>
                        <SectionCard title="Next Purchase Prediction" icon="🛍️">
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
                                <InfoRow label="Predicted Next Date" value={formatDate(nextPurchase.predicted_next_date)} />
                                <InfoRow label="Days Until Next Purchase" value={
                                    nextPurchase.days_until_next >= 0
                                        ? `In ${nextPurchase.days_until_next} days`
                                        : `${Math.abs(nextPurchase.days_until_next)} days overdue`
                                } />
                                <InfoRow label="Predicted Amount" value={formatRupee(nextPurchase.predicted_amount)} />
                                <InfoRow label="Likely Category" value={nextPurchase.likely_category || '—'} />
                                <InfoRow label="Avg Purchase Interval" value={`${nextPurchase.avg_interval_days} days`} />
                                <InfoRow label="Purchase History Count" value={nextPurchase.purchase_history_count} />
                            </div>
                            {/* Probability pill */}
                            <div style={{ marginTop: 14, display: 'flex', alignItems: 'center', gap: 10 }}>
                                <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Next-Purchase Probability:</div>
                                <div style={{
                                    background: nextPurchase.next_purchase_probability >= 0.7
                                        ? '#d1fae5' : nextPurchase.next_purchase_probability >= 0.4 ? '#fef9c3' : '#fee2e2',
                                    color: nextPurchase.next_purchase_probability >= 0.7
                                        ? '#065f46' : nextPurchase.next_purchase_probability >= 0.4 ? '#78350f' : '#991b1b',
                                    padding: '4px 12px', borderRadius: 20, fontSize: 13, fontWeight: 700
                                }}>
                                    {(nextPurchase.next_purchase_probability * 100).toFixed(0)}% — {nextPurchase.probability_label}
                                </div>
                            </div>
                            {/* Mini sequence */}
                            {nextPurchase.sequence_summary?.length > 0 && (
                                <div style={{ marginTop: 14 }}>
                                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>Last {nextPurchase.sequence_summary.length} purchases:</div>
                                    {nextPurchase.sequence_summary.map((p, i) => (
                                        <div key={i} style={{
                                            display: 'flex', justifyContent: 'space-between',
                                            fontSize: 12, padding: '4px 0',
                                            borderBottom: '1px solid var(--border)'
                                        }}>
                                            <span style={{ color: 'var(--text-secondary)' }}>{formatDate(p.date)}</span>
                                            <span className="badge badge-blue">{p.category || '—'}</span>
                                            <span style={{ fontWeight: 600, color: 'var(--success)' }}>{formatRupee(p.amount)}</span>
                                            {p.gap_days != null && <span style={{ color: 'var(--text-muted)' }}>+{p.gap_days}d</span>}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </SectionCard>

                        {/* ── NEW: ANOMALY DETECTION ── */}
                        {anomalyData && !anomalyData.error && (
                            <SectionCard title="Anomaly Detection" icon="🔎">
                                {(() => {
                                    const badge = anomalyBadge(anomalyData.anomaly_flag);
                                    return (
                                        <>
                                            <div style={{
                                                background: badge.bg, color: badge.color,
                                                border: `1px solid ${badge.border}`,
                                                borderRadius: 8, padding: '10px 14px',
                                                fontSize: 14, fontWeight: 700, marginBottom: 14
                                            }}>
                                                {badge.text}
                                            </div>

                                            {/* Score gauge */}
                                            <div style={{ marginBottom: 14 }}>
                                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                                                    <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Anomaly Score</span>
                                                    <span style={{ fontSize: 12, fontWeight: 700, color: anomalyData.anomaly_score > 50 ? '#dc2626' : '#16a34a' }}>
                                                        {anomalyData.anomaly_score}/100
                                                    </span>
                                                </div>
                                                <div style={{ background: 'var(--bg-tertiary)', borderRadius: 8, height: 10 }}>
                                                    <div style={{
                                                        width: `${anomalyData.anomaly_score}%`, height: '100%', borderRadius: 8,
                                                        background: anomalyData.anomaly_score > 70 ? '#ef4444' : anomalyData.anomaly_score > 40 ? '#f59e0b' : '#10b981',
                                                        transition: 'width 0.5s ease'
                                                    }} />
                                                </div>
                                            </div>

                                            <div style={{ fontSize: 13, lineHeight: 1.7, color: 'var(--text-secondary)', marginBottom: 12 }}>
                                                {anomalyData.explanation}
                                            </div>

                                            <div style={{ fontSize: 11, color: 'var(--text-muted)', fontStyle: 'italic' }}>
                                                Method: Isolation Forest | Raw score: {anomalyData.raw_score}
                                            </div>
                                        </>
                                    );
                                })()}
                            </SectionCard>
                        )}
                    </div>
                )}

                {/* ── NEW: PRODUCT RECOMMENDATIONS ── */}
                {recData && !recData.error && recData.recommendations?.length > 0 && (
                    <SectionCard title="Product Recommendations" icon="🎯" style={{ marginBottom: 20 }}>
                        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 14 }}>
                            Personalised based on purchase history · Method: <strong>{recData.method}</strong>
                            {recData.already_purchased?.length > 0 && (
                                <> · Already purchased: {recData.already_purchased.join(', ')}</>
                            )}
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
                            {recData.recommendations.map((rec, i) => (
                                <div key={i} style={{
                                    background: 'var(--bg-secondary)',
                                    border: '1px solid var(--border)',
                                    borderRadius: 10, padding: '12px 14px',
                                }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                                        <span style={{
                                            background: rec.source === 'collaborative' ? '#dbeafe' : '#f3e8ff',
                                            color: rec.source === 'collaborative' ? '#1d4ed8' : '#7c3aed',
                                            fontSize: 10, padding: '2px 8px', borderRadius: 10, fontWeight: 600
                                        }}>
                                            {rec.source === 'collaborative' ? '👥 Collaborative' : '⭐ Popular'}
                                        </span>
                                    </div>
                                    <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>{rec.category}</div>
                                    <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.5 }}>{rec.reason}</div>
                                </div>
                            ))}
                        </div>
                    </SectionCard>
                )}

                {/* ── EXISTING: Recommended Actions ── */}
                {recs.length > 0 && (
                    <SectionCard title="Recommended Actions" icon="💡" style={{ marginBottom: 20 }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                            {recs.map((rec, i) => (
                                <div key={i} style={{
                                    padding: '12px 16px',
                                    borderRadius: 'var(--radius)',
                                    ...priorityStyle(rec.priority)
                                }}>
                                    <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>
                                        {rec.priority} — {rec.action}
                                    </div>
                                    <div style={{ fontSize: 12, opacity: 0.85 }}>{rec.detail}</div>
                                </div>
                            ))}
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 12, fontStyle: 'italic' }}>
                            {report.disclaimer}
                        </div>
                    </SectionCard>
                )}

                {/* ── PURCHASE HISTORY TABLE ── */}
                <SectionCard title={`Purchase History (${purchases.length} records)`} icon="🧾">
                    {purchases.length === 0 ? (
                        <div className="state-center" style={{ padding: '32px 0' }}>
                            <div className="state-desc">No purchase records found.</div>
                        </div>
                    ) : (
                        <div className="table-wrap">
                            <table>
                                <thead>
                                    <tr>
                                        <th>#</th>
                                        <th>Category</th>
                                        <th>Amount</th>
                                        <th>Date</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {purchases.map((p, i) => (
                                        <tr key={p.purchase_id || i}>
                                            <td className="td-muted">{i + 1}</td>
                                            <td><span className="badge badge-blue">{p.product_category}</span></td>
                                            <td style={{ fontWeight: 600, color: 'var(--success)' }}>
                                                {formatRupee(p.amount)}
                                            </td>
                                            <td className="td-muted">{formatDate(p.purchase_date)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </SectionCard>

            </div>
        </>
    );
}
