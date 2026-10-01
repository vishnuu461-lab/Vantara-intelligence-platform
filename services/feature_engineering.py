# ============================================================
# services/feature_engineering.py — Customer Feature Store
# ============================================================
# Computes all customer-level features for ML models.
# Respects point-in-time cutoff to prevent target leakage.
#
# FEATURES COMPUTED:
#   RFM:        recency, frequency, monetary
#   Spend:      total_spend, avg_spend, historical_clv
#   Trend:      purchase_freq_trend, avg_interval_days,
#               interval_variance, seasonal_concentration
#   Affinity:   top_category, category_count, return_rate
#   Engagement: website_visits, complaints, discount_sensitivity,
#               engagement_score, avg_basket_size
# ============================================================

import numpy as np
from datetime import date
from sqlalchemy import func
from models.customer import Customer
from models.purchase import Purchase
from extensions import db


# ── Point-in-time cutoff ───────────────────────────────────

def get_features_for_customer(customer_id: str, cutoff_date: date = None) -> dict | None:
    """
    Compute the full feature vector for a single customer.

    Args:
        customer_id: e.g. "C1001"
        cutoff_date: only use data on/before this date (leakage prevention).
                     Defaults to today.

    Returns:
        Feature dict or None if customer not found.
    """
    customer = db.session.get(Customer, customer_id)
    if not customer:
        return None

    cutoff = cutoff_date or date.today()

    # Fetch all purchases up to cutoff
    purchases = Purchase.query.filter(
        Purchase.customer_id == customer_id,
        Purchase.purchase_date <= cutoff
    ).order_by(Purchase.purchase_date.asc()).all()

    # ── RFM ───────────────────────────────────────────────

    # Recency (days since last purchase before cutoff)
    purchase_dates = [p.purchase_date for p in purchases if p.purchase_date]
    if purchase_dates:
        last_date = max(purchase_dates)
        recency_days = (cutoff - last_date).days
    else:
        recency_days = 9999  # Never purchased

    frequency = len(purchases)
    monetary = sum(p.amount for p in purchases if p.amount) if purchases else 0.0

    # ── Spend metrics ──────────────────────────────────────

    avg_spend = (monetary / frequency) if frequency > 0 else 0.0

    # Historical CLV: total spend * (1 + frequency/10) heuristic
    historical_clv = monetary * (1 + frequency / 10.0)

    # ── Time-gap / interval features ──────────────────────

    if len(purchase_dates) >= 2:
        gaps = [(purchase_dates[i] - purchase_dates[i-1]).days
                for i in range(1, len(purchase_dates))]
        avg_interval_days   = float(np.mean(gaps))
        interval_variance   = float(np.var(gaps))
        min_gap             = float(np.min(gaps))
        max_gap             = float(np.max(gaps))
    else:
        avg_interval_days   = 0.0
        interval_variance   = 0.0
        min_gap             = 0.0
        max_gap             = 0.0

    # Purchase frequency trend:
    # Compare orders in last 90 days vs 90-180 days ago
    recent_90  = [p for p in purchases
                  if p.purchase_date and (cutoff - p.purchase_date).days <= 90]
    prior_90   = [p for p in purchases
                  if p.purchase_date and 90 < (cutoff - p.purchase_date).days <= 180]
    freq_trend = len(recent_90) - len(prior_90)  # positive = growing

    # ── Seasonal concentration ─────────────────────────────
    # What fraction of orders fall in the customer's top quarter?
    if purchase_dates:
        quarters = [((d.month - 1) // 3) + 1 for d in purchase_dates]
        from collections import Counter
        q_counts = Counter(quarters)
        top_q_count = max(q_counts.values())
        seasonal_concentration = top_q_count / len(purchase_dates)
    else:
        seasonal_concentration = 0.0

    # ── Category affinity ─────────────────────────────────

    if purchases:
        cat_result = db.session.query(
            Purchase.product_category,
            func.count(Purchase.purchase_id).label("cnt")
        ).filter(
            Purchase.customer_id == customer_id,
            Purchase.purchase_date <= cutoff
        ).group_by(Purchase.product_category).order_by(
            func.count(Purchase.purchase_id).desc()
        ).first()
        top_category = cat_result[0] if cat_result else "N/A"

        all_cat_result = db.session.query(
            func.count(func.distinct(Purchase.product_category))
        ).filter(
            Purchase.customer_id == customer_id,
            Purchase.purchase_date <= cutoff
        ).scalar()
        category_count = all_cat_result or 0
    else:
        top_category   = "N/A"
        category_count = 0

    # ── Return rate ────────────────────────────────────────
    # Negative-amount purchases treated as returns
    returns = [p for p in purchases if p.amount and p.amount < 0]
    return_rate = len(returns) / frequency if frequency > 0 else 0.0

    # ── Engagement score (0-100, composite) ───────────────
    visits    = customer.website_visits or 0
    complaints = customer.complaints or 0

    # Normalised sub-scores (clamped 0-1)
    visit_score     = min(visits / 100.0, 1.0)
    recency_score   = max(1.0 - recency_days / 365.0, 0.0)
    freq_score      = min(frequency / 20.0, 1.0)
    complaint_pen   = min(complaints / 5.0, 1.0)

    engagement_score = round(
        (visit_score * 25 + recency_score * 35 + freq_score * 30 - complaint_pen * 10),
        2
    )
    engagement_score = max(0.0, min(100.0, engagement_score))

    # ── Average basket size ────────────────────────────────
    avg_basket_size = avg_spend  # proxy (same as avg_spend here)

    # ── Subscription flag ──────────────────────────────────
    sub_active = 1 if (customer.subscription_status or "").lower() in (
        "active", "premium"
    ) else 0

    return {
        "customer_id":             customer_id,
        "cutoff_date":             cutoff.isoformat(),
        # RFM
        "recency_days":            recency_days,
        "frequency":               frequency,
        "monetary":                round(monetary, 2),
        # Spend
        "avg_spend":               round(avg_spend, 2),
        "historical_clv":          round(historical_clv, 2),
        # Intervals
        "avg_interval_days":       round(avg_interval_days, 2),
        "interval_variance":       round(interval_variance, 2),
        "min_gap_days":            round(min_gap, 2),
        "max_gap_days":            round(max_gap, 2),
        "purchase_freq_trend":     freq_trend,
        # Seasonal
        "seasonal_concentration":  round(seasonal_concentration, 4),
        # Category
        "top_category":            top_category,
        "category_count":          category_count,
        # Returns / sensitivity
        "return_rate":             round(return_rate, 4),
        # Engagement
        "website_visits":          visits,
        "complaints":              complaints,
        "engagement_score":        engagement_score,
        "avg_basket_size":         round(avg_basket_size, 2),
        # Subscription
        "subscription_active":     sub_active,
        # Raw customer fields (for model input parity)
        "total_orders":            customer.total_orders or 0,
        "total_spend":             customer.total_spend or 0.0,
        "average_order_value":     customer.average_order_value or 0.0,
    }


def get_all_features(cutoff_date: date = None) -> list[dict]:
    """Return feature dicts for ALL customers."""
    customers = Customer.query.all()
    results = []
    for c in customers:
        feat = get_features_for_customer(c.customer_id, cutoff_date)
        if feat:
            results.append(feat)
    return results
