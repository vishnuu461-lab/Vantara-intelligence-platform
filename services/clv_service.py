# ============================================================
# services/clv_service.py — CLV Prediction Service
# ============================================================
# Loads the trained CLV model and predicts Customer Lifetime
# Value for a specific customer.
# ============================================================

import os
import joblib
import numpy as np
from datetime import date
from models.customer import Customer
from models.purchase import Purchase
from extensions import db
from sqlalchemy import func

# ============================================================
# LOAD TRAINED MODEL
# ============================================================

# ── Lazy-load globals (loaded on first call, not at import time) ──
_clv_model  = None
_clv_scaler = None
_model_loaded = False

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH  = os.path.join(BASE_DIR, "ml", "models", "clv_model.pkl")
SCALER_PATH = os.path.join(BASE_DIR, "ml", "models", "clv_scaler.pkl")


def _load_model():
    """Load CLV model and scaler on demand (lazy init)."""
    global _clv_model, _clv_scaler, _model_loaded
    if _model_loaded:
        return
    _model_loaded = True
    if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
        try:
            _clv_model  = joblib.load(MODEL_PATH)
            _clv_scaler = joblib.load(SCALER_PATH)
            print("  CLV model loaded successfully.")
        except Exception as e:
            print(f"  WARNING: CLV model load failed: {e}")
            _clv_model = _clv_scaler = None
    else:
        print("  WARNING: CLV model not found. Run ml/train_clv_model.py first.")


# ============================================================
# MAIN PREDICTION FUNCTION
# ============================================================

def predict_clv(customer_id):
    """
    Predicts Customer Lifetime Value using an analytical formula
    based on each customer's actual purchase behavior.

    Formula:
        CLV = avg_order_value × orders_per_year × lifetime_years
              × recency_factor × complaint_factor

    This gives meaningfully different values for each customer
    based on their real data (spend, frequency, subscription, recency).
    """
    from utils.cache import cache_get, cache_set
    _cache_key = f"clv:{customer_id}"
    cached = cache_get(_cache_key)
    if cached is not None:
        return cached

    # --- Fetch customer ---
    customer = db.session.get(Customer, customer_id)
    if not customer:
        return None

    today = date.today()

    # ── Core metrics ──────────────────────────────────────────
    avg_order   = customer.average_order_value or 0
    total_orders = customer.total_orders or 0
    complaints  = customer.complaints or 0

    # Days since last purchase
    if customer.last_purchase_date:
        days_since_last = (today - customer.last_purchase_date).days
    else:
        days_since_last = 730  # Never bought → treat as very inactive

    # ── Orders per year (from actual purchase history) ────────
    first_purchase = db.session.query(
        func.min(Purchase.purchase_date)
    ).filter(Purchase.customer_id == customer_id).scalar()

    if first_purchase and total_orders > 0:
        months_active = max((today - first_purchase).days / 30.0, 1)
        orders_per_year = round((total_orders / months_active) * 12, 2)
    else:
        orders_per_year = max(total_orders, 1)  # At least 1/year

    orders_per_year = min(orders_per_year, 52)  # Cap at weekly purchases

    # ── Customer Lifetime estimate (years) ────────────────────
    # Based on subscription tier — Premium customers stay longer
    sub = customer.subscription_status or ""
    if sub == "Premium":
        lifetime_years = 4.5
    elif sub == "Active":
        lifetime_years = 3.0
    elif sub == "Inactive":
        lifetime_years = 1.5
    else:  # Cancelled or unknown
        lifetime_years = 0.8

    # ── Recency factor (how recently they purchased) ──────────
    if days_since_last <= 30:
        recency_factor = 1.30   # Very recent — highly engaged
    elif days_since_last <= 90:
        recency_factor = 1.15
    elif days_since_last <= 180:
        recency_factor = 1.00
    elif days_since_last <= 365:
        recency_factor = 0.75   # Fading engagement
    elif days_since_last <= 730:
        recency_factor = 0.50   # At risk
    else:
        recency_factor = 0.25   # Near-lost customer

    # ── Complaint penalty ─────────────────────────────────────
    # Every complaint reduces expected CLV (satisfaction hurt)
    complaint_factor = max(0.40, 1.0 - (complaints * 0.12))

    # ── Calculate CLV ─────────────────────────────────────────
    predicted_clv = (
        avg_order
        * orders_per_year
        * lifetime_years
        * recency_factor
        * complaint_factor
    )
    predicted_clv = max(0, round(predicted_clv, 2))

    # ── CLV Tier ──────────────────────────────────────────────
    if predicted_clv >= 100000:
        clv_tier, clv_color = "Platinum", "purple"
        clv_action = "Extremely high-value. Offer VIP treatment and a dedicated account manager."
    elif predicted_clv >= 50000:
        clv_tier, clv_color = "Gold", "gold"
        clv_action = "High-value customer. Prioritize retention with loyalty rewards and personalized offers."
    elif predicted_clv >= 20000:
        clv_tier, clv_color = "Silver", "silver"
        clv_action = "Medium-value. Encourage more purchases through targeted promotions."
    elif predicted_clv >= 5000:
        clv_tier, clv_color = "Bronze", "brown"
        clv_action = "Lower-value. Use email campaigns and small discounts to re-engage."
    else:
        clv_tier, clv_color = "Entry", "gray"
        clv_action = "Very low predicted value. Offer a first-purchase incentive to boost engagement."

    # ── Context: compare to average ───────────────────────────
    avg_spend_result = db.session.query(func.avg(Customer.total_spend)).scalar()
    avg_spend = round(avg_spend_result or 0, 2)
    total_spend = customer.total_spend or 0
    comparison = (
        f"Above average (avg: Rs.{avg_spend:,.0f})"
        if total_spend >= avg_spend
        else f"Below average (avg: Rs.{avg_spend:,.0f})"
    )

    result = {
        "customer_id":    customer_id,
        "name":           customer.name,
        "predicted_clv":  predicted_clv,
        "predicted_clv_formatted": f"Rs.{predicted_clv:,.0f}",
        "clv_tier":       clv_tier,
        "clv_color":      clv_color,
        "recommended_action": clv_action,
        "context": {
            "current_total_spend":      total_spend,
            "current_spend_vs_average": comparison,
            "orders_per_year":          orders_per_year,
            "lifetime_estimate_years":  lifetime_years,
            "recency_factor":           recency_factor,
            "complaint_factor":         complaint_factor,
            "subscription_status":      customer.subscription_status,
            "days_since_last_purchase": days_since_last,
        },
        "features_used": {
            "avg_order_value":     avg_order,
            "orders_per_year":     orders_per_year,
            "lifetime_years":      lifetime_years,
            "recency_factor":      recency_factor,
            "complaint_factor":    complaint_factor,
            "total_orders":        total_orders,
            "days_since_last":     days_since_last,
        },
        "model_used":  "Analytical CLV Formula (RFM-based)",
        "disclaimer": (
            "CLV is estimated using avg_order_value × purchase_frequency × "
            "lifetime_years × recency_factor × complaint_factor. "
            "Use as a guide for retention prioritization."
        )
    }
    cache_set(_cache_key, result)
    return result

# ============================================================
# FALLBACK: Formula-Based CLV (kept as utility)
# ============================================================

def formula_based_clv(customer):
    """Simple formula-based CLV fallback."""
    avg_order = customer.average_order_value or 0
    orders    = customer.total_orders or 0
    orders_per_year = min(orders, 24)
    estimated_years = 2.0
    if customer.subscription_status == "Premium":
        estimated_years = 3.0
    elif customer.subscription_status in ["Inactive", "Cancelled"]:
        estimated_years = 0.5
    predicted_clv = round(avg_order * orders_per_year * estimated_years, 2)
    return {
        "customer_id":             customer.customer_id,
        "name":                    customer.name,
        "predicted_clv":           predicted_clv,
        "predicted_clv_formatted": f"Rs.{predicted_clv:,.0f}",
        "clv_tier":                "Bronze",
        "clv_color":               "brown",
        "model_used":              "Formula-Based",
        "disclaimer":              "Simplified estimate.",
    }
