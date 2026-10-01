// ErrorMessage — shown when a backend API call fails
export default function ErrorMessage({ message, onRetry }) {
    return (
        <div className="state-center">
            <div className="state-icon">⚠️</div>
            <div className="state-title">Something went wrong</div>
            <div className="state-desc">{message || 'Unable to load data. Is the backend running?'}</div>
            {onRetry && (
                <button className="btn btn-outline" style={{ marginTop: 12 }} onClick={onRetry}>
                    Try Again
                </button>
            )}
        </div>
    );
}
