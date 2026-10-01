// ============================================================
// App.jsx — Root component with routing
// ============================================================
// BrowserRouter  = enables URL-based navigation
// Routes / Route = maps each URL path to a page component
// Sidebar        = stays visible on every page
// ============================================================

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import './index.css';

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
  return (
    <BrowserRouter>
      <div className="app-shell">

        {/* Sidebar — always visible on the left */}
        <Sidebar />

        {/* Main content — changes based on URL */}
        <main className="main-content">
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
