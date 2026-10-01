// ============================================================
// api/predictionApi.js — Prediction & Analysis API calls
// ============================================================

import api from './axios';

// GET /api/segments — All customers segmented into 5 groups
export async function getAllSegments() {
    const response = await api.get('/api/segments');
    return response.data;
}

// GET /api/analysis/summary — Aggregate stats across all customers
export async function getAnalysisSummary() {
    const response = await api.get('/api/analysis/summary');
    return response.data;
}
