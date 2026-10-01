# ============================================================
# services/analytics_service.py — Customer Data Analysis
# ============================================================
# This file contains all the data analysis logic.
#
# WHY A SEPARATE SERVICE FILE?
#   Routes (in routes/) handle HTTP — receiving requests and
#   sending responses. They should stay clean and simple.
#   The actual calculations belong in a 'service' file.
#   This makes the code easier to read, test, and reuse.
#
# WHAT THIS FILE DOES:
#   - Calculates customer behavior metrics
#   - Computes recency, frequency, monetary values (RFM)
#   - Generates rule-based AI insights
#   - Provides summary statistics
# ============================================================

from datetime import date, timedelta
from models.customer import Customer
from models.purchase import Purchase
from extensions import db
from sqlalchemy import func


# ============================================================
# FUNCTION 1: Analyze a Single Customer's Behavior
# ============================================================

def analyze_customer_behavior(customer_id):
    """
    Analyzes a single customer's purchase behavior.

    Returns a dictionary with:
      - Basic metrics (orders, spend, avg order value)
      - Recency (how recently they bought)
      - Frequency label (High / Medium / Low)
      - Favorite category
      - Spending trend label
      - AI-generated insight text

    Args:
        customer_id (str): The customer's ID (e.g., "C1001")

    Returns:
        dict: Behavior analysis results, or None if not found
    """

    # --- Fetch customer from database ---
    customer = db.session.get(Customer, customer_id)
    if not customer:
        return None

    today = date.today()

    # --------------------------------------------------------
    # STEP 1: Calculate Recency
    # Recency = how many days since their last purchase
    # Lower number = more recent = better engagement
    # --------------------------------------------------------
    if customer.last_purchase_date:
        days_since_last_purchase = (today - customer.last_purchase_date).days
    else:
        days_since_last_purchase = None  # Never purchased

    # Assign a recency label based on days
    if days_since_last_purchase is None:
        recency_label = "Never Purchased"
    elif days_since_last_purchase <= 30:
        recency_label = "Very Recent"          # Bought within 1 month
    elif days_since_last_purchase <= 90:
        recency_label = "Recent"               # Bought within 3 months
    elif days_since_last_purchase <= 180:
        recency_label = "Moderate"             # Bought within 6 months
    elif days_since_last_purchase <= 365:
        recency_label = "Lapsed"               # Bought within 1 year
    else:
        recency_label = "Long Inactive"        # No purchase in 1+ year

    # --------------------------------------------------------
    # STEP 2: Calculate Frequency Label
    # Frequency = number of orders placed
    # More orders = more engaged customer
    # --------------------------------------------------------
    orders = customer.total_orders or 0

    if orders == 0:
        frequency_label = "No Purchases"
    elif orders <= 2:
        frequency_label = "Low"
    elif orders <= 8:
        frequency_label = "Medium"
    elif orders <= 20:
        frequency_label = "High"
    else:
        frequency_label = "Very High"

    # --------------------------------------------------------
    # STEP 3: Spending Level
    # Based on total spend, classify into tiers
    # --------------------------------------------------------
    spend = customer.total_spend or 0

    if spend == 0:
        spending_level = "No Spending"
    elif spend < 10000:
        spending_level = "Low Spender"
    elif spend < 50000:
        spending_level = "Medium Spender"
    elif spend < 100000:
        spending_level = "High Spender"
    else:
        spending_level = "Premium Spender"

    # --------------------------------------------------------
    # STEP 4: Favorite Product Category
    # We query the purchases table to find which category
    # this customer buys from most often
    # --------------------------------------------------------
    top_category_result = db.session.query(
        Purchase.product_category,
        func.count(Purchase.purchase_id).label("count")
    ).filter(
        Purchase.customer_id == customer_id
    ).group_by(
        Purchase.product_category
    ).order_by(
        func.count(Purchase.purchase_id).desc()
    ).first()

    favorite_category = top_category_result[0] if top_category_result else "N/A"

    # --------------------------------------------------------
    # STEP 5: Recent Purchases (last 3 purchases)
    # --------------------------------------------------------
    recent_purchases = Purchase.query.filter_by(
        customer_id=customer_id
    ).order_by(
        Purchase.purchase_date.desc()
    ).limit(3).all()

    recent_purchases_list = [p.to_dict() for p in recent_purchases]

    # --------------------------------------------------------
    # STEP 6: Purchase Frequency per Month
    # --------------------------------------------------------
    if customer.last_purchase_date and orders > 0:
        # How many months has this customer been active?
        first_purchase_query = db.session.query(
            func.min(Purchase.purchase_date)
        ).filter(Purchase.customer_id == customer_id).scalar()

        if first_purchase_query:
            days_as_customer = (today - first_purchase_query).days
            months_as_customer = max(days_as_customer / 30, 1)  # Minimum 1 month
            purchases_per_month = round(orders / months_as_customer, 2)
        else:
            purchases_per_month = 0
    else:
        purchases_per_month = 0

    # --------------------------------------------------------
    # STEP 7: Rule-Based AI Insight
    # We combine all metrics to generate a human-readable
    # insight about this customer — like a mini report card
    # --------------------------------------------------------
    insight = generate_customer_insight(
        customer=customer,
        days_since_last_purchase=days_since_last_purchase,
        frequency_label=frequency_label,
        spending_level=spending_level,
        favorite_category=favorite_category
    )

    # --------------------------------------------------------
    # Return all results as a dictionary
    # --------------------------------------------------------
    return {
        "customer_id": customer_id,
        "name": customer.name,

        # Basic metrics
        "total_orders": orders,
        "total_spend": spend,
        "average_order_value": customer.average_order_value or 0,

        # Recency
        "last_purchase_date": (
            customer.last_purchase_date.isoformat()
            if customer.last_purchase_date else None
        ),
        "days_since_last_purchase": days_since_last_purchase,
        "recency_label": recency_label,

        # Frequency
        "frequency_label": frequency_label,
        "purchases_per_month": purchases_per_month,

        # Spending
        "spending_level": spending_level,

        # Behavior
        "favorite_category": favorite_category,
        "website_visits": customer.website_visits or 0,
        "complaints": customer.complaints or 0,
        "subscription_status": customer.subscription_status,

        # Recent activity
        "recent_purchases": recent_purchases_list,

        # AI Insight
        "insight": insight,
    }


# ============================================================
# FUNCTION 2: Generate Rule-Based AI Insight
# ============================================================

def generate_customer_insight(
    customer, days_since_last_purchase,
    frequency_label, spending_level, favorite_category
):
    """
    Generates a human-readable insight about a customer
    using simple rules based on their metrics.

    This is RULE-BASED — not an AI model — but it produces
    useful, readable summaries. We can upgrade to an LLM later.

    Args:
        customer: Customer database object
        days_since_last_purchase: int or None
        frequency_label: str ("High", "Low", etc.)
        spending_level: str ("Premium Spender", etc.)
        favorite_category: str

    Returns:
        str: A human-readable insight paragraph
    """
    insights = []
    name = customer.name.split()[0]  # Use first name only

    # --- Recency insight ---
    if days_since_last_purchase is None:
        insights.append(
            f"{name} has never made a purchase yet. "
            "Consider sending a welcome offer to encourage the first purchase."
        )
    elif days_since_last_purchase <= 30:
        insights.append(
            f"{name} is a highly active customer, having purchased within the last "
            f"{days_since_last_purchase} days."
        )
    elif days_since_last_purchase <= 90:
        insights.append(
            f"{name} purchased {days_since_last_purchase} days ago and remains engaged."
        )
    elif days_since_last_purchase <= 365:
        insights.append(
            f"{name}'s last purchase was {days_since_last_purchase} days ago. "
            "Activity is declining — re-engagement recommended."
        )
    else:
        insights.append(
            f"{name} has been inactive for over {days_since_last_purchase} days. "
            "High churn risk — immediate intervention needed."
        )

    # --- Frequency insight ---
    if frequency_label in ["High", "Very High"]:
        insights.append(
            f"With {customer.total_orders} total orders, {name} is a frequent buyer."
        )
    elif frequency_label == "Low":
        insights.append(
            f"{name} has only placed {customer.total_orders} orders. "
            "Low engagement — consider loyalty incentives."
        )

    # --- Spending insight ---
    if spending_level == "Premium Spender":
        insights.append(
            f"As a premium spender (₹{customer.total_spend:,.0f} total), "
            f"{name} is one of the most valuable customers."
        )
    elif spending_level == "High Spender":
        insights.append(
            f"{name} has spent ₹{customer.total_spend:,.0f} — a high-value customer."
        )
    elif spending_level == "No Spending":
        insights.append(
            f"{name} has not made any purchases yet."
        )

    # --- Category insight ---
    if favorite_category and favorite_category != "N/A":
        insights.append(
            f"Favorite product category: {favorite_category}. "
            "Targeted promotions in this category may drive repeat purchases."
        )

    # --- Complaints insight ---
    if customer.complaints and customer.complaints >= 3:
        insights.append(
            f"⚠️ {name} has filed {customer.complaints} complaints. "
            "Urgent customer support attention is recommended."
        )
    elif customer.complaints and customer.complaints >= 1:
        insights.append(
            f"{name} has {customer.complaints} complaint(s) on record."
        )

    # --- Subscription insight ---
    if customer.subscription_status in ["Inactive", "Cancelled"]:
        insights.append(
            f"Subscription status is '{customer.subscription_status}'. "
            "Win-back campaign may help re-activate this customer."
        )
    elif customer.subscription_status == "Premium":
        insights.append(f"{name} holds a Premium subscription — a loyal customer.")

    # Join all insights into one paragraph
    return " ".join(insights)


# ============================================================
# FUNCTION 3: Get Summary Stats for All Customers
# ============================================================

def get_all_customers_analysis():
    """
    Performs a quick analysis on all customers in the database.
    Used to generate summary metrics for the dashboard.

    Returns:
        dict: Summary statistics across all customers
    """
    customers = Customer.query.all()
    today = date.today()

    if not customers:
        return {"error": "No customers found"}

    total_spend_list = [c.total_spend or 0 for c in customers]
    total_orders_list = [c.total_orders or 0 for c in customers]

    # Days since last purchase for each customer
    recency_list = []
    for c in customers:
        if c.last_purchase_date:
            recency_list.append((today - c.last_purchase_date).days)

    avg_recency = round(sum(recency_list) / len(recency_list), 1) if recency_list else None

    return {
        "total_customers_analyzed": len(customers),
        "total_revenue": round(sum(total_spend_list), 2),
        "average_spend_per_customer": round(
            sum(total_spend_list) / len(total_spend_list), 2
        ),
        "max_spend": max(total_spend_list),
        "min_spend": min(total_spend_list),
        "average_orders_per_customer": round(
            sum(total_orders_list) / len(total_orders_list), 2
        ),
        "average_days_since_last_purchase": avg_recency,
        "customers_with_complaints": sum(
            1 for c in customers if (c.complaints or 0) > 0
        ),
        "customers_never_purchased": sum(
            1 for c in customers if (c.total_orders or 0) == 0
        ),
    }
