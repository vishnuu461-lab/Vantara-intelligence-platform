// ============================================================
// CustomerDetail.jsx — Full AI-powered customer profile
// ============================================================
// Calls 2 APIs in parallel:
//   1. GET /api/customers/:id          → profile + purchases
//   2. GET /api/customers/:id/insights → full AI report
//      (insights already contains churn, clv, segment, behavior)
//
// Promise.all() runs both calls simultaneously — faster than
// calling them one by one.
// ============================================================

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Navbar from '../components/layout/Navbar';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorMessage from '../components/common/ErrorMessage';
import { getCustomerById, getInsights } from '../api/customerApi';

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

// Churn risk colour class
function churnBadgeClass(level) {
    if (level === 'Low') return 'badge-green';
    if (level === 'Medium') return 'badge-amber';
    return 'badge-red';
}

// CLV tier colour class
function clvBadgeClass(tier) {
    const map = {
        Platinum: 'badge-indigo', Gold: 'badge-gold',
        Silver: 'badge-blue', Bronze: 'badge-gray', Entry: 'badge-gray'
    };
    return map[tier] || 'badge-gray';
}

// Segment colour class
function segmentBadgeClass(code) {
    const map = {
        HIGH_VALUE: 'badge-indigo', REGULAR: 'badge-blue',
        NEW: 'badge-green', INACTIVE: 'badge-amber', HIGH_RISK: 'badge-red'
    };
    return map[code] || 'badge-gray';
}

// Priority → colour
function priorityStyle(priority = '') {
    if (priority.includes('URGENT') || priority.includes('CRITICAL'))
        return { background: 'var(--danger-light)', borderLeft: '3px solid var(--danger)', color: '#dc2626' };
    if (priority.includes('OPPORTUNITY'))
        return { background: 'var(--success-light)', borderLeft: '3px solid var(--success)', color: '#059669' };
    return { background: 'var(--info-light)', borderLeft: '3px solid var(--info)', color: '#2563eb' };
}

// ── Main Component ─────────────────────────────────────────

export default function CustomerDetail() {
    const { id } = useParams();
    const navigate = useNavigate();

    const [customer, setCustomer] = useState(null);
    const [purchases, setPurchases] = useState([]);
    const [report, setReport] = useState(null);   // AI insights report
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchAll = async () => {
        setLoading(true);
        setError(null);
        try {
            // Run both API calls at the same time (parallel)
            const [custRes, insightRes] = await Promise.all([
                getCustomerById(id),
                getInsights(id),
            ]);

            if (!custRes.success) throw new Error(custRes.error || 'Customer not found');
            if (!insightRes.success) throw new Error(insightRes.error || 'Insights failed');

            setCustomer(custRes.customer);
            setPurchases(custRes.purchase_history || []);
            setReport(insightRes.intelligence_report);
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

    // Status badge class
    const statusClass = {
        Premium: 'badge-indigo', Active: 'badge-green',
        Inactive: 'badge-amber', Cancelled: 'badge-red'
    }[customer.subscription_status] || 'badge-gray';

    // ── Render ─────────────────────────────────────────────
    return (
        <>
            <Navbar
                pageTitle={customer.name}
                pageSubtitle={`${id} · ${customer.location || '—'} · ${customer.subscription_status}`}
            />

            <div className="page-body">

                {/* Back button */}
                <button className="btn btn-outline btn-sm"
                    onClick={() => navigate('/customers')}
                    style={{ marginBottom: 20 }}>
                    ← Back to Customers
                </button>

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

                    {/* AI Summary */}
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

                    {/* Predictions */}
                    <SectionCard title="ML Predictions" icon="📊">
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

                            {/* Churn */}
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

                            {/* CLV */}
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <div>
                                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>PREDICTED CLV</div>
                                    <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--success)' }}>
                                        {clv.formatted || '—'}
                                    </div>
                                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Customer Lifetime Value (est.)</div>
                                </div>
                                <span className={`badge ${clvBadgeClass(clv.tier)}`} style={{ fontSize: 13, padding: '6px 14px' }}>
                                    {clv.tier || '—'} Tier
                                </span>
                            </div>

                            <hr style={{ borderColor: 'var(--border)' }} />

                            {/* Segment */}
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <div>
                                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>SEGMENT</div>
                                    <div style={{ fontSize: 18, fontWeight: 700 }}>{segment.name || '—'}</div>
                                    <div style={{ fontSize: 11, color: 'var(--text-muted)', maxWidth: 200 }}>
                                        {segment.reason || ''}
                                    </div>
                                </div>
                                <span className={`badge ${segmentBadgeClass(segment.code)}`} style={{ fontSize: 13, padding: '6px 14px' }}>
                                    {segment.name || '—'}
                                </span>
                            </div>

                        </div>
                    </SectionCard>

                </div>

                {/* ── ROW 2: Behavior + Customer Info ── */}
                <div className="grid-2" style={{ marginBottom: 20 }}>

                    {/* Purchase Behavior */}
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

                    {/* Customer Account Info */}
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

                {/* ── RECOMMENDATIONS ── */}
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
                        <div style={{
                            fontSize: 11, color: 'var(--text-muted)', marginTop: 12,
                            fontStyle: 'italic'
                        }}>
                            {report.disclaimer}
                        </div>
                    </SectionCard>
                )}

                {/* ── PURCHASE HISTORY TABLE ── */}
                <SectionCard
                    title={`Purchase History (${purchases.length} records)`}
                    icon="🧾"
                >
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
                                            <td>
                                                <span className="badge badge-blue">{p.product_category}</span>
                                            </td>
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
