// ============================================================
// api/dashboardApi.js — Dashboard API calls
// ============================================================
// All functions that call dashboard-related backend endpoints.
// Pages import these functions instead of writing fetch/axios
// calls directly inside components.
// ============================================================

import api from './axios';

// GET /api/dashboard
// Returns: { success, dashboard: { customer_overview, revenue_summary,
//            risk_and_value, purchase_insights, generated_at } }
export async function getDashboard() {
    const response = await api.get('/api/dashboard');
    return response.data;
}

// GET /api/analysis/summary
// Returns aggregate stats across all customers
export async function getAnalysisSummary() {
    const response = await api.get('/api/analysis/summary');
    return response.data;
}
