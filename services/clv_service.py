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

# Use current working directory (where you run app.py from)
# This is more reliable than __file__ in Flask debug mode
BASE_DIR    = os.getcwd()
MODEL_PATH  = os.path.join(BASE_DIR, "ml", "models", "clv_model.pkl")
SCALER_PATH = os.path.join(BASE_DIR, "ml", "models", "clv_scaler.pkl")

clv_model  = None
clv_scaler = None

if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
    clv_model  = joblib.load(MODEL_PATH)
    clv_scaler = joblib.load(SCALER_PATH)
    print("  CLV model loaded successfully.")
else:
    print("  WARNING: CLV model not found. Run ml/train_clv_model.py first.")


# ============================================================
# MAIN PREDICTION FUNCTION
# ============================================================

def predict_clv(customer_id):
    """
    Predicts the Customer Lifetime Value for a given customer.

    CLV = Estimated total revenue this customer will generate
          in the next 12 months (approximately).

    Args:
        customer_id (str): e.g., "C1001"

    Returns:
        dict with predicted_clv and supporting context
    """

    # --- Fetch customer ---
    customer = db.session.get(Customer, customer_id)
    if not customer:
        return None

    # --- Fallback if model not loaded ---
    if clv_model is None or clv_scaler is None:
        return formula_based_clv(customer)

    today = date.today()

    # --------------------------------------------------------
    # CALCULATE FEATURES
    # Same order and logic as training!
    # --------------------------------------------------------

    total_orders = customer.total_orders or 0
    total_spend  = customer.total_spend or 0
    avg_order_value = customer.average_order_value or 0

    # Days since last purchase
    if customer.last_purchase_date:
        days_since_last = (today - customer.last_purchase_date).days
    else:
        days_since_last = 365

    # purchases_per_month: calculate from purchase history
    first_purchase = db.session.query(
        func.min(Purchase.purchase_date)
    ).filter(Purchase.customer_id == customer_id).scalar()

    if first_purchase and total_orders > 0:
        months_active = max((today - first_purchase).days / 30, 1)
        purchases_per_month = round(total_orders / months_active, 4)
    else:
        purchases_per_month = 0.0

    # subscription_active flag
    subscription_active = (
        1 if customer.subscription_status in ["Active", "Premium"] else 0
    )

    features = np.array([[
        total_orders,
        total_spend,
        avg_order_value,
        customer.website_visits or 0,
        customer.complaints or 0,
        subscription_active,
        days_since_last,
        purchases_per_month
    ]])

    # Scale and predict
    features_scaled = clv_scaler.transform(features)
    predicted_clv   = float(clv_model.predict(features_scaled)[0])
    predicted_clv   = max(0, round(predicted_clv, 2))  # No negative CLV

    # --------------------------------------------------------
    # CLV TIER CLASSIFICATION
    # --------------------------------------------------------
    if predicted_clv >= 100000:
        clv_tier   = "Platinum"
        clv_color  = "purple"
        clv_action = (
            "Extremely high-value customer. Offer VIP treatment, "
            "exclusive deals, and a dedicated account manager."
        )
    elif predicted_clv >= 50000:
        clv_tier   = "Gold"
        clv_color  = "gold"
        clv_action = (
            "High-value customer. Prioritize retention with "
            "loyalty rewards and personalized offers."
        )
    elif predicted_clv >= 20000:
        clv_tier   = "Silver"
        clv_color  = "silver"
        clv_action = (
            "Medium-value customer. Encourage more purchases "
            "through targeted promotions and upselling."
        )
    elif predicted_clv >= 5000:
        clv_tier   = "Bronze"
        clv_color  = "brown"
        clv_action = (
            "Lower-value customer. Use low-cost retention "
            "strategies like email campaigns and small discounts."
        )
    else:
        clv_tier   = "Entry"
        clv_color  = "gray"
        clv_action = (
            "Very low predicted value. Focus on understanding "
            "why engagement is low and offer a first-purchase incentive."
        )

    # --------------------------------------------------------
    # CONTEXT: Compare to average
    # --------------------------------------------------------
    avg_spend_result = db.session.query(
        func.avg(Customer.total_spend)
    ).scalar()
    avg_spend = round(avg_spend_result or 0, 2)

    comparison = (
        f"Above average (avg: Rs.{avg_spend:,.0f})"
        if total_spend >= avg_spend
        else f"Below average (avg: Rs.{avg_spend:,.0f})"
    )

    return {
        "customer_id":    customer_id,
        "name":           customer.name,
        "predicted_clv":  predicted_clv,
        "predicted_clv_formatted": f"Rs.{predicted_clv:,.0f}",
        "clv_tier":       clv_tier,
        "clv_color":      clv_color,
        "recommended_action": clv_action,
        "context": {
            "current_total_spend":       total_spend,
            "current_spend_vs_average":  comparison,
            "purchases_per_month":       purchases_per_month,
            "subscription_status":       customer.subscription_status,
            "days_since_last_purchase":  days_since_last,
        },
        "features_used": {
            "total_orders":        total_orders,
            "total_spend":         total_spend,
            "avg_order_value":     avg_order_value,
            "website_visits":      customer.website_visits or 0,
            "complaints":          customer.complaints or 0,
            "subscription_active": subscription_active,
            "days_since_last":     days_since_last,
            "purchases_per_month": purchases_per_month,
        },
        "model_used":  "Random Forest Regressor",
        "disclaimer": (
            "CLV is a statistical estimate for the next ~12 months. "
            "Actual revenue depends on future customer behavior, "
            "market conditions, and business strategy. Use this as "
            "a guide, not a guarantee."
        )
    }


# ============================================================
# FALLBACK: Formula-Based CLV
# ============================================================

def formula_based_clv(customer):
    """
    Simple formula-based CLV when ML model is not available.
    Formula: avg_order_value * orders_per_year * estimated_years
    """
    avg_order = customer.average_order_value or 0
    orders    = customer.total_orders or 0

    orders_per_year = min(orders, 24)    # Cap at 24 per year
    estimated_years = 2.0                # Assume 2-year horizon

    if customer.subscription_status == "Premium":  estimated_years = 3.0
    elif customer.subscription_status in ["Inactive", "Cancelled"]: estimated_years = 0.5

    predicted_clv = round(avg_order * orders_per_year * estimated_years, 2)

    return {
        "customer_id":    customer.customer_id,
        "name":           customer.name,
        "predicted_clv":  predicted_clv,
        "predicted_clv_formatted": f"Rs.{predicted_clv:,.0f}",
        "model_used":  "Formula-Based (ML model not trained yet)",
        "disclaimer": "Run ml/train_clv_model.py for ML-based predictions."
    }
