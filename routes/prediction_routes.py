# ============================================================
# routes/prediction_routes.py — Analysis & Prediction APIs
# ============================================================
# EXISTING routes (preserved):
#   GET /api/customers/<id>/behavior
#   GET /api/analysis/summary
#   GET /api/customers/<id>/churn
#   GET /api/customers/<id>/clv
#   GET /api/segments
#   GET /api/customers/<id>/segment
#   GET /api/customers/<id>/insights
#
# NEW routes added:
#   GET /api/customers/<id>/next-purchase
#   GET /api/customers/<id>/recommend
#   GET /api/customers/<id>/explain/shap
#   GET /api/customers/<id>/explain/lime
#   GET /api/customers/<id>/anomaly
#   GET /api/customers/<id>/features
#   GET /api/anomalies
#   GET /api/explain/global
#   GET /api/model/info
#   POST /api/batch/churn
# ============================================================

from flask import Blueprint, jsonify, request
from models.customer import Customer
from services.analytics_service import (
    analyze_customer_behavior,
    get_all_customers_analysis
)
from services.churn_service import predict_churn
from services.clv_service import predict_clv
from services.segmentation_service import get_all_segments, get_customer_segment
from services.insights_service import get_customer_insights

prediction_bp = Blueprint("prediction_bp", __name__)


# ── EXISTING ROUTE 1 ──────────────────────────────────────

@prediction_bp.route("/api/customers/<string:customer_id>/behavior", methods=["GET"])
def get_customer_behavior(customer_id):
    """Returns a complete behavioral analysis of one customer."""
    try:
        customer = Customer.query.get(customer_id)
        if not customer:
            return jsonify({"success": False, "error": f"Customer '{customer_id}' not found"}), 404
        result = analyze_customer_behavior(customer_id)
        return jsonify({"success": True, "behavior_analysis": result}), 200
    except Exception as e:
        return jsonify({"success": False, "error": "Failed to analyze customer behavior", "message": str(e)}), 500


# ── EXISTING ROUTE 2 ──────────────────────────────────────

@prediction_bp.route("/api/analysis/summary", methods=["GET"])
def get_analysis_summary():
    """Returns aggregate analysis stats across all customers."""
    try:
        result = get_all_customers_analysis()
        return jsonify({"success": True, "summary": result}), 200
    except Exception as e:
        return jsonify({"success": False, "error": "Failed to generate summary", "message": str(e)}), 500


# ── EXISTING ROUTE 3 ──────────────────────────────────────

@prediction_bp.route("/api/customers/<string:customer_id>/churn", methods=["GET"])
def get_churn_prediction(customer_id):
    """Predicts churn probability for a customer using ML model."""
    try:
        customer = Customer.query.get(customer_id)
        if not customer:
            return jsonify({"success": False, "error": f"Customer '{customer_id}' not found"}), 404
        result = predict_churn(customer_id)
        return jsonify({"success": True, "churn_prediction": result}), 200
    except Exception as e:
        return jsonify({"success": False, "error": "Churn prediction failed", "message": str(e)}), 500


# ── EXISTING ROUTE 4 ──────────────────────────────────────

@prediction_bp.route("/api/customers/<string:customer_id>/clv", methods=["GET"])
def get_clv_prediction(customer_id):
    """Predicts Customer Lifetime Value using ML model."""
    try:
        customer = Customer.query.get(customer_id)
        if not customer:
            return jsonify({"success": False, "error": f"Customer '{customer_id}' not found"}), 404
        result = predict_clv(customer_id)
        return jsonify({"success": True, "clv_prediction": result}), 200
    except Exception as e:
        return jsonify({"success": False, "error": "CLV prediction failed", "message": str(e)}), 500


# ── EXISTING ROUTE 5 ──────────────────────────────────────

@prediction_bp.route("/api/segments", methods=["GET"])
def get_segments():
    """Segments ALL customers into groups."""
    try:
        result = get_all_segments()
        return jsonify({"success": True, "segmentation": result}), 200
    except Exception as e:
        return jsonify({"success": False, "error": "Segmentation failed", "message": str(e)}), 500


# ── EXISTING ROUTE 6 ──────────────────────────────────────

@prediction_bp.route("/api/customers/<string:customer_id>/segment", methods=["GET"])
def get_single_segment(customer_id):
    """Returns the segment for one specific customer."""
    try:
        result = get_customer_segment(customer_id)
        if not result:
            return jsonify({"success": False, "error": f"Customer '{customer_id}' not found"}), 404
        return jsonify({"success": True, "segment_info": result}), 200
    except Exception as e:
        return jsonify({"success": False, "error": "Segment lookup failed", "message": str(e)}), 500


# ── EXISTING ROUTE 7 ──────────────────────────────────────

@prediction_bp.route("/api/customers/<string:customer_id>/insights", methods=["GET"])
def get_insights(customer_id):
    """Full AI intelligence report for one customer."""
    try:
        customer = Customer.query.get(customer_id)
        if not customer:
            return jsonify({"success": False, "error": f"Customer '{customer_id}' not found"}), 404
        result = get_customer_insights(customer_id)
        return jsonify({"success": True, "intelligence_report": result}), 200
    except Exception as e:
        return jsonify({"success": False, "error": "Failed to generate insights", "message": str(e)}), 500


# ── NEW ROUTE 8: Next-Purchase Prediction ─────────────────

@prediction_bp.route("/api/customers/<string:customer_id>/next-purchase", methods=["GET"])
def get_next_purchase(customer_id):
    """
    Predicts next purchase date, amount and probability
    using exponentially-weighted historical intervals.
    """
    try:
        from services.next_purchase_service import predict_next_purchase
        customer = Customer.query.get(customer_id)
        if not customer:
            return jsonify({"success": False, "error": f"Customer '{customer_id}' not found"}), 404
        result = predict_next_purchase(customer_id)
        return jsonify({"success": True, "next_purchase": result}), 200
    except Exception as e:
        return jsonify({"success": False, "error": "Next-purchase prediction failed", "message": str(e)}), 500


# ── NEW ROUTE 9: Product Recommendations ──────────────────

@prediction_bp.route("/api/customers/<string:customer_id>/recommend", methods=["GET"])
def get_recommendations(customer_id):
    """
    Returns personalised product category recommendations
    based on collaborative filtering + bestseller fallback.
    """
    try:
        from services.recommendation_service import get_recommendations
        customer = Customer.query.get(customer_id)
        if not customer:
            return jsonify({"success": False, "error": f"Customer '{customer_id}' not found"}), 404
        top_n = request.args.get("top_n", 5, type=int)
        result = get_recommendations(customer_id, top_n=top_n)
        return jsonify({"success": True, "recommendations": result}), 200
    except Exception as e:
        return jsonify({"success": False, "error": "Recommendation failed", "message": str(e)}), 500


# ── NEW ROUTE 10: SHAP Explanation ────────────────────────

@prediction_bp.route("/api/customers/<string:customer_id>/explain/shap", methods=["GET"])
def explain_shap(customer_id):
    """
    Returns SHAP values explaining the churn prediction for this
    customer, along with a plain-language explanation.
    """
    try:
        from services.xai_service import explain_shap as _shap
        customer = Customer.query.get(customer_id)
        if not customer:
            return jsonify({"success": False, "error": f"Customer '{customer_id}' not found"}), 404
        result = _shap(customer_id)
        return jsonify({"success": True, "explanation": result}), 200
    except Exception as e:
        return jsonify({"success": False, "error": "SHAP explanation failed", "message": str(e)}), 500


# ── NEW ROUTE 11: LIME Explanation ────────────────────────

@prediction_bp.route("/api/customers/<string:customer_id>/explain/lime", methods=["GET"])
def explain_lime(customer_id):
    """Returns a LIME explanation for the churn prediction."""
    try:
        from services.xai_service import explain_lime as _lime
        customer = Customer.query.get(customer_id)
        if not customer:
            return jsonify({"success": False, "error": f"Customer '{customer_id}' not found"}), 404
        result = _lime(customer_id)
        return jsonify({"success": True, "lime_explanation": result}), 200
    except Exception as e:
        return jsonify({"success": False, "error": "LIME explanation failed", "message": str(e)}), 500


# ── NEW ROUTE 12: Global Feature Importance ───────────────

@prediction_bp.route("/api/explain/global", methods=["GET"])
def global_feature_importance():
    """Returns global feature importance from the churn model."""
    try:
        from services.xai_service import get_global_feature_importance
        result = get_global_feature_importance()
        return jsonify({"success": True, "global_importance": result}), 200
    except Exception as e:
        return jsonify({"success": False, "error": "Feature importance failed", "message": str(e)}), 500


# ── NEW ROUTE 13: Single-Customer Anomaly ─────────────────

@prediction_bp.route("/api/customers/<string:customer_id>/anomaly", methods=["GET"])
def get_anomaly(customer_id):
    """Returns anomaly score and flag for a single customer."""
    try:
        from services.anomaly_service import get_anomaly_score
        customer = Customer.query.get(customer_id)
        if not customer:
            return jsonify({"success": False, "error": f"Customer '{customer_id}' not found"}), 404
        result = get_anomaly_score(customer_id)
        return jsonify({"success": True, "anomaly": result}), 200
    except Exception as e:
        return jsonify({"success": False, "error": "Anomaly detection failed", "message": str(e)}), 500


# ── NEW ROUTE 14: All Anomalies ───────────────────────────

@prediction_bp.route("/api/anomalies", methods=["GET"])
def get_all_anomalies():
    """Returns anomaly scores and flags for all customers."""
    try:
        from services.anomaly_service import get_all_anomalies as _all
        result = _all()
        return jsonify({"success": True, "anomaly_report": result}), 200
    except Exception as e:
        return jsonify({"success": False, "error": "Anomaly scan failed", "message": str(e)}), 500


# ── NEW ROUTE 15: Customer Feature Vector ─────────────────

@prediction_bp.route("/api/customers/<string:customer_id>/features", methods=["GET"])
def get_customer_features(customer_id):
    """Returns full 20+ feature vector for a customer (ML transparency)."""
    try:
        from services.feature_engineering import get_features_for_customer
        customer = Customer.query.get(customer_id)
        if not customer:
            return jsonify({"success": False, "error": f"Customer '{customer_id}' not found"}), 404
        result = get_features_for_customer(customer_id)
        return jsonify({"success": True, "features": result}), 200
    except Exception as e:
        return jsonify({"success": False, "error": "Feature extraction failed", "message": str(e)}), 500


# ── NEW ROUTE 16: Model Metadata ──────────────────────────

@prediction_bp.route("/api/model/info", methods=["GET"])
def get_model_info():
    """Returns metadata about the currently deployed churn model."""
    import os, json
    base       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    model_path = os.path.join(base, "ml", "models", "churn_model.pkl")
    name_path  = os.path.join(base, "ml", "models", "churn_best_name.txt")
    log_path   = os.path.join(base, "ml", "experiment_log.json")

    model_name = "Random Forest (v1)"
    if os.path.exists(name_path):
        with open(name_path) as f:
            model_name = f.read().strip()

    last_experiment = None
    if os.path.exists(log_path):
        with open(log_path) as f:
            try:
                history = json.load(f)
                last_experiment = history[-1] if history else None
            except Exception:
                pass

    return jsonify({
        "success": True,
        "model_info": {
            "model_name":   model_name,
            "model_file":   "ml/models/churn_model.pkl",
            "model_exists": os.path.exists(model_path),
            "features": [
                "total_orders", "total_spend", "days_since_last_purchase",
                "average_order_value", "website_visits", "complaints",
                "subscription_active"
            ],
            "last_experiment": last_experiment,
        }
    }), 200


# ── NEW ROUTE 17: Batch Churn Prediction ──────────────────

@prediction_bp.route("/api/batch/churn", methods=["POST"])
def batch_churn():
    """
    Batch churn prediction for up to 200 customer IDs.
    Body: { "customer_ids": ["C1001", "C1002", ...] }
    """
    try:
        data = request.get_json()
        if not data or "customer_ids" not in data:
            return jsonify({"success": False, "error": "Provide customer_ids list in JSON body"}), 400
        ids = data["customer_ids"]
        if not isinstance(ids, list) or len(ids) == 0:
            return jsonify({"success": False, "error": "customer_ids must be a non-empty list"}), 400
        if len(ids) > 200:
            return jsonify({"success": False, "error": "Max 200 IDs per batch"}), 400

        results, errors = [], []
        for cid in ids:
            try:
                results.append(predict_churn(str(cid)))
            except Exception as e:
                errors.append({"customer_id": cid, "error": str(e)})

        return jsonify({
            "success":      True,
            "processed":    len(results),
            "errors":       len(errors),
            "results":      results,
            "error_details": errors,
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": "Batch prediction failed", "message": str(e)}), 500
