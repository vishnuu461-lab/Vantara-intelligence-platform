# ============================================================
# routes/dashboard_routes.py — Dashboard Summary API
# ============================================================
# This file provides the main dashboard data endpoint.
#
# API ENDPOINT:
#   GET /api/dashboard  → Returns business summary statistics
#
# This is the FIRST thing your frontend will call when it
# loads the dashboard page.
# ============================================================

from flask import Blueprint, jsonify
from extensions import db
from models.customer import Customer
from models.purchase import Purchase
from sqlalchemy import func
from datetime import date, timedelta

dashboard_bp = Blueprint("dashboard_bp", __name__)


# ============================================================
# ROUTE: GET /api/dashboard
# ============================================================
# PURPOSE : Returns complete summary statistics for the
#           business dashboard
# METHOD  : GET
# URL     : http://localhost:5000/api/dashboard
# ============================================================

@dashboard_bp.route("/api/dashboard", methods=["GET"])
def get_dashboard():
    """
    Returns a complete summary of business metrics.

    This single endpoint gives the frontend everything it
    needs to display the main dashboard at a glance.
    """
    try:
        today = date.today()

        # --------------------------------------------------------
        # 1. CUSTOMER COUNT METRICS
        # --------------------------------------------------------

        # Total number of customers in the database
        total_customers = Customer.query.count()

        # Active customers = subscription_status is 'Active' or 'Premium'
        active_customers = Customer.query.filter(
            Customer.subscription_status.in_(["Active", "Premium"])
        ).count()

        # Inactive customers = 'Inactive' or 'Cancelled'
        inactive_customers = Customer.query.filter(
            Customer.subscription_status.in_(["Inactive", "Cancelled"])
        ).count()

        # Premium customers specifically
        premium_customers = Customer.query.filter_by(
            subscription_status="Premium"
        ).count()

        # New customers = joined in the last 30 days
        thirty_days_ago = today - timedelta(days=30)
        new_customers = Customer.query.filter(
            Customer.created_at >= thirty_days_ago
        ).count()

        # --------------------------------------------------------
        # 2. REVENUE METRICS
        # --------------------------------------------------------

        # Total revenue = sum of all customer spend
        # func.sum() is SQLAlchemy's way of doing SQL SUM()
        total_revenue_result = db.session.query(
            func.sum(Customer.total_spend)
        ).scalar()
        # .scalar() returns a single value (not a list)
        total_revenue = round(total_revenue_result or 0, 2)
        # 'or 0' handles the case where there are no customers

        # Average spend per customer
        avg_customer_spend = round(
            total_revenue / total_customers if total_customers > 0 else 0, 2
        )

        # Average order value across all customers
        avg_order_value_result = db.session.query(
            func.avg(Customer.average_order_value)
        ).scalar()
        avg_order_value = round(avg_order_value_result or 0, 2)

        # Total number of orders across all customers
        total_orders_result = db.session.query(
            func.sum(Customer.total_orders)
        ).scalar()
        total_orders = int(total_orders_result or 0)

        # --------------------------------------------------------
        # 3. HIGH RISK CUSTOMERS (Churn Risk)
        # --------------------------------------------------------
        # Rule-based identification (before ML model is ready):
        # A customer is HIGH RISK if they have:
        #   - No purchase in last 90 days  AND
        #   - At least 1 complaint  OR  Inactive/Cancelled status
        ninety_days_ago = today - timedelta(days=90)

        high_risk_customers = Customer.query.filter(
            db.or_(
                # Risk condition 1: inactive status with complaints
                db.and_(
                    Customer.subscription_status.in_(["Inactive", "Cancelled"]),
                    Customer.complaints >= 1
                ),
                # Risk condition 2: no purchase for 90+ days
                db.and_(
                    Customer.last_purchase_date <= ninety_days_ago,
                    Customer.last_purchase_date.isnot(None)
                )
            )
        ).count()

        # --------------------------------------------------------
        # 4. HIGH VALUE CUSTOMERS
        # --------------------------------------------------------
        # A customer is HIGH VALUE if their total spend is in
        # the top tier — above Rs. 50,000
        high_value_threshold = 50000.0
        high_value_customers = Customer.query.filter(
            Customer.total_spend >= high_value_threshold
        ).count()

        # --------------------------------------------------------
        # 5. PURCHASE METRICS
        # --------------------------------------------------------

        # Total purchase transactions in the purchases table
        total_transactions = Purchase.query.count()

        # Most popular product category (most purchased)
        top_category_result = db.session.query(
            Purchase.product_category,
            func.count(Purchase.purchase_id).label("count")
        ).group_by(Purchase.product_category)\
         .order_by(func.count(Purchase.purchase_id).desc())\
         .first()

        top_category = top_category_result[0] if top_category_result else "N/A"

        # Total revenue from the purchases table directly
        purchases_revenue_result = db.session.query(
            func.sum(Purchase.amount)
        ).scalar()
        purchases_revenue = round(purchases_revenue_result or 0, 2)

        # --------------------------------------------------------
        # 6. LOCATION BREAKDOWN (Top 5 cities)
        # --------------------------------------------------------
        location_data = db.session.query(
            Customer.location,
            func.count(Customer.customer_id).label("count")
        ).group_by(Customer.location)\
         .order_by(func.count(Customer.customer_id).desc())\
         .limit(5)\
         .all()

        top_locations = [
            {"location": row[0], "customer_count": row[1]}
            for row in location_data
        ]

        # --------------------------------------------------------
        # 7. GENDER BREAKDOWN
        # --------------------------------------------------------
        gender_data = db.session.query(
            Customer.gender,
            func.count(Customer.customer_id).label("count")
        ).group_by(Customer.gender).all()

        gender_breakdown = {
            row[0]: row[1] for row in gender_data if row[0]
        }

        # --------------------------------------------------------
        # BUILD THE FINAL RESPONSE
        # --------------------------------------------------------
        return jsonify({
            "success": True,
            "dashboard": {

                # --- Customer Overview ---
                "customer_overview": {
                    "total_customers": total_customers,
                    "active_customers": active_customers,
                    "inactive_customers": inactive_customers,
                    "premium_customers": premium_customers,
                    "new_customers_last_30_days": new_customers,
                },

                # --- Revenue Summary ---
                "revenue_summary": {
                    "total_revenue": total_revenue,
                    "average_customer_spend": avg_customer_spend,
                    "average_order_value": avg_order_value,
                    "total_orders": total_orders,
                    "total_transactions": total_transactions,
                    "purchases_revenue": purchases_revenue,
                },

                # --- Risk & Value Indicators ---
                "risk_and_value": {
                    "high_risk_customers": high_risk_customers,
                    "high_value_customers": high_value_customers,
                    "high_value_threshold": f"Spend above Rs.{high_value_threshold:,.0f}",
                },

                # --- Purchase Insights ---
                "purchase_insights": {
                    "top_product_category": top_category,
                    "top_locations": top_locations,
                    "gender_breakdown": gender_breakdown,
                },

                # --- Meta Info ---
                "generated_at": today.isoformat(),
                "note": "Dashboard data is calculated in real-time from the database."
            }
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Failed to load dashboard data",
            "message": str(e)
        }), 500
