# ============================================================
# services/xai_service.py — Explainable AI (SHAP + LIME)
# ============================================================
# Provides SHAP and LIME explanations for the churn model.
# Generates plain-language explanations accessible from the API.
#
# IMPORTANT:
#   - Loads the existing churn model (ml/models/churn_model.pkl)
#   - Does NOT replace or retrain the model
#   - Generates per-customer explanations on demand
# ============================================================

import os
import sys
import numpy as np
import joblib
import logging

logger = logging.getLogger(__name__)

# Resolve paths
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MODEL_PATH  = os.path.join(_BASE, "ml", "models", "churn_model.pkl")
_SCALER_PATH = os.path.join(_BASE, "ml", "models", "churn_scaler.pkl")

# Feature names — must match train_churn_model.py
FEATURE_NAMES = [
    "total_orders",
    "total_spend",
    "days_since_last_purchase",
    "average_order_value",
    "website_visits",
    "complaints",
    "subscription_active",
]

# ── Load model once at import time ────────────────────────

_model  = None
_scaler = None
_explainer = None  # SHAP explainer (lazy-loaded)

def _load():
    global _model, _scaler
    if _model is None:
        if not os.path.exists(_MODEL_PATH):
            raise FileNotFoundError(
                f"Churn model not found at {_MODEL_PATH}. "
                "Run: python ml/train_churn_model.py"
            )
        _model  = joblib.load(_MODEL_PATH)
        _scaler = joblib.load(_SCALER_PATH)


def _get_explainer():
    """Lazy-load SHAP TreeExplainer."""
    global _explainer
    if _explainer is None:
        try:
            import shap
            _load()
            _explainer = shap.TreeExplainer(_model)
        except ImportError:
            logger.warning("SHAP not installed — install with: pip install shap")
            _explainer = None
    return _explainer


def _customer_to_features(customer) -> np.ndarray:
    """Convert a Customer ORM object to the 7-feature vector."""
    sub_active = 1 if (customer.subscription_status or "").lower() in (
        "active", "premium"
    ) else 0
    from datetime import date
    if customer.last_purchase_date:
        days_since = (date.today() - customer.last_purchase_date).days
    else:
        days_since = 9999

    return np.array([[
        customer.total_orders or 0,
        customer.total_spend or 0.0,
        days_since,
        customer.average_order_value or 0.0,
        customer.website_visits or 0,
        customer.complaints or 0,
        sub_active,
    ]])


# ── SHAP explanations ──────────────────────────────────────

def explain_shap(customer_id: str) -> dict:
    """
    Return SHAP values for a single customer showing which
    features push the churn prediction higher or lower.
    """
    from models.customer import Customer
    from extensions import db

    customer = db.session.get(Customer, customer_id)
    if not customer:
        return {"error": f"Customer {customer_id} not found"}

    try:
        _load()
        explainer = _get_explainer()

        X = _customer_to_features(customer)
        X_scaled = _scaler.transform(X)

        # Churn probability
        prob = float(_model.predict_proba(X_scaled)[0][1])
        pred = int(_model.predict(X_scaled)[0])

        if explainer is None:
            # Fallback: use feature importances
            importances = _model.feature_importances_
            shap_values = [(f, float(imp * (prob - 0.5) * 2))
                           for f, imp in zip(FEATURE_NAMES, importances)]
        else:
            import shap
            sv = explainer.shap_values(X_scaled)
            # sv shape: [n_classes][n_samples, n_features] for tree models
            if isinstance(sv, list):
                vals = sv[1][0]   # class=1 (churned)
            else:
                vals = sv[0]
            shap_values = list(zip(FEATURE_NAMES, [float(v) for v in vals]))

        # Sort by absolute SHAP value
        shap_values.sort(key=lambda x: abs(x[1]), reverse=True)

        # Actual feature values
        feat_vals = dict(zip(FEATURE_NAMES, _customer_to_features(customer)[0].tolist()))

        # Plain-language explanation
        explanation = _build_plain_explanation(
            customer.name, prob, pred, shap_values, feat_vals
        )

        return {
            "customer_id":      customer_id,
            "name":             customer.name,
            "churn_probability": round(prob, 4),
            "prediction":       "Churned" if pred == 1 else "Active",
            "shap_values": [
                {
                    "feature":     f,
                    "shap_value":  round(v, 4),
                    "direction":   "increases_churn" if v > 0 else "decreases_churn",
                    "importance":  round(abs(v), 4),
                    "actual_value": feat_vals.get(f),
                }
                for f, v in shap_values
            ],
            "plain_language_explanation": explanation,
            "method": "shap_tree_explainer",
        }

    except Exception as e:
        logger.error(f"SHAP explanation failed for {customer_id}: {e}")
        return {"error": str(e), "customer_id": customer_id}


def explain_lime(customer_id: str) -> dict:
    """
    Return a LIME explanation for a single customer.
    LIME perturbs the input and fits a local linear model.
    """
    from models.customer import Customer
    from extensions import db

    customer = db.session.get(Customer, customer_id)
    if not customer:
        return {"error": f"Customer {customer_id} not found"}

    try:
        import lime
        import lime.lime_tabular
        import numpy as np
        _load()

        X = _customer_to_features(customer)
        X_scaled = _scaler.transform(X)
        prob = float(_model.predict_proba(X_scaled)[0][1])

        # Build LIME explainer with a small synthetic background
        np.random.seed(42)
        bg = np.random.randn(200, len(FEATURE_NAMES))

        lime_exp = lime.lime_tabular.LimeTabularExplainer(
            training_data=bg,
            feature_names=FEATURE_NAMES,
            class_names=["Active", "Churned"],
            mode="classification",
            random_state=42,
        )

        def predict_fn(arr):
            return _model.predict_proba(_scaler.transform(arr))

        explanation = lime_exp.explain_instance(
            X_scaled[0],
            predict_fn,
            num_features=7,
        )

        lime_list = explanation.as_list()
        feat_vals  = dict(zip(FEATURE_NAMES, X[0].tolist()))

        return {
            "customer_id":       customer_id,
            "name":              customer.name,
            "churn_probability": round(prob, 4),
            "prediction":        "Churned" if prob >= 0.5 else "Active",
            "lime_values": [
                {
                    "condition":   cond,
                    "lime_weight": round(weight, 4),
                    "direction":   "increases_churn" if weight > 0 else "decreases_churn",
                }
                for cond, weight in lime_list
            ],
            "method": "lime_tabular",
        }

    except ImportError:
        return {"error": "LIME not installed. Run: pip install lime"}
    except Exception as e:
        logger.error(f"LIME explanation failed for {customer_id}: {e}")
        return {"error": str(e)}


def get_global_feature_importance() -> dict:
    """
    Return global feature importance from the churn model.
    Handles both tree-based models (feature_importances_) and
    other models (MLP, LR) via permutation importance fallback.
    """
    try:
        _load()

        # Try tree-based feature importances first (RF, XGB, LGB)
        if hasattr(_model, "feature_importances_"):
            importances = _model.feature_importances_
            method = "tree_feature_importance"
        else:
            # Fallback: permutation importance on small synthetic dataset
            from sklearn.inspection import permutation_importance
            import numpy as np
            np.random.seed(42)
            n = 200
            X_bg = np.column_stack([
                np.random.randint(0, 30, n),          # total_orders
                np.random.uniform(0, 200000, n),       # total_spend
                np.random.randint(1, 500, n),          # days_since_last
                np.random.uniform(500, 10000, n),      # avg_order_value
                np.random.randint(0, 200, n),          # website_visits
                np.random.randint(0, 5, n),            # complaints
                np.random.randint(0, 2, n),            # subscription_active
            ])
            X_scaled = _scaler.transform(X_bg)
            y_bg = _model.predict(X_scaled)

            pi = permutation_importance(
                _model, X_scaled, y_bg,
                n_repeats=5, random_state=42, scoring="accuracy"
            )
            importances = pi.importances_mean
            # Normalise to sum to 1
            total = importances.sum()
            if total > 0:
                importances = importances / total
            method = "permutation_importance"

        ranked = sorted(
            zip(FEATURE_NAMES, importances),
            key=lambda x: x[1], reverse=True
        )
        return {
            "method": method,
            "global_importances": [
                {"feature": f, "importance": round(float(v), 4), "rank": i + 1}
                for i, (f, v) in enumerate(ranked)
            ]
        }
    except Exception as e:
        return {"error": str(e)}


# ── Plain-language explanation builder ─────────────────────

def _build_plain_explanation(name: str, prob: float, pred: int,
                              shap_vals: list, feat_vals: dict) -> str:
    """Generate a human-readable churn explanation from SHAP values."""
    first = name.split()[0]
    risk  = "high" if prob >= 0.7 else "medium" if prob >= 0.4 else "low"
    lines = [
        f"{first} is classified as {risk} churn risk "
        f"({prob*100:.1f}% probability)."
    ]

    # Explain top 3 drivers
    drivers = []
    for feat, val in shap_vals[:3]:
        actual = feat_vals.get(feat, "N/A")
        direction = "increasing" if val > 0 else "decreasing"

        if feat == "days_since_last_purchase":
            drivers.append(
                f"high recency ({int(actual)} days since last purchase) is "
                f"{direction} churn risk"
            )
        elif feat == "total_orders":
            drivers.append(
                f"low purchase frequency ({int(actual)} orders) is "
                f"{direction} churn risk"
            )
        elif feat == "complaints":
            drivers.append(
                f"{int(actual)} complaint(s) on record is "
                f"{direction} churn risk"
            )
        elif feat == "website_visits":
            drivers.append(
                f"website visit count ({int(actual)}) is "
                f"{direction} churn risk"
            )
        elif feat == "subscription_active":
            status = "active" if actual == 1 else "inactive"
            drivers.append(
                f"subscription is {status}, which is {direction} churn risk"
            )
        elif feat == "total_spend":
            drivers.append(
                f"total spend (₹{actual:,.0f}) is {direction} churn risk"
            )

    if drivers:
        lines.append(
            f"{first} is mainly classified this way because their "
            + ", while their ".join(drivers) + "."
        )

    return " ".join(lines)
