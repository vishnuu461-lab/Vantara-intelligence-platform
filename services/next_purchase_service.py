# ============================================================
# services/next_purchase_service.py — Next-Purchase Prediction
# ============================================================
# Predicts when a customer is likely to buy next and the
# probable purchase amount, based on their purchase history.
#
# APPROACH (no LSTM training required at runtime):
#   - Use customer's own historical inter-purchase intervals
#   - Fit a simple exponential smoothing trend
#   - Predict next date = last_purchase + avg_interval
#   - Predict amount = exponentially-weighted avg of past amounts
#   - Compute "next-purchase probability" from recency vs interval
#
# An LSTM variant can replace this service once enough
# sequential data is available (see ml/train_next_purchase_lstm.py).
# ============================================================

import math
from datetime import date, timedelta
from models.customer import Customer
from models.purchase import Purchase
from extensions import db


def predict_next_purchase(customer_id: str) -> dict:
    """
    Predict the next purchase date, amount, and probability.

    Returns:
        {
          customer_id, name,
          purchase_history_count,
          avg_interval_days,
          last_purchase_date,
          predicted_next_date,
          days_until_next,
          predicted_amount,
          next_purchase_probability,
          probability_label,
          likely_category,
          sequence_summary  (last 5 purchases as list)
        }
    """
    customer = db.session.get(Customer, customer_id)
    if not customer:
        return {"error": f"Customer {customer_id} not found"}

    # Fetch time-ordered purchase history
    purchases = Purchase.query.filter_by(
        customer_id=customer_id
    ).order_by(Purchase.purchase_date.asc()).all()

    today = date.today()

    if not purchases:
        return {
            "customer_id":              customer_id,
            "name":                     customer.name,
            "purchase_history_count":   0,
            "avg_interval_days":        None,
            "last_purchase_date":       None,
            "predicted_next_date":      None,
            "days_until_next":          None,
            "predicted_amount":         None,
            "next_purchase_probability": 0.0,
            "probability_label":        "Very Low",
            "likely_category":          None,
            "sequence_summary":         [],
            "note": "No purchase history available for prediction.",
        }

    # ── Build time-ordered sequence ────────────────────────

    dated = [p for p in purchases if p.purchase_date]
    dated.sort(key=lambda p: p.purchase_date)

    # Inter-purchase intervals (days)
    intervals = [
        (dated[i].purchase_date - dated[i-1].purchase_date).days
        for i in range(1, len(dated))
    ]

    if intervals:
        # Exponential weighting — recent gaps matter more
        weights   = [math.exp(0.1 * i) for i in range(len(intervals))]
        wsum      = sum(weights)
        avg_interval = sum(w * g for w, g in zip(weights, intervals)) / wsum
    else:
        # Only one purchase — use overall average from DB
        avg_interval = 60  # default: 60-day cadence

    avg_interval = max(1, round(avg_interval))

    last_purchase = dated[-1].purchase_date
    days_since    = (today - last_purchase).days

    # ── Predicted next date ───────────────────────────────

    predicted_next = last_purchase + timedelta(days=avg_interval)
    days_until     = (predicted_next - today).days

    # ── Predicted amount (exp-weighted avg of past amounts) ─

    amounts = [p.amount for p in dated if p.amount and p.amount > 0]
    if amounts:
        a_weights = [math.exp(0.15 * i) for i in range(len(amounts))]
        aw_sum    = sum(a_weights)
        pred_amount = sum(w * a for w, a in zip(a_weights, amounts)) / aw_sum
    else:
        pred_amount = customer.average_order_value or 0.0

    # ── Next-purchase probability ──────────────────────────
    # P = sigmoid-like function of how overdue the customer is
    # If days_since ≤ avg_interval → high probability
    # If days_since >> avg_interval → lower probability
    ratio = days_since / avg_interval if avg_interval > 0 else 1.0
    if ratio <= 0.5:
        prob = 0.90
    elif ratio <= 1.0:
        prob = 0.75
    elif ratio <= 1.5:
        prob = 0.55
    elif ratio <= 2.0:
        prob = 0.35
    elif ratio <= 3.0:
        prob = 0.18
    else:
        prob = 0.08

    if prob >= 0.75:   prob_label = "Very High"
    elif prob >= 0.55: prob_label = "High"
    elif prob >= 0.35: prob_label = "Medium"
    elif prob >= 0.18: prob_label = "Low"
    else:              prob_label = "Very Low"

    # ── Likely category (most recent / most frequent) ──────

    from collections import Counter
    cats = [p.product_category for p in dated if p.product_category]
    likely_category = Counter(cats).most_common(1)[0][0] if cats else None

    # ── Last-5 purchase sequence ───────────────────────────

    sequence = [
        {
            "date":     p.purchase_date.isoformat() if p.purchase_date else None,
            "amount":   round(p.amount, 2) if p.amount else None,
            "category": p.product_category,
            "gap_days": (dated[i].purchase_date - dated[i-1].purchase_date).days
                        if i > 0 and dated[i].purchase_date and dated[i-1].purchase_date
                        else None,
        }
        for i, p in enumerate(dated[-5:], start=max(0, len(dated) - 5))
    ]

    return {
        "customer_id":               customer_id,
        "name":                      customer.name,
        "purchase_history_count":    len(dated),
        "avg_interval_days":         avg_interval,
        "last_purchase_date":        last_purchase.isoformat(),
        "days_since_last_purchase":  days_since,
        "predicted_next_date":       predicted_next.isoformat(),
        "days_until_next":           days_until,
        "predicted_amount":          round(pred_amount, 2),
        "next_purchase_probability": round(prob, 4),
        "probability_label":         prob_label,
        "likely_category":           likely_category,
        "sequence_summary":          sequence,
    }
