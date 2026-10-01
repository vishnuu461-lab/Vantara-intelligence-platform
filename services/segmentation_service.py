# ============================================================
# services/segmentation_service.py — Customer Segmentation
# ============================================================
# This file segments ALL customers into meaningful groups.
#
# APPROACH: Rule-Based Segmentation
#   We assign each customer a segment based on clear rules.
#   This is easy to understand, explain, and adjust.
#
# WHY NOT PURE K-MEANS FIRST?
#   K-Means is unsupervised — it groups based on patterns but
#   doesn't give meaningful names to groups automatically.
#   Rule-based is more explainable for a first version.
#   We add K-Means as an ADDITIONAL analysis layer below.
#
# SEGMENTS:
#   - High Value   : Top spenders with frequent purchases
#   - Regular      : Steady buyers, moderate engagement
#   - New          : Joined recently, few orders
#   - Inactive     : Long time since last purchase
#   - High Risk    : Complaints + inactive/cancelled subscription
# ============================================================

from datetime import date, timedelta
from models.customer import Customer
from extensions import db


# ============================================================
# SEGMENT RULES — All the logic is defined here clearly
# ============================================================
# These thresholds are adjustable business decisions.
# Change them if your business defines segments differently.

HIGH_VALUE_SPEND_THRESHOLD   = 50000   # Rs. minimum total spend
HIGH_VALUE_ORDERS_THRESHOLD  = 10      # Minimum orders
INACTIVE_DAYS_THRESHOLD      = 730     # No purchase for 2 years
NEW_CUSTOMER_ORDERS_THRESHOLD = 3      # 3 or fewer orders = new
HIGH_RISK_COMPLAINTS          = 2      # 2+ complaints = at risk


def assign_segment(customer):
    """
    Assigns a customer to exactly ONE segment using priority rules.

    Priority order (most urgent → least urgent):
    1. High Risk (checked first — needs immediate action)
    2. Inactive  (no purchase for 6+ months)
    3. High Value (top spenders)
    4. New       (very few orders)
    5. Regular   (everyone else)

    Args:
        customer: Customer database object

    Returns:
        dict with segment name, color, and reason
    """
    today = date.today()

    # Calculate days since last purchase
    if customer.last_purchase_date:
        days_inactive = (today - customer.last_purchase_date).days
    else:
        days_inactive = 9999  # Never purchased → very inactive

    total_orders = customer.total_orders or 0
    total_spend  = customer.total_spend or 0
    complaints   = customer.complaints or 0
    status       = customer.subscription_status or "Active"

    # --------------------------------------------------------
    # RULE 1: HIGH RISK
    # High complaints AND (inactive or cancelled)
    # This checks FIRST because it's most urgent
    # --------------------------------------------------------
    is_inactive_status = status in ["Inactive", "Cancelled"]

    if complaints >= HIGH_RISK_COMPLAINTS and is_inactive_status:
        return {
            "segment": "High Risk",
            "segment_code": "HIGH_RISK",
            "color": "#e74c3c",   # Red
            "icon": "warning",
            "reason": (
                f"{complaints} complaints + {status} subscription. "
                "Immediate retention action required."
            ),
            "priority": 1
        }

    # Also mark as High Risk if many days inactive with complaints
    if complaints >= 1 and days_inactive >= INACTIVE_DAYS_THRESHOLD:
        return {
            "segment": "High Risk",
            "segment_code": "HIGH_RISK",
            "color": "#e74c3c",
            "icon": "warning",
            "reason": (
                f"Inactive for {days_inactive} days with {complaints} complaint(s). "
                "Customer at risk of permanent churn."
            ),
            "priority": 1
        }

    # --------------------------------------------------------
    # RULE 2: INACTIVE
    # No purchase for INACTIVE_DAYS_THRESHOLD days
    # --------------------------------------------------------
    if days_inactive >= INACTIVE_DAYS_THRESHOLD:
        return {
            "segment": "Inactive",
            "segment_code": "INACTIVE",
            "color": "#95a5a6",   # Gray
            "icon": "sleep",
            "reason": (
                f"No purchase for {days_inactive} days "
                f"(threshold: {INACTIVE_DAYS_THRESHOLD} days)."
            ),
            "priority": 2
        }

    # --------------------------------------------------------
    # RULE 3: HIGH VALUE
    # High total spend AND many orders
    # --------------------------------------------------------
    if (total_spend >= HIGH_VALUE_SPEND_THRESHOLD and
            total_orders >= HIGH_VALUE_ORDERS_THRESHOLD):
        return {
            "segment": "High Value",
            "segment_code": "HIGH_VALUE",
            "color": "#f39c12",   # Gold
            "icon": "star",
            "reason": (
                f"Total spend Rs.{total_spend:,.0f} "
                f"with {total_orders} orders — top-tier customer."
            ),
            "priority": 3
        }

    # --------------------------------------------------------
    # RULE 4: NEW CUSTOMER
    # Very few orders placed (still exploring)
    # --------------------------------------------------------
    if total_orders <= NEW_CUSTOMER_ORDERS_THRESHOLD:
        return {
            "segment": "New",
            "segment_code": "NEW",
            "color": "#3498db",   # Blue
            "icon": "new",
            "reason": (
                f"Only {total_orders} order(s) placed. "
                "Recently joined — nurture with welcome offers."
            ),
            "priority": 4
        }

    # --------------------------------------------------------
    # RULE 5: REGULAR (Default)
    # Steady customers who don't fit other segments
    # --------------------------------------------------------
    return {
        "segment": "Regular",
        "segment_code": "REGULAR",
        "color": "#2ecc71",   # Green
        "icon": "check",
        "reason": (
            f"{total_orders} orders, Rs.{total_spend:,.0f} total spend. "
            "Engaged regular customer."
        ),
        "priority": 5
    }


# ============================================================
# MAIN FUNCTION: Segment ALL Customers
# ============================================================

def get_all_segments():
    """
    Segments ALL customers in the database.

    Returns a dict containing:
      - summary: count and % per segment
      - customers_by_segment: each segment with its customers
      - all_customers: flat list with segment assigned
    """
    customers = Customer.query.all()

    if not customers:
        return {"error": "No customers found"}

    # Assign segment to each customer
    segmented = []
    for c in customers:
        seg_info = assign_segment(c)
        customer_data = c.to_dict()
        customer_data["segment"]      = seg_info["segment"]
        customer_data["segment_code"] = seg_info["segment_code"]
        customer_data["segment_color"]= seg_info["color"]
        customer_data["segment_reason"]= seg_info["reason"]
        segmented.append(customer_data)

    # Group customers by segment
    segment_names = ["High Value", "Regular", "New", "Inactive", "High Risk"]
    customers_by_segment = {}

    for seg_name in segment_names:
        group = [c for c in segmented if c["segment"] == seg_name]
        customers_by_segment[seg_name] = {
            "count": len(group),
            "percentage": round(len(group) / len(customers) * 100, 1),
            "customers": group
        }

    # Summary counts
    summary = {
        seg: {
            "count": customers_by_segment[seg]["count"],
            "percentage": customers_by_segment[seg]["percentage"],
            "color": next(
                (c["segment_color"] for c in segmented
                 if c["segment"] == seg), "#999"
            )
        }
        for seg in segment_names
    }

    return {
        "total_customers": len(customers),
        "summary": summary,
        "customers_by_segment": customers_by_segment,
        "segment_definitions": {
            "High Value":  f"Spend >= Rs.{HIGH_VALUE_SPEND_THRESHOLD:,} AND orders >= {HIGH_VALUE_ORDERS_THRESHOLD}",
            "Regular":     "Active buyers not in other segments",
            "New":         f"Total orders <= {NEW_CUSTOMER_ORDERS_THRESHOLD}",
            "Inactive":    f"No purchase for {INACTIVE_DAYS_THRESHOLD}+ days",
            "High Risk":   f"Complaints >= {HIGH_RISK_COMPLAINTS} + inactive/cancelled status OR inactive with complaint",
        },
        "generated_at": date.today().isoformat()
    }


# ============================================================
# SINGLE CUSTOMER SEGMENT
# ============================================================

def get_customer_segment(customer_id):
    """
    Returns the segment for a specific customer.

    Args:
        customer_id (str): e.g., "C1001"

    Returns:
        dict with segment info, or None if not found
    """
    customer = db.session.get(Customer, customer_id)
    if not customer:
        return None

    seg_info = assign_segment(customer)

    return {
        "customer_id": customer_id,
        "name": customer.name,
        "segment": seg_info["segment"],
        "segment_code": seg_info["segment_code"],
        "color": seg_info["color"],
        "reason": seg_info["reason"],
        "key_metrics": {
            "total_orders":   customer.total_orders or 0,
            "total_spend":    customer.total_spend or 0,
            "complaints":     customer.complaints or 0,
            "subscription":   customer.subscription_status,
            "last_purchase":  (
                customer.last_purchase_date.isoformat()
                if customer.last_purchase_date else "Never"
            )
        }
    }
