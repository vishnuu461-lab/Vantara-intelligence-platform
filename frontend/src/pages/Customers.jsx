// ============================================================
// Customers.jsx — Customer list page
// ============================================================
// Calls GET /api/customers with filters & pagination
// Displays a searchable, filterable customer table
// ============================================================

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/layout/Navbar';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorMessage from '../components/common/ErrorMessage';
import { getCustomers } from '../api/customerApi';

// ── Helpers ────────────────────────────────────────────────

function formatRupee(amount) {
  if (!amount && amount !== 0) return '—';
  if (amount >= 100000) return `₹${(amount / 100000).toFixed(1)}L`;
  if (amount >= 1000) return `₹${(amount / 1000).toFixed(1)}K`;
  return `₹${Math.round(amount)}`;
}

function formatDate(dateStr) {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric'
  });
}

// Status badge color mapping
function StatusBadge({ status }) {
  const map = {
    Premium: 'badge-indigo',
    Active: 'badge-green',
    Inactive: 'badge-amber',
    Cancelled: 'badge-red',
  };
  return (
    <span className={`badge ${map[status] || 'badge-gray'}`}>
      {status || '—'}
    </span>
  );
}

// Risk badge based on complaints + status
function RiskBadge({ complaints, status }) {
  const isHighRisk = status === 'Cancelled' || status === 'Inactive' || complaints >= 2;
  const isMedRisk = complaints === 1;
  if (isHighRisk) return <span className="badge badge-red">High</span>;
  if (isMedRisk) return <span className="badge badge-amber">Medium</span>;
  return <span className="badge badge-green">Low</span>;
}

// ── Main Component ─────────────────────────────────────────

const LOCATIONS = ['', 'Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Hyderabad', 'Pune', 'Kolkata'];
const STATUSES = ['', 'Active', 'Premium', 'Inactive', 'Cancelled'];

export default function Customers() {
  const navigate = useNavigate();

  // State
  const [customers, setCustomers] = useState([]);
  const [pagination, setPagination] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filter state
  const [search, setSearch] = useState('');
  const [location, setLocation] = useState('');
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(1);

  // Fetch customers from backend
  const fetchCustomers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getCustomers({ page, perPage: 15, location, status });
      if (result.success) {
        setCustomers(result.customers);
        setPagination(result.pagination);
      } else {
        setError('Backend returned an error.');
      }
    } catch (err) {
      setError(err.message || 'Could not connect to backend.');
    } finally {
      setLoading(false);
    }
  }, [page, location, status]);

  // Re-fetch when page/filters change
  useEffect(() => { fetchCustomers(); }, [fetchCustomers]);

  // Reset to page 1 when filters change
  const handleLocationChange = (val) => { setLocation(val); setPage(1); };
  const handleStatusChange = (val) => { setStatus(val); setPage(1); };

  // Client-side search on name/id (after data loads from backend)
  const displayedCustomers = search.trim()
    ? customers.filter(c =>
      c.name?.toLowerCase().includes(search.toLowerCase()) ||
      c.customer_id?.toLowerCase().includes(search.toLowerCase()) ||
      c.location?.toLowerCase().includes(search.toLowerCase())
    )
    : customers;

  // ── RENDER ──────────────────────────────────────────────

  return (
    <>
      <Navbar
        pageTitle="Customers"
        pageSubtitle={
          pagination.total_customers
            ? `${pagination.total_customers} customers · Page ${pagination.page} of ${pagination.total_pages}`
            : 'All customer records'
        }
      />

      <div className="page-body">

        {/* Page Header */}
        <div className="page-header">
          <div>
            <h1>Customer Records</h1>
            <p>Search, filter, and manage all your customers</p>
          </div>
        </div>

        {/* ── Filters Bar ── */}
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-body" style={{ padding: '16px 24px' }}>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>

              {/* Search box */}
              <div className="search-wrap" style={{ flex: 1, minWidth: 200 }}>
                <span className="search-icon">🔍</span>
                <input
                  className="input"
                  placeholder="Search by name, ID, or location..."
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                />
              </div>

              {/* Location filter */}
              <select
                className="select"
                style={{ width: 160 }}
                value={location}
                onChange={e => handleLocationChange(e.target.value)}
              >
                <option value="">All Locations</option>
                {LOCATIONS.filter(l => l).map(l => (
                  <option key={l} value={l}>{l}</option>
                ))}
              </select>

              {/* Status filter */}
              <select
                className="select"
                style={{ width: 160 }}
                value={status}
                onChange={e => handleStatusChange(e.target.value)}
              >
                <option value="">All Statuses</option>
                {STATUSES.filter(s => s).map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>

              {/* Clear filters */}
              {(search || location || status) && (
                <button className="btn btn-outline btn-sm" onClick={() => {
                  setSearch(''); setLocation(''); setStatus(''); setPage(1);
                }}>
                  ✕ Clear
                </button>
              )}

              {/* Refresh */}
              <button className="btn btn-outline btn-sm" onClick={fetchCustomers}>
                🔄 Refresh
              </button>

            </div>
          </div>
        </div>

        {/* ── Table ── */}
        <div className="card">

          {loading ? (
            <LoadingSpinner message="Loading customers..." />
          ) : error ? (
            <ErrorMessage message={error} onRetry={fetchCustomers} />
          ) : displayedCustomers.length === 0 ? (
            <div className="state-center">
              <div className="state-icon">👥</div>
              <div className="state-title">No customers found</div>
              <div className="state-desc">Try changing your search or filters.</div>
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
                    <th>Risk</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {displayedCustomers.map(c => (
                    <tr key={c.customer_id}>

                      <td>
                        <span className="badge badge-gray" style={{ fontFamily: 'monospace', fontSize: 12 }}>
                          {c.customer_id}
                        </span>
                      </td>

                      <td>
                        <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{c.name}</div>
                        <div className="td-muted">{c.gender}, {c.age} yrs</div>
                      </td>

                      <td className="td-muted">📍 {c.location || '—'}</td>

                      <td><StatusBadge status={c.subscription_status} /></td>

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

                      <td>
                        <RiskBadge complaints={c.complaints} status={c.subscription_status} />
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

          {/* ── Pagination ── */}
          {!loading && !error && pagination.total_pages > 1 && (
            <div style={{
              padding: '16px 24px',
              borderTop: '1px solid var(--border)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                Showing {((page - 1) * 15) + 1}–{Math.min(page * 15, pagination.total_customers)} of {pagination.total_customers} customers
              </span>

              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  className="btn btn-outline btn-sm"
                  disabled={!pagination.has_prev}
                  onClick={() => setPage(p => p - 1)}
                  style={{ opacity: pagination.has_prev ? 1 : 0.4 }}
                >
                  ← Prev
                </button>

                {/* Page number buttons */}
                {Array.from({ length: pagination.total_pages }, (_, i) => i + 1).map(p => (
                  <button
                    key={p}
                    className={`btn btn-sm ${p === page ? 'btn-primary' : 'btn-outline'}`}
                    onClick={() => setPage(p)}
                  >
                    {p}
                  </button>
                ))}

                <button
                  className="btn btn-outline btn-sm"
                  disabled={!pagination.has_next}
                  onClick={() => setPage(p => p + 1)}
                  style={{ opacity: pagination.has_next ? 1 : 0.4 }}
                >
                  Next →
                </button>
              </div>
            </div>
          )}

        </div>

        {/* ── Summary footer ── */}
        {!loading && !error && (
          <div style={{ marginTop: 16, fontSize: 12, color: 'var(--text-muted)', textAlign: 'right' }}>
            Data from Flask + MySQL backend · {pagination.total_customers} total records
          </div>
        )}

      </div>
    </>
  );
}
