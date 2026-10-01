// ============================================================
// api/axios.js — Centralized Axios Instance
// ============================================================
// Instead of writing "http://localhost:5000" everywhere,
// we create ONE axios instance with the base URL set once.
//
// import api from './axios'
// api.get('/api/dashboard')  ← automatically hits localhost:5000
//
// VITE_API_URL comes from the .env file we created:
//   VITE_API_URL=http://localhost:5000
// ============================================================

import axios from 'axios';

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:5000',
    timeout: 15000,   // 15 seconds — cancel if backend takes too long
    headers: {
        'Content-Type': 'application/json',
    },
});

export default api;
