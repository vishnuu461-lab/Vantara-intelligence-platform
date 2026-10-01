# ============================================================
# services/anomaly_service.py — Anomaly Detection
# ============================================================
# Detects anomalous customer spending/behaviour using
# Isolation Forest (sklearn) — a genuine unsupervised detector.
#
# NOTE: An Autoencoder (TF/Keras) variant is in
#       ml/train_autoencoder.py. This service uses Isolation
#       Forest as the production runtime (no GPU needed,
#       fast inference, well-validated threshold).
#
# FEATURES USED:
#   total_spend, total_orders, average_order_value,
#   website_visits, complaints, days_since_last_purchase
# ============================================================

import os
import numpy as np
import logging
from datetime import date

logger = logging.getLogger(__name__)

# ── Lazy-loaded model ──────────────────────────────────────

_iso_model = None

def _get_model():
    """Return a fitted Isolation Forest, training on-the-fly if needed."""
    global _iso_model
    if _iso_model is None:
        _iso_model = _train_isolation_forest()
    return _iso_model


def _build_feature_matrix():
    """Build feature matrix from all customers for training."""
    from models.customer import Customer
    customers = Customer.query.all()
    if not customers:
        return np.array([]).reshape(0, 6), []

    X, ids = [], []
    today = date.today()
    for c in customers:
        last = (today - c.last_purchase_date).days if c.last_purchase_date else 9999
        X.append([
            c.total_orders or 0,
            c.total_spend or 0.0,
            c.average_order_value or 0.0,
            c.website_visits or 0,
            c.complaints or 0,
            last,
        ])
        ids.append(c.customer_id)
    return np.array(X, dtype=float), ids


def _train_isolation_forest():
    """Train Isolation Forest on all customer features."""
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler

    X, _ = _build_feature_matrix()
    if len(X) < 5:
        return None

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    iso = IsolationForest(
        n_estimators=100,
        contamination=0.05,   # expect ~5% anomalies
        random_state=42,
    )
    iso.fit(X_scaled)
    # Store scaler inside the model object for convenience
    iso._vantara_scaler = scaler
    return iso


# ── Public API ─────────────────────────────────────────────

def get_anomaly_score(customer_id: str) -> dict:
    """
    Compute anomaly score for a single customer.

    Returns:
        {
          customer_id, name,
          anomaly_score (0-100, higher = more anomalous),
          is_anomaly (bool),
          anomaly_flag ("ANOMALY" | "NORMAL"),
          features_used,
          explanation
        }
    """
    from models.customer import Customer
    from extensions import db

    customer = db.session.get(Customer, customer_id)
    if not customer:
        return {"error": f"Customer {customer_id} not found"}

    try:
        model = _get_model()
        if model is None:
            return {"error": "Not enough data to build anomaly model (need ≥ 5 customers)"}

        today = date.today()
        last = (today - customer.last_purchase_date).days if customer.last_purchase_date else 9999

        feat = np.array([[
            customer.total_orders or 0,
            customer.total_spend or 0.0,
            customer.average_order_value or 0.0,
            customer.website_visits or 0,
            customer.complaints or 0,
            last,
        ]], dtype=float)

        scaler = model._vantara_scaler
        feat_scaled = scaler.transform(feat)

        # Raw score: negative = anomaly, positive = normal
        raw_score = float(model.score_samples(feat_scaled)[0])
        prediction = int(model.predict(feat_scaled)[0])  # -1 = anomaly, 1 = normal

        # Normalise to 0-100 (anomaly score; higher = stranger)
        # Typical range for IsolationForest scores: [-0.5, 0.5]
        anomaly_score = round(max(0.0, min(100.0, (-raw_score + 0.3) * 200)), 1)
        is_anomaly = prediction == -1

        explanation = _build_anomaly_explanation(customer, is_anomaly, anomaly_score)

        return {
            "customer_id":    customer_id,
            "name":           customer.name,
            "anomaly_score":  anomaly_score,
            "is_anomaly":     is_anomaly,
            "anomaly_flag":   "ANOMALY" if is_anomaly else "NORMAL",
            "raw_score":      round(raw_score, 4),
            "features_used": {
                "total_orders":          customer.total_orders or 0,
                "total_spend":           customer.total_spend or 0.0,
                "average_order_value":   customer.average_order_value or 0.0,
                "website_visits":        customer.website_visits or 0,
                "complaints":            customer.complaints or 0,
                "days_since_last_purchase": last,
            },
            "explanation": explanation,
        }

    except Exception as e:
        logger.error(f"Anomaly detection failed for {customer_id}: {e}")
        return {"error": str(e)}


def get_all_anomalies() -> dict:
    """Return anomaly status for all customers, sorted by score."""
    from models.customer import Customer
    customers = Customer.query.all()

    results = []
    for c in customers:
        r = get_anomaly_score(c.customer_id)
        if "error" not in r:
            results.append(r)

    results.sort(key=lambda x: x["anomaly_score"], reverse=True)
    anomalies = [r for r in results if r["is_anomaly"]]

    return {
        "total_customers":  len(results),
        "anomaly_count":    len(anomalies),
        "anomaly_rate":     round(len(anomalies) / len(results) * 100, 1) if results else 0,
        "customers":        results,
        "top_anomalies":    anomalies[:10],
    }


def _build_anomaly_explanation(customer, is_anomaly: bool, score: float) -> str:
    """Plain-language anomaly explanation."""
    name = customer.name.split()[0]
    if is_anomaly:
        reasons = []
        if (customer.total_spend or 0) > 100000:
            reasons.append("unusually high total spend")
        if (customer.complaints or 0) >= 3:
            reasons.append("high number of complaints")
        if (customer.total_orders or 0) == 0:
            reasons.append("no purchase history despite being registered")
        if not reasons:
            reasons.append("an unusual combination of activity metrics")
        return (
            f"{name} is flagged as an anomaly (score: {score}/100) due to "
            + " and ".join(reasons)
            + ". This warrants manual review."
        )
    else:
        return f"{name} displays normal behaviour patterns (anomaly score: {score}/100)."
