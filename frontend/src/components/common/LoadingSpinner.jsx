// LoadingSpinner — shown while data is being fetched from backend
export default function LoadingSpinner({ message = 'Loading data...' }) {
    return (
        <div className="state-center">
            <div className="spinner"></div>
            <div className="state-desc">{message}</div>
        </div>
    );
}
