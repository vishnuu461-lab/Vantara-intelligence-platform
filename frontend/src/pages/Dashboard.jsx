// ============================================================
// Dashboard.jsx — Main business overview page
// ============================================================
// This page calls GET /api/dashboard and displays:
//   - 8 stat cards (customers, revenue, risk, etc.)
//   - Pie chart: subscription status breakdown
//   - Bar chart: top customer locations
//   - Summary row: top category, gender, generated date
//
// REACT HOOKS EXPLAINED:
//   useState  = stores data (like a variable that triggers re-render)
//   useEffect = runs code when component loads (like "on page open")
// ============================================================

import { useState, useEffect } from 'react';
import {
    PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
    BarChart, Bar, XAxis, YAxis, CartesianGrid
} from 'recharts';

import Navbar from '../components/layout/Navbar';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorMessage from '../components/common/ErrorMessage';
import { getDashboard } from '../api/dashboardApi';

// Colors for charts
const PIE_COLORS = ['#4f46e5', '#10b981', '#f59e0b', '#ef4444'];
const BAR_COLOR = '#4f46e5';

// ============================================================
// Helper: Format currency in Indian Rupee style
// ============================================================
function formatRupee(amount) {
    if (!amount && amount !== 0) return '—';
    if (amount >= 100000) return `₹${(amount / 100000).toFixed(1)}L`;
    if (amount >= 1000) return `₹${(amount / 1000).toFixed(1)}K`;
    return `₹${Math.round(amount)}`;
}

// ============================================================
// StatCard — one metric tile
// ============================================================
function StatCard({ icon, label, value, sub, colorClass }) {
    return (
        <div className="stat-card">
            <div className={`stat-icon ${colorClass}`}>{icon}</div>
            <div className="stat-info">
                <div className="stat-label">{label}</div>
                <div className="stat-value">{value}</div>
                {sub && <div className="stat-sub">{sub}</div>}
            </div>
        </div>
    );
}

// ============================================================
// Main Dashboard Component
// ============================================================
export default function Dashboard() {
    // State variables
    const [data, setData] = useState(null);   // backend response
    const [loading, setLoading] = useState(true);   // show spinner
    const [error, setError] = useState(null);   // show error

    // fetchData: calls the backend and stores the result
    const fetchData = async () => {
        setLoading(true);
        setError(null);
        try {
            const result = await getDashboard();
            if (result.success) {
                setData(result.dashboard);
            } else {
                setError('Backend returned an error. Please check Flask is running.');
            }
        } catch (err) {
            setError(err.message || 'Could not connect to backend at localhost:5000');
        } finally {
            setLoading(false);
        }
    };

    // useEffect: runs fetchData once when the page first loads
    useEffect(() => {
        fetchData();
    }, []);   // [] = only run once (on mount)

    // ──────────────────────────────────────────────────────────
    // RENDER: Loading state
    // ──────────────────────────────────────────────────────────
    if (loading) {
        return (
            <>
                <Navbar pageTitle="Dashboard" pageSubtitle="Business overview at a glance" />
                <div className="page-body">
                    <LoadingSpinner message="Loading dashboard data from backend..." />
                </div>
            </>
        );
    }

    // ──────────────────────────────────────────────────────────
    // RENDER: Error state
    // ──────────────────────────────────────────────────────────
    if (error) {
        return (
            <>
                <Navbar pageTitle="Dashboard" pageSubtitle="Business overview at a glance" />
                <div className="page-body">
                    <ErrorMessage message={error} onRetry={fetchData} />
                </div>
            </>
        );
    }

    // ──────────────────────────────────────────────────────────
    // Extract data from backend response
    // ──────────────────────────────────────────────────────────
    const co = data.customer_overview;    // customer counts
    const rev = data.revenue_summary;     // revenue metrics
    const risk = data.risk_and_value;     // risk indicators
    const pi = data.purchase_insights;   // purchase data

    // Build pie chart data from subscription breakdown
    const pieData = [
        { name: 'Active', value: co.active_customers - co.premium_customers },
        { name: 'Premium', value: co.premium_customers },
        { name: 'Inactive', value: co.inactive_customers },
    ].filter(d => d.value > 0);

    // Build bar chart data from top locations
    const barData = (pi.top_locations || []).map(loc => ({
        name: loc.location,
        count: loc.customer_count,
    }));

    // Gender breakdown
    const genderBreakdown = pi.gender_breakdown || {};

    // ──────────────────────────────────────────────────────────
    // RENDER: Success state — full dashboard
    // ──────────────────────────────────────────────────────────
    return (
        <>
            <Navbar
                pageTitle="Dashboard"
                pageSubtitle={`Last updated: ${data.generated_at} · ${co.total_customers} customers total`}
            />

            <div className="page-body">

                {/* ── Page Header ── */}
                <div className="page-header">
                    <div>
                        <h1>Business Overview</h1>
                        <p>Real-time metrics from your customer database</p>
                    </div>
                    <button className="btn btn-outline btn-sm" onClick={fetchData}>
                        🔄 Refresh
                    </button>
                </div>

                {/* ── STAT CARDS ROW 1: Customers ── */}
                <div className="stats-grid">
                    <StatCard
                        icon="👥" colorClass="blue"
                        label="Total Customers"
                        value={co.total_customers}
                        sub="All registered customers"
                    />
                    <StatCard
                        icon="✅" colorClass="green"
                        label="Active Customers"
                        value={co.active_customers}
                        sub={`${co.premium_customers} on Premium plan`}
                    />
                    <StatCard
                        icon="😴" colorClass="amber"
                        label="Inactive Customers"
                        value={co.inactive_customers}
                        sub="Inactive or Cancelled"
                    />
                    <StatCard
                        icon="🆕" colorClass="indigo"
                        label="New (Last 30 Days)"
                        value={co.new_customers_last_30_days}
                        sub="Recently joined"
                    />
                </div>

                {/* ── STAT CARDS ROW 2: Revenue & Risk ── */}
                <div className="stats-grid">
                    <StatCard
                        icon="💰" colorClass="green"
                        label="Total Revenue"
                        value={formatRupee(rev.total_revenue)}
                        sub={`From ${rev.total_orders} total orders`}
                    />
                    <StatCard
                        icon="📦" colorClass="blue"
                        label="Avg Order Value"
                        value={formatRupee(rev.average_order_value)}
                        sub={`${rev.total_transactions} transactions`}
                    />
                    <StatCard
                        icon="⚠️" colorClass="red"
                        label="High Risk Customers"
                        value={risk.high_risk_customers}
                        sub="Churn or complaint risk"
                    />
                    <StatCard
                        icon="🏆" colorClass="indigo"
                        label="High Value Customers"
                        value={risk.high_value_customers}
                        sub={risk.high_value_threshold}
                    />
                </div>

                {/* ── CHARTS ROW ── */}
                <div className="grid-2" style={{ marginBottom: 24 }}>

                    {/* Pie Chart: Subscription Status */}
                    <div className="card">
                        <div className="card-header">
                            <div>
                                <div className="card-title">Customer Distribution</div>
                                <div className="card-subtitle">By subscription status</div>
                            </div>
                        </div>
                        <div className="card-body">
                            <ResponsiveContainer width="100%" height={240}>
                                <PieChart>
                                    <Pie
                                        data={pieData}
                                        cx="50%" cy="50%"
                                        innerRadius={60}
                                        outerRadius={95}
                                        paddingAngle={3}
                                        dataKey="value"
                                        label={({ name, percent }) =>
                                            `${name} ${(percent * 100).toFixed(0)}%`
                                        }
                                    >
                                        {pieData.map((_, i) => (
                                            <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                                        ))}
                                    </Pie>
                                    <Tooltip formatter={(v) => [`${v} customers`]} />
                                    <Legend />
                                </PieChart>
                            </ResponsiveContainer>
                        </div>
                    </div>

                    {/* Bar Chart: Top Locations */}
                    <div className="card">
                        <div className="card-header">
                            <div>
                                <div className="card-title">Top Customer Cities</div>
                                <div className="card-subtitle">Customers by location (Top 5)</div>
                            </div>
                        </div>
                        <div className="card-body">
                            <ResponsiveContainer width="100%" height={240}>
                                <BarChart data={barData} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                                    <XAxis
                                        dataKey="name"
                                        tick={{ fontSize: 12, fill: '#64748b' }}
                                    />
                                    <YAxis
                                        allowDecimals={false}
                                        tick={{ fontSize: 12, fill: '#64748b' }}
                                    />
                                    <Tooltip formatter={(v) => [`${v} customers`]} />
                                    <Bar dataKey="count" fill={BAR_COLOR} radius={[4, 4, 0, 0]} />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </div>

                </div>

                {/* ── SUMMARY ROW ── */}
                <div className="grid-3">

                    {/* Top Category */}
                    <div className="card">
                        <div className="card-header">
                            <div className="card-title">🛒 Top Product Category</div>
                        </div>
                        <div className="card-body" style={{ textAlign: 'center', padding: '32px 24px' }}>
                            <div style={{ fontSize: 36, marginBottom: 8 }}>📦</div>
                            <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--primary)' }}>
                                {pi.top_product_category || '—'}
                            </div>
                            <div className="stat-sub" style={{ marginTop: 6 }}>Most purchased category</div>
                        </div>
                    </div>

                    {/* Gender Breakdown */}
                    <div className="card">
                        <div className="card-header">
                            <div className="card-title">👤 Gender Breakdown</div>
                        </div>
                        <div className="card-body">
                            {Object.entries(genderBreakdown).length === 0 ? (
                                <div className="state-desc" style={{ textAlign: 'center' }}>No data</div>
                            ) : (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 14, paddingTop: 8 }}>
                                    {Object.entries(genderBreakdown).map(([gender, count]) => {
                                        const pct = Math.round((count / co.total_customers) * 100);
                                        return (
                                            <div key={gender}>
                                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, fontSize: 13 }}>
                                                    <span style={{ fontWeight: 500 }}>{gender}</span>
                                                    <span style={{ color: 'var(--text-secondary)' }}>{count} ({pct}%)</span>
                                                </div>
                                                <div style={{ background: 'var(--border)', borderRadius: 999, height: 8 }}>
                                                    <div style={{
                                                        width: `${pct}%`,
                                                        height: '100%',
                                                        borderRadius: 999,
                                                        background: gender === 'Female' ? '#ec4899' : '#4f46e5'
                                                    }} />
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Revenue Stats */}
                    <div className="card">
                        <div className="card-header">
                            <div className="card-title">💳 Revenue Details</div>
                        </div>
                        <div className="card-body">
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                                {[
                                    { label: 'Avg Spend / Customer', value: formatRupee(rev.average_customer_spend) },
                                    { label: 'Total Orders', value: rev.total_orders?.toLocaleString() },
                                    { label: 'Total Transactions', value: rev.total_transactions?.toLocaleString() },
                                    { label: 'Transaction Revenue', value: formatRupee(rev.purchases_revenue) },
                                ].map(item => (
                                    <div key={item.label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                        <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{item.label}</span>
                                        <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>{item.value}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>

                </div>

            </div>
        </>
    );
}
