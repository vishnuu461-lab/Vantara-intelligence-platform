// ============================================================
// DetailDrawer.jsx — Reusable slide-in detail panel
// ============================================================
// Opens a right-side drawer over the current page so the user
// stays within their current feature section.
// Backdrop click also closes the drawer.
// ============================================================

import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

export default function DetailDrawer({ open, onClose, title, subtitle, customerId, children }) {
    const navigate = useNavigate();

    // Lock body scroll while drawer is open
    useEffect(() => {
        document.body.style.overflow = open ? 'hidden' : '';
        return () => { document.body.style.overflow = ''; };
    }, [open]);

    // Close on Escape key
    useEffect(() => {
        if (!open) return;
        const handler = (e) => { if (e.key === 'Escape') onClose(); };
        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, [open, onClose]);

    if (!open) return null;

    return (
        <>
            {/* Backdrop */}
            <div
                onClick={onClose}
                style={{
                    position: 'fixed', inset: 0,
                    background: 'rgba(15, 23, 42, 0.45)',
                    backdropFilter: 'blur(3px)',
                    zIndex: 300,
                }}
            />

            {/* Drawer panel */}
            <div style={{
                position: 'fixed', top: 0, right: 0, bottom: 0,
                width: 'min(500px, 94vw)',
                background: 'var(--bg-card, #fff)',
                borderLeft: '1px solid var(--border, #e2e8f0)',
                boxShadow: '-12px 0 40px rgba(0,0,0,0.18)',
                zIndex: 301,
                display: 'flex',
                flexDirection: 'column',
                animation: 'drawerSlideIn 0.22s cubic-bezier(0.16, 1, 0.3, 1)',
            }}>

                {/* ── Drawer Header ── */}
                <div style={{
                    padding: '18px 24px',
                    borderBottom: '1px solid var(--border, #e2e8f0)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    flexShrink: 0,
                }}>
                    <div>
                        <div style={{ fontWeight: 700, fontSize: 17, color: 'var(--text-primary, #0f172a)' }}>
                            {title}
                        </div>
                        {subtitle && (
                            <div style={{ fontSize: 12, color: 'var(--text-muted, #94a3b8)', marginTop: 3 }}>
                                {subtitle}
                            </div>
                        )}
                    </div>
                    <button
                        onClick={onClose}
                        title="Close (Esc)"
                        style={{
                            background: 'var(--bg-surface, #f8fafc)',
                            border: '1px solid var(--border, #e2e8f0)',
                            borderRadius: 8, width: 32, height: 32,
                            cursor: 'pointer', fontSize: 16,
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            color: 'var(--text-secondary, #64748b)',
                            flexShrink: 0, marginLeft: 12,
                        }}
                    >
                        ✕
                    </button>
                </div>

                {/* ── Scrollable Content ── */}
                <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px' }}>
                    {children}
                </div>

                {/* ── Footer: explicit cross-section link ── */}
                {customerId && (
                    <div style={{
                        padding: '14px 24px',
                        borderTop: '1px solid var(--border, #e2e8f0)',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        flexShrink: 0,
                        background: 'var(--bg-surface, #f8fafc)',
                    }}>
                        <span style={{ fontSize: 12, color: 'var(--text-muted, #94a3b8)' }}>
                            {customerId}
                        </span>
                        <button
                            className="btn btn-outline btn-sm"
                            onClick={() => { onClose(); navigate(`/customers/${customerId}`); }}
                        >
                            👤 View Full Customer Profile →
                        </button>
                    </div>
                )}
            </div>
        </>
    );
}
