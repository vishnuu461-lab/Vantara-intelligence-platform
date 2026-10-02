// ============================================================
// api/axios.js — Centralized Axios Instance
// ============================================================
// VITE_API_URL is set via:
//   - Local dev:  frontend/.env  → http://localhost:5000
//   - Production: Vercel env var → https://vantara-ai-intelligence-platform.onrender.com
//
// The fallback URL ensures the deployed site always works
// even if the Vercel env var is not picked up in the build.
// ============================================================

import axios from 'axios';

// Determine the correct backend URL:
// 1. Use VITE_API_URL env var if available (set in Vercel dashboard)
// 2. If running on localhost → use local Flask server
// 3. Otherwise → use the deployed Render backend
const getBaseURL = () => {
    if (import.meta.env.VITE_API_URL) {
        return import.meta.env.VITE_API_URL;
    }
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        return 'http://localhost:5000';
    }
    // Production fallback — always points to Render backend
    return 'https://vantara-ai-intelligence-platform.onrender.com';
};

const api = axios.create({
    baseURL: getBaseURL(),
    timeout: 30000,   // 30 seconds — extra time for Render cold start wake-up
    headers: {
        'Content-Type': 'application/json',
    },
});

export default api;
