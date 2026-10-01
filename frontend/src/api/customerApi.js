// ============================================================
// api/customerApi.js — Customer API calls
// ============================================================

import api from './axios';

// GET /api/customers?page=&per_page=&location=&status=
// Returns paginated customer list with optional filters
export async function getCustomers({ page = 1, perPage = 15, location = '', status = '' } = {}) {
    const params = { page, per_page: perPage };
    if (location) params.location = location;
    if (status) params.status = status;
    const response = await api.get('/api/customers', { params });
    return response.data;
}

// GET /api/customers/:id
// Returns one customer + their purchase history
export async function getCustomerById(id) {
    const response = await api.get(`/api/customers/${id}`);
    return response.data;
}

// GET /api/customers/:id/churn
// Backend wraps data inside { success, churn_prediction: { ... } }
// We unwrap it here so callers get a flat object.
export async function getChurnPrediction(id) {
    const response = await api.get(`/api/customers/${id}/churn`);
    const data = response.data;
    if (data.success && data.churn_prediction) {
        const cp = data.churn_prediction;
        return {
            success: true,
            customer_id: cp.customer_id,
            churn_probability: cp.churn_probability,
            percentage: cp.churn_percentage,   // normalise name
            risk_level: cp.risk_level,
            explanation: cp.explanation,
            recommendation: cp.recommendation,
            model_used: cp.model_used,
        };
    }
    return data;
}

// GET /api/customers/:id/clv
// Backend wraps inside { success, clv_prediction: { ... } }
export async function getCLVPrediction(id) {
    const response = await api.get(`/api/customers/${id}/clv`);
    const data = response.data;
    if (data.success && data.clv_prediction) {
        const cp = data.clv_prediction;
        return {
            success: true,
            customer_id: cp.customer_id,
            predicted_clv: cp.predicted_clv,
            formatted: cp.predicted_clv_formatted,
            tier: cp.clv_tier,
            color: cp.clv_color,
            action: cp.recommended_action,
            context: cp.context,
            model_used: cp.model_used,
        };
    }
    return data;
}

// GET /api/customers/:id/behavior
export async function getBehavior(id) {
    const response = await api.get(`/api/customers/${id}/behavior`);
    return response.data;
}

// GET /api/customers/:id/segment
export async function getSegment(id) {
    const response = await api.get(`/api/customers/${id}/segment`);
    return response.data;
}

// GET /api/customers/:id/insights
export async function getInsights(id) {
    const response = await api.get(`/api/customers/${id}/insights`);
    return response.data;
}
