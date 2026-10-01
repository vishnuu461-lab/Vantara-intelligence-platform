// ============================================================
// Navbar.jsx — Top navigation bar
// ============================================================
// Shows the current page title and a backend status indicator.
// Receives pageTitle and pageSubtitle as props from each page.
// ============================================================

export default function Navbar({ pageTitle, pageSubtitle }) {
    return (
        <header className="navbar">

            {/* Left: Current page title */}
            <div className="navbar-left">
                <div className="page-title">{pageTitle || 'Vantara'}</div>
                {pageSubtitle && (
                    <div className="page-subtitle">{pageSubtitle}</div>
                )}
            </div>

            {/* Right: Status + User */}
            <div className="navbar-right">
                <div className="status-dot">Backend Connected</div>
                <div className="avatar">V</div>
            </div>

        </header>
    );
}
