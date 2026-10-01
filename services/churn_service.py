# ============================================================
# services/churn_service.py — Churn Prediction Service
# ============================================================
# This file loads the trained churn model and uses it to
# predict whether a specific customer is likely to churn.
#
# HOW IT WORKS:
#   1. Load the saved model from ml/models/churn_model.pkl
#   2. Fetch the customer's data from the database
#   3. Prepare the features (same format as training)
#   4. Run the prediction
#   5. Return the churn probability and risk level
# ============================================================

import os
import joblib
import numpy as np
from datetime import date
from models.customer import Customer
from extensions import db

# ============================================================
# LOAD THE TRAINED MODEL
# ============================================================
# We load the model ONCE when this file is imported.
# This is efficient — we don't reload the model on every request.

# Build the absolute path to the model files
BASE_DIR     = os.getcwd()
MODEL_PATH   = os.path.join(BASE_DIR, "ml", "models", "churn_model.pkl")
SCALER_PATH  = os.path.join(BASE_DIR, "ml", "models", "churn_scaler.pkl")

# Try to load the model — it may not exist yet if training hasn't run
churn_model = None
churn_scaler = None

if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
    churn_model = joblib.load(MODEL_PATH)
    churn_scaler = joblib.load(SCALER_PATH)
    print("  Churn model loaded successfully.")
else:
    print("  WARNING: Churn model not found. Run ml/train_churn_model.py first.")


# ============================================================
# MAIN PREDICTION FUNCTION
# ============================================================

def predict_churn(customer_id):
    """
    Predicts the churn probability for a specific customer.

    Args:
        customer_id (str): e.g., "C1001"

    Returns:
        dict: {
            "customer_id": ...,
            "churn_probability": 0.82,
            "risk_level": "High",
            "risk_color": "red",
            "features_used": {...},
            "explanation": "..."
        }
        or None if customer not found
    """

    # --- Fetch customer ---
    customer = db.session.get(Customer, customer_id)
    if not customer:
        return None

    # --- Check if model is available ---
    if churn_model is None or churn_scaler is None:
        # Fall back to rule-based prediction if model not trained
        return rule_based_churn(customer)

    today = date.today()

    # --------------------------------------------------------
    # PREPARE FEATURES
    # Must be in EXACT same order as training!
    # Order: total_orders, total_spend, days_since_last_purchase,
    #        average_order_value, website_visits, complaints,
    #        subscription_active
    # --------------------------------------------------------

    # Days since last purchase
    if customer.last_purchase_date:
        days_since_last = (today - customer.last_purchase_date).days
    else:
        days_since_last = 365  # Never bought → treat as 1 year inactive

    # subscription_active: 1 if Active/Premium, 0 if Inactive/Cancelled
    subscription_active = (
        1 if customer.subscription_status in ["Active", "Premium"] else 0
    )

    features = np.array([[
        customer.total_orders or 0,
        customer.total_spend or 0,
        days_since_last,
        customer.average_order_value or 0,
        customer.website_visits or 0,
        customer.complaints or 0,
        subscription_active
    ]])

    # --------------------------------------------------------
    # SCALE FEATURES (same scaler used in training)
    # --------------------------------------------------------
    features_scaled = churn_scaler.transform(features)

    # --------------------------------------------------------
    # MAKE PREDICTION
    # predict_proba returns [probability_active, probability_churned]
    # We want the SECOND value → probability of churning
    # --------------------------------------------------------
    probabilities = churn_model.predict_proba(features_scaled)[0]
    churn_probability = round(float(probabilities[1]), 4)

    # --------------------------------------------------------
    # DETERMINE RISK LEVEL
    # --------------------------------------------------------
    if churn_probability >= 0.70:
        risk_level = "High"
        risk_color = "red"
        recommendation = (
            "Immediate action needed. Consider a personal outreach, "
            "special discount, or loyalty reward to retain this customer."
        )
    elif churn_probability >= 0.40:
        risk_level = "Medium"
        risk_color = "orange"
        recommendation = (
            "Monitor this customer closely. A targeted email campaign "
            "or product recommendation may help retain them."
        )
    else:
        risk_level = "Low"
        risk_color = "green"
        recommendation = (
            "This customer appears healthy and engaged. "
            "Continue providing good service to maintain loyalty."
        )

    # --------------------------------------------------------
    # BUILD EXPLANATION
    # --------------------------------------------------------
    explanation_parts = []

    if days_since_last > 180:
        explanation_parts.append(
            f"No purchase in {days_since_last} days (high inactivity)."
        )
    if (customer.complaints or 0) >= 2:
        explanation_parts.append(
            f"{customer.complaints} complaints on record."
        )
    if subscription_active == 0:
        explanation_parts.append(
            f"Subscription status is '{customer.subscription_status}'."
        )
    if (customer.total_orders or 0) <= 2:
        explanation_parts.append("Very few orders placed.")
    if (customer.website_visits or 0) < 10:
        explanation_parts.append("Very low website engagement.")

    if not explanation_parts:
        explanation_parts.append(
            "Customer shows healthy engagement across all metrics."
        )

    explanation = " ".join(explanation_parts)

    return {
        "customer_id": customer_id,
        "name": customer.name,
        "churn_probability": churn_probability,
        "churn_percentage": f"{churn_probability * 100:.1f}%",
        "risk_level": risk_level,
        "risk_color": risk_color,
        "recommendation": recommendation,
        "explanation": explanation,
        "features_used": {
            "total_orders": customer.total_orders or 0,
            "total_spend": customer.total_spend or 0,
            "days_since_last_purchase": days_since_last,
            "average_order_value": customer.average_order_value or 0,
            "website_visits": customer.website_visits or 0,
            "complaints": customer.complaints or 0,
            "subscription_active": subscription_active,
        },
        "model_used": "Random Forest Classifier",
        "disclaimer": (
            "This is an ML-based estimate trained on synthetic data. "
            "Use alongside human judgment for business decisions."
        )
    }


# ============================================================
# FALLBACK: Rule-Based Churn (when model not trained yet)
# ============================================================

def rule_based_churn(customer):
    """
    Simple rule-based churn estimation.
    Used as fallback when ML model is not available.
    """
    today = date.today()
    score = 0

    if customer.last_purchase_date:
        days = (today - customer.last_purchase_date).days
        if days > 365: score += 4
        elif days > 180: score += 3
        elif days > 90: score += 1
    else:
        score += 4

    if (customer.complaints or 0) >= 3: score += 3
    elif (customer.complaints or 0) >= 1: score += 1

    if customer.subscription_status in ["Inactive", "Cancelled"]: score += 3

    if (customer.total_orders or 0) <= 1: score += 2
    if (customer.website_visits or 0) < 5: score += 1

    # Convert score to probability (max possible score ~13)
    probability = min(round(score / 13, 2), 0.99)

    if probability >= 0.70: risk_level = "High"
    elif probability >= 0.40: risk_level = "Medium"
    else: risk_level = "Low"

    return {
        "customer_id": customer.customer_id,
        "name": customer.name,
        "churn_probability": probability,
        "churn_percentage": f"{probability * 100:.1f}%",
        "risk_level": risk_level,
        "model_used": "Rule-Based (ML model not trained yet)",
        "disclaimer": "Run ml/train_churn_model.py for ML-based predictions."
    }
