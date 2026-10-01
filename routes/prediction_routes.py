# ============================================================
# routes/prediction_routes.py — Analysis & Prediction APIs
# ============================================================
# This file contains routes for:
#   GET /api/customers/<id>/behavior   → Purchase behavior
#   GET /api/customers/<id>/churn      → Churn prediction (Stage 10)
#   GET /api/customers/<id>/clv        → CLV prediction (Stage 11)
#   GET /api/segments                  → Customer segments (Stage 13)
#   GET /api/analysis/summary          → Overall stats
# ============================================================

from flask import Blueprint, jsonify
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


# ============================================================
# ROUTE 1: GET /api/customers/<customer_id>/behavior
# ============================================================
# PURPOSE : Analyze a specific customer's purchase behavior
# METHOD  : GET
# URL     : http://localhost:5000/api/customers/C1001/behavior
# ============================================================

@prediction_bp.route("/api/customers/<string:customer_id>/behavior", methods=["GET"])
def get_customer_behavior(customer_id):
    """
    Returns a complete behavioral analysis of one customer.
    Includes recency, frequency, spending level, favorite
    category, recent purchases, and AI-generated insight.
    """
    try:
        # Look up the customer first
        customer = Customer.query.get(customer_id)
        if not customer:
            return jsonify({
                "success": False,
                "error": f"Customer '{customer_id}' not found"
            }), 404

        # Run the analysis from our service
        result = analyze_customer_behavior(customer_id)

        return jsonify({
            "success": True,
            "behavior_analysis": result
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Failed to analyze customer behavior",
            "message": str(e)
        }), 500


# ============================================================
# ROUTE 2: GET /api/analysis/summary
# ============================================================
# PURPOSE : Overall statistics across ALL customers
# METHOD  : GET
# URL     : http://localhost:5000/api/analysis/summary
# ============================================================

@prediction_bp.route("/api/analysis/summary", methods=["GET"])
def get_analysis_summary():
    """Returns aggregate analysis stats across all customers."""
    try:
        result = get_all_customers_analysis()
        return jsonify({
            "success": True,
            "summary": result
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Failed to generate summary",
            "message": str(e)
        }), 500


# ============================================================
# Placeholder routes for upcoming stages
# (These will be filled in Stages 10, 11, 13)
# ============================================================

@prediction_bp.route("/api/customers/<string:customer_id>/churn", methods=["GET"])
def get_churn_prediction(customer_id):
    """Predicts churn probability for a customer using ML model."""
    try:
        customer = Customer.query.get(customer_id)
        if not customer:
            return jsonify({
                "success": False,
                "error": f"Customer '{customer_id}' not found"
            }), 404

        result = predict_churn(customer_id)
        return jsonify({
            "success": True,
            "churn_prediction": result
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Churn prediction failed",
            "message": str(e)
        }), 500


@prediction_bp.route("/api/customers/<string:customer_id>/clv", methods=["GET"])
def get_clv_prediction(customer_id):
    """Predicts Customer Lifetime Value using ML model."""
    try:
        customer = Customer.query.get(customer_id)
        if not customer:
            return jsonify({
                "success": False,
                "error": f"Customer '{customer_id}' not found"
            }), 404

        result = predict_clv(customer_id)
        return jsonify({
            "success": True,
            "clv_prediction": result
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "CLV prediction failed",
            "message": str(e)
        }), 500


@prediction_bp.route("/api/segments", methods=["GET"])
def get_segments():
    """
    Segments ALL customers into groups:
    High Value, Regular, New, Inactive, High Risk.
    Returns counts, percentages, and full customer lists per segment.
    """
    try:
        result = get_all_segments()
        return jsonify({
            "success": True,
            "segmentation": result
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Segmentation failed",
            "message": str(e)
        }), 500


@prediction_bp.route("/api/customers/<string:customer_id>/segment", methods=["GET"])
def get_single_segment(customer_id):
    """Returns the segment for one specific customer."""
    try:
        result = get_customer_segment(customer_id)
        if not result:
            return jsonify({
                "success": False,
                "error": f"Customer '{customer_id}' not found"
            }), 404
        return jsonify({
            "success": True,
            "segment_info": result
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Segment lookup failed",
            "message": str(e)
        }), 500


# ============================================================
# ROUTE: GET /api/customers/<customer_id>/insights
# ============================================================
# PURPOSE : Full AI intelligence report for ONE customer
# METHOD  : GET
# URL     : http://localhost:5000/api/customers/C1001/insights
#
# This is the MOST POWERFUL endpoint — it combines:
#   behaviour + churn + CLV + segment + health score +
#   AI summary + recommendations → all in one response
# ============================================================

@prediction_bp.route("/api/customers/<string:customer_id>/insights", methods=["GET"])
def get_insights(customer_id):
    """
    Returns a complete AI-powered intelligence report
    combining all predictions and analysis for one customer.
    """
    try:
        customer = Customer.query.get(customer_id)
        if not customer:
            return jsonify({
                "success": False,
                "error": f"Customer '{customer_id}' not found"
            }), 404

        result = get_customer_insights(customer_id)
        return jsonify({
            "success": True,
            "intelligence_report": result
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Failed to generate insights",
            "message": str(e)
        }), 500
