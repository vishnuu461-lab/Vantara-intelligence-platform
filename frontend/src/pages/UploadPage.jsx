// ============================================================
// UploadPage.jsx — CSV Customer Data Upload
// ============================================================
// API: POST /api/upload   (multipart/form-data, key = "file")
//
// Response:
//   { success, message, report: { total_rows_in_csv, valid_rows,
//     inserted, duplicates_skipped, invalid_skipped, errors },
//     inserted_customers[], duplicates[], skipped_rows[],
//     warnings[], insert_errors[] }
//
// Features:
//   - Drag-and-drop zone + click-to-browse
//   - CSV template download (hardcoded)
//   - Live upload with progress state
//   - Detailed results panel with tabs
//   - Instructions & required columns reference
// ============================================================

import { useState, useRef, useCallback } from 'react';
import Navbar from '../components/layout/Navbar';
import api from '../api/axios';

// ── CSV template the user can download ─────────────────────

const TEMPLATE_HEADER = 'customer_id,name,age,gender,location,email,total_orders,total_spend,average_order_value,last_purchase_date,website_visits,complaints,subscription_status';
const TEMPLATE_ROWS = [
  TEMPLATE_HEADER,
  'C2001,Sample User,28,Female,Mumbai,sample@email.com,12,25000,2083,2024-06-15,45,0,Active',
  'C2002,Another User,35,Male,Delhi,another@email.com,5,8500,1700,2024-03-01,20,1,Inactive',
];
const TEMPLATE_TEXT = TEMPLATE_ROWS.join('\r\n');

// Download as .csv (needs Excel or similar installed)
function downloadCSV() {
  const blob = new Blob(['\uFEFF' + TEMPLATE_TEXT], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'vantara_customers_template.csv'; a.click();
  URL.revokeObjectURL(url);
}

// Download as .txt — opens in Notepad on any Windows machine
function downloadTXT() {
  const blob = new Blob([TEMPLATE_TEXT], { type: 'text/plain;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'vantara_customers_template.txt'; a.click();
  URL.revokeObjectURL(url);
}

// Copy raw CSV text to clipboard
async function copyToClipboard() {
  await navigator.clipboard.writeText(TEMPLATE_TEXT);
}

// ── Upload function ─────────────────────────────────────────

async function uploadCSV(file) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await api.post('/api/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
}

// ── Helpers ─────────────────────────────────────────────────

function SectionCard({ title, items, emptyMsg, colorClass, keyField = 'customer_id' }) {
  if (!items?.length) return (
    <div style={{
      padding: '16px', borderRadius: 'var(--radius)',
      background: '#f8fafc', color: 'var(--text-muted)',
      fontSize: 12, textAlign: 'center'
    }}>
      {emptyMsg}
    </div>
  );
  return (
    <div>
      <div style={{
        fontWeight: 600, fontSize: 12, color: 'var(--text-secondary)',
        textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 8
      }}>
        {title} ({items.length})
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {items.slice(0, 20).map((item, i) => (
          <div key={i} style={{
            padding: '8px 12px', borderRadius: 'var(--radius)',
            background: colorClass === 'green' ? 'var(--success-light)' :
              colorClass === 'amber' ? 'var(--warning-light)' :
                'var(--danger-light)',
            fontSize: 12, display: 'flex', gap: 8,
          }}>
            <span style={{
              fontWeight: 700,
              color: colorClass === 'green' ? '#059669' :
                colorClass === 'amber' ? '#d97706' : '#dc2626',
            }}>
              {item[keyField] || item.row_number || item.customer_id || `#${i + 1}`}
            </span>
            <span style={{ color: 'var(--text-secondary)' }}>
              {item.name && `${item.name} · `}
              {item.reason || item.error || item.message || ''}
            </span>
          </div>
        ))}
        {items.length > 20 && (
          <div style={{ fontSize: 11, color: 'var(--text-muted)', textAlign: 'center' }}>
            + {items.length - 20} more…
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────

export default function UploadPage() {
  const [dragOver, setDragOver] = useState(false);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);   // last upload result
  const [errMsg, setErrMsg] = useState('');
  const [activeTab, setActiveTab] = useState('inserted');
  const [showPreview, setShowPreview] = useState(false);
  const [copied, setCopied] = useState(false);

  const inputRef = useRef(null);

  const handleCopy = async () => {
    await copyToClipboard();
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleFile = useCallback((f) => {
    if (!f) return;
    if (!f.name.endsWith('.csv')) {
      setErrMsg('Only .csv files are allowed.');
      return;
    }
    setFile(f);
    setResult(null);
    setErrMsg('');
  }, []);

  // Drag events
  const onDragOver = (e) => { e.preventDefault(); setDragOver(true); };
  const onDragLeave = () => setDragOver(false);
  const onDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files?.[0];
    if (f) handleFile(f);
  };

  // Upload
  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setErrMsg('');
    setResult(null);
    try {
      const data = await uploadCSV(file);
      setResult(data);
      setActiveTab(
        data.report?.inserted > 0 ? 'inserted' :
          data.report?.duplicates_skipped > 0 ? 'duplicates' : 'skipped'
      );
    } catch (err) {
      const msg = err.response?.data?.error || err.response?.data?.message || err.message;
      setErrMsg(msg || 'Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const reset = () => {
    setFile(null);
    setResult(null);
    setErrMsg('');
    if (inputRef.current) inputRef.current.value = '';
  };

  // ── Render ───────────────────────────────────────────────
  return (
    <>
      <Navbar
        pageTitle="Data Upload"
        pageSubtitle="Import customer records from CSV"
      />

      <div className="page-body">

        {/* Header */}
        <div className="page-header">
          <div>
            <h1>Import Customer Data</h1>
            <p>Upload a CSV file to add new customers to the Vantara database</p>
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button className="btn btn-outline btn-sm" onClick={downloadCSV}>
              ⬇️ Download .csv
            </button>
            <button className="btn btn-outline btn-sm" onClick={downloadTXT}>
              📄 Download .txt
            </button>
            <button className="btn btn-outline btn-sm" onClick={handleCopy}>
              {copied ? '✅ Copied!' : '📋 Copy template'}
            </button>
            <button className="btn btn-outline btn-sm"
              onClick={() => setShowPreview(v => !v)}>
              {showPreview ? '🔼 Hide preview' : '🔍 Preview template'}
            </button>
          </div>
        </div>

        {/* Template preview panel */}
        {showPreview && (
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-header">
              <div>
                <div className="card-title">📄 CSV Template Preview</div>
                <div className="card-subtitle">Copy this content into any text editor and save as customers.csv</div>
              </div>
              <button className="btn btn-outline btn-sm" onClick={handleCopy}>
                {copied ? '✅ Copied!' : '📋 Copy all'}
              </button>
            </div>
            <div className="card-body" style={{ padding: 0 }}>
              <pre style={{
                fontFamily: 'Consolas, monospace',
                fontSize: 11,
                background: '#0f172a',
                color: '#a5b4fc',
                padding: '20px 24px',
                overflowX: 'auto',
                margin: 0,
                lineHeight: 1.7,
                userSelect: 'all',
              }}>
                {TEMPLATE_ROWS.map((row, i) => (
                  <div key={i} style={{ color: i === 0 ? '#f8fafc' : '#94a3b8' }}>
                    {row}
                  </div>
                ))}
              </pre>
              <div style={{
                padding: '10px 24px', fontSize: 11,
                color: 'var(--text-muted)', borderTop: '1px solid var(--border)'
              }}>
                💡 Tip: Click <strong>"Copy all"</strong> above → open Notepad → paste → File → Save As → change extension to <strong>.csv</strong>
              </div>
            </div>
          </div>
        )}

        <div className="grid-2" style={{ alignItems: 'start' }}>

          {/* ── LEFT: Drop zone + controls ── */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

            {/* Drag-and-drop zone */}
            <div className="card">
              <div className="card-header">
                <div>
                  <div className="card-title">📂 Upload CSV File</div>
                  <div className="card-subtitle">Drag & drop or click to browse</div>
                </div>
              </div>
              <div className="card-body">

                {/* Drop zone */}
                <div
                  onClick={() => inputRef.current?.click()}
                  onDragOver={onDragOver}
                  onDragLeave={onDragLeave}
                  onDrop={onDrop}
                  style={{
                    border: `2px dashed ${dragOver
                      ? 'var(--primary)' : file ? 'var(--success)' : 'var(--border)'}`,
                    borderRadius: 'var(--radius-lg)',
                    background: dragOver
                      ? 'var(--primary-light)' : file ? 'var(--success-light)' : '#f8fafc',
                    padding: '40px 24px',
                    textAlign: 'center',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                  }}
                >
                  <div style={{ fontSize: 40, marginBottom: 12 }}>
                    {file ? '✅' : dragOver ? '📂' : '📤'}
                  </div>
                  {file ? (
                    <>
                      <div style={{ fontWeight: 600, color: 'var(--success)', fontSize: 14 }}>
                        {file.name}
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                        {(file.size / 1024).toFixed(1)} KB · Click to change file
                      </div>
                    </>
                  ) : (
                    <>
                      <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: 14 }}>
                        {dragOver ? 'Drop CSV here!' : 'Drag & drop your CSV file here'}
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                        or click to browse · Max 5 MB · .csv files only
                      </div>
                    </>
                  )}
                </div>
                <input ref={inputRef} type="file" accept=".csv"
                  style={{ display: 'none' }}
                  onChange={e => handleFile(e.target.files?.[0])} />

                {/* Error message */}
                {errMsg && (
                  <div style={{
                    marginTop: 14, padding: '10px 14px', borderRadius: 'var(--radius)',
                    background: 'var(--danger-light)', borderLeft: '3px solid var(--danger)',
                    color: '#dc2626', fontSize: 13,
                  }}>
                    ❌ {errMsg}
                  </div>
                )}

                {/* Action buttons */}
                <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
                  <button
                    className="btn btn-primary"
                    style={{ flex: 1 }}
                    disabled={!file || uploading}
                    onClick={handleUpload}
                  >
                    {uploading
                      ? '⏳ Uploading...'
                      : file
                        ? `🚀 Upload "${file.name}"`
                        : '📤 Select a file first'}
                  </button>
                  {(file || result) && (
                    <button className="btn btn-outline" onClick={reset}>✕ Reset</button>
                  )}
                </div>
              </div>
            </div>

            {/* Required Columns Reference */}
            <div className="card">
              <div className="card-header">
                <div className="card-title">📋 Required CSV Columns</div>
              </div>
              <div className="card-body">
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {[
                    { col: 'customer_id', req: true, type: 'string', note: 'Unique ID e.g. C2001' },
                    { col: 'name', req: true, type: 'string', note: 'Full name' },
                    { col: 'age', req: false, type: 'number', note: 'Integer' },
                    { col: 'gender', req: false, type: 'string', note: 'Male / Female / Other' },
                    { col: 'location', req: false, type: 'string', note: 'City name' },
                    { col: 'email', req: false, type: 'string', note: 'Valid email' },
                    { col: 'total_orders', req: false, type: 'number', note: 'Integer' },
                    { col: 'total_spend', req: false, type: 'number', note: 'Decimal ₹' },
                    { col: 'average_order_value', req: false, type: 'number', note: 'Auto-calculated if blank' },
                    { col: 'last_purchase_date', req: false, type: 'date', note: 'YYYY-MM-DD' },
                    { col: 'website_visits', req: false, type: 'number', note: 'Integer' },
                    { col: 'complaints', req: false, type: 'number', note: 'Integer' },
                    { col: 'subscription_status', req: false, type: 'string', note: 'Active / Inactive / Premium / Cancelled' },
                  ].map(({ col, req, type, note }) => (
                    <div key={col} style={{
                      display: 'flex', alignItems: 'center', gap: 10,
                      padding: '5px 0', borderBottom: '1px solid #f1f5f9',
                    }}>
                      <span style={{
                        fontFamily: 'monospace', fontSize: 12, fontWeight: 600,
                        color: 'var(--primary)', minWidth: 160,
                      }}>{col}</span>
                      <span className={`badge ${req ? 'badge-red' : 'badge-gray'}`}
                        style={{ fontSize: 9 }}>
                        {req ? 'REQUIRED' : 'optional'}
                      </span>
                      <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                        {type} · {note}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

          </div>

          {/* ── RIGHT: Results panel ── */}
          <div>
            {/* Idle / uploading state */}
            {!result && !uploading && (
              <div className="card">
                <div className="card-body">
                  <div className="state-center">
                    <div className="state-icon">📊</div>
                    <div className="state-title">No upload yet</div>
                    <div className="state-desc">
                      Upload a CSV file to see the import results here.<br />
                      Download the template to get started quickly.
                    </div>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center' }}>
                      <button className="btn btn-outline btn-sm" onClick={downloadCSV}>⬇️ .csv</button>
                      <button className="btn btn-outline btn-sm" onClick={downloadTXT}>📄 .txt</button>
                      <button className="btn btn-outline btn-sm" onClick={handleCopy}>
                        {copied ? '✅ Copied!' : '📋 Copy'}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {uploading && (
              <div className="card">
                <div className="card-body">
                  <div className="state-center">
                    <div className="spinner" />
                    <div className="state-title">Uploading & processing…</div>
                    <div className="state-desc">
                      Validating rows, checking for duplicates,<br />
                      and inserting into MySQL…
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Results */}
            {result && !uploading && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

                {/* Summary banner */}
                <div style={{
                  padding: '20px 24px',
                  borderRadius: 'var(--radius-lg)',
                  background: result.success ? 'var(--success-light)' : 'var(--warning-light)',
                  border: `1px solid ${result.success ? '#a7f3d0' : '#fde68a'}`,
                }}>
                  <div style={{
                    fontSize: 15, fontWeight: 700,
                    color: result.success ? '#059669' : '#d97706', marginBottom: 6
                  }}>
                    {result.success ? '✅ Import Successful!' : '⚠️ Import Completed with Warnings'}
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                    {result.message}
                  </div>
                </div>

                {/* Report stat cards */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(3, 1fr)',
                  gap: 12,
                }}>
                  {[
                    { label: 'Total in CSV', val: result.report?.total_rows_in_csv, color: '#3b82f6', icon: '📄' },
                    { label: 'Inserted', val: result.report?.inserted, color: '#10b981', icon: '✅' },
                    { label: 'Duplicates', val: result.report?.duplicates_skipped, color: '#f59e0b', icon: '🔁' },
                    { label: 'Invalid rows', val: result.report?.invalid_skipped, color: '#ef4444', icon: '❌' },
                    { label: 'Valid rows', val: result.report?.valid_rows, color: '#8b5cf6', icon: '✔️' },
                    { label: 'Errors', val: result.report?.errors, color: '#dc2626', icon: '⚠️' },
                  ].map(({ label, val, color, icon }) => (
                    <div key={label} style={{
                      padding: '12px 14px', borderRadius: 'var(--radius)',
                      background: 'white', border: '1px solid var(--border)',
                      textAlign: 'center',
                    }}>
                      <div style={{ fontSize: 18 }}>{icon}</div>
                      <div style={{ fontSize: 20, fontWeight: 700, color, marginTop: 4 }}>
                        {val ?? 0}
                      </div>
                      <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>
                        {label}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Tabbed detail sections */}
                <div className="card">
                  {/* Tabs */}
                  <div style={{
                    display: 'flex', borderBottom: '1px solid var(--border)',
                    overflowX: 'auto',
                  }}>
                    {[
                      { key: 'inserted', label: `✅ Inserted (${result.inserted_customers?.length ?? 0})` },
                      { key: 'duplicates', label: `🔁 Duplicates (${result.duplicates?.length ?? 0})` },
                      { key: 'skipped', label: `❌ Skipped (${result.skipped_rows?.length ?? 0})` },
                      { key: 'warnings', label: `⚠️ Warnings (${result.warnings?.length ?? 0})` },
                    ].map(tab => (
                      <button key={tab.key}
                        onClick={() => setActiveTab(tab.key)}
                        style={{
                          padding: '10px 16px', fontSize: 12, fontWeight: 600,
                          border: 'none', background: 'none', cursor: 'pointer',
                          borderBottom: `2px solid ${activeTab === tab.key ? 'var(--primary)' : 'transparent'}`,
                          color: activeTab === tab.key ? 'var(--primary)' : 'var(--text-secondary)',
                          whiteSpace: 'nowrap',
                          transition: 'all 0.15s',
                        }}>
                        {tab.label}
                      </button>
                    ))}
                  </div>

                  <div className="card-body">
                    {activeTab === 'inserted' && (
                      <SectionCard
                        title="Successfully Inserted"
                        items={result.inserted_customers}
                        emptyMsg="No customers were inserted."
                        colorClass="green"
                      />
                    )}
                    {activeTab === 'duplicates' && (
                      <SectionCard
                        title="Skipped — Already Exists"
                        items={result.duplicates}
                        emptyMsg="No duplicates found — all IDs were new!"
                        colorClass="amber"
                      />
                    )}
                    {activeTab === 'skipped' && (
                      <SectionCard
                        title="Invalid Rows Skipped"
                        items={result.skipped_rows}
                        emptyMsg="No rows were skipped — data looks clean!"
                        colorClass="red"
                        keyField="row_number"
                      />
                    )}
                    {activeTab === 'warnings' && (
                      <SectionCard
                        title="Warnings"
                        items={result.warnings?.map(w =>
                          typeof w === 'string' ? { message: w } : w
                        )}
                        emptyMsg="No warnings — clean import!"
                        colorClass="amber"
                        keyField="message"
                      />
                    )}
                  </div>
                </div>

              </div>
            )}
          </div>

        </div>
      </div>
    </>
  );
}
