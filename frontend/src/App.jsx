// ============================================================
// App.jsx — Root component with routing
// ============================================================

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { useState, useEffect } from 'react';
import './index.css';
import api from './api/axios';

import Sidebar from './components/layout/Sidebar';
import Dashboard from './pages/Dashboard';
import Customers from './pages/Customers';
import CustomerDetail from './pages/CustomerDetail';
import ChurnPage from './pages/ChurnPage';
import CLVPage from './pages/CLVPage';
import BehaviorPage from './pages/BehaviorPage';
import SegmentsPage from './pages/SegmentsPage';
import InsightsPage from './pages/InsightsPage';
import UploadPage from './pages/UploadPage';

export default function App() {
  const [waking, setWaking] = useState(false);

  useEffect(() => {
    // Check if backend responds quickly — if not, show a wake-up banner
    const timer = setTimeout(() => setWaking(true), 3000); // show banner after 3s
    api.get('/api/health', { timeout: 65000 })
      .then(() => { clearTimeout(timer); setWaking(false); })
      .catch(() => { clearTimeout(timer); setWaking(false); });
    return () => clearTimeout(timer);
  }, []);

  return (
    <BrowserRouter>
      <div className="app-shell">

        {/* Wake-up banner — shown when Render is cold-starting */}
        {waking && (
          <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, zIndex: 9999,
            background: 'linear-gradient(90deg, #f59e0b, #d97706)',
            color: 'white', textAlign: 'center',
            padding: '10px 16px', fontSize: 13, fontWeight: 600,
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
          }}>
            <span>⏳</span>
            Server is waking up (free hosting sleeps after 15 min of inactivity).
            Pages will load in ~30–60 seconds. Please wait…
          </div>
        )}

        {/* Sidebar — always visible */}
        <Sidebar />

        {/* Main content — changes based on URL */}
        <main className="main-content" style={{ marginTop: waking ? 42 : 0 }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/customers" element={<Customers />} />
            <Route path="/customers/:id" element={<CustomerDetail />} />
            <Route path="/churn" element={<ChurnPage />} />
            <Route path="/clv" element={<CLVPage />} />
            <Route path="/behavior" element={<BehaviorPage />} />
            <Route path="/segments" element={<SegmentsPage />} />
            <Route path="/insights" element={<InsightsPage />} />
            <Route path="/upload" element={<UploadPage />} />
          </Routes>
        </main>

      </div>
    </BrowserRouter>
  );
}
