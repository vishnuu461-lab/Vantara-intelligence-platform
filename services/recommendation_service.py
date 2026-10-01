# ============================================================
# services/recommendation_service.py — Product Recommendation
# ============================================================
# Generates personalised product/category recommendations
# for each customer based on their purchase history.
#
# APPROACH:
#   1. Content-based: recommend categories/products the customer
#      hasn't tried but are popular among similar customers.
#   2. Collaborative: customers who bought X also bought Y.
#   3. Fallback: bestselling categories.
#
# IMPORTANT: No future data is used — pure history-based.
# ============================================================

from collections import Counter, defaultdict
from models.customer import Customer
from models.purchase import Purchase
from extensions import db
from sqlalchemy import func


def _get_customer_categories(customer_id: str) -> set:
    """Return the set of categories this customer has bought."""
    rows = db.session.query(Purchase.product_category).filter(
        Purchase.customer_id == customer_id
    ).all()
    return {r[0] for r in rows if r[0]}


def _get_global_bestsellers(top_n: int = 6) -> list[dict]:
    """Return the most purchased categories across all customers."""
    rows = db.session.query(
        Purchase.product_category,
        func.count(Purchase.purchase_id).label("cnt")
    ).group_by(Purchase.product_category).order_by(
        func.count(Purchase.purchase_id).desc()
    ).limit(top_n).all()

    return [{"category": r[0], "purchase_count": r[1], "source": "bestseller"}
            for r in rows if r[0]]


def _collaborative_recs(customer_id: str, bought: set, top_n: int = 4) -> list[dict]:
    """
    Find customers who share at least one category with this customer
    and recommend categories they bought that this customer hasn't.
    """
    if not bought:
        return []

    # Find other customers who bought at least one of the same categories
    similar_customers = db.session.query(
        Purchase.customer_id
    ).filter(
        Purchase.product_category.in_(bought),
        Purchase.customer_id != customer_id
    ).distinct().all()

    similar_ids = [r[0] for r in similar_customers]
    if not similar_ids:
        return []

    # Get all categories bought by similar customers
    recs = db.session.query(
        Purchase.product_category,
        func.count(Purchase.purchase_id).label("cnt")
    ).filter(
        Purchase.customer_id.in_(similar_ids),
        Purchase.product_category.notin_(bought)
    ).group_by(Purchase.product_category).order_by(
        func.count(Purchase.purchase_id).desc()
    ).limit(top_n).all()

    return [{"category": r[0], "purchase_count": r[1], "source": "collaborative"}
            for r in recs if r[0]]


def get_recommendations(customer_id: str, top_n: int = 5) -> dict:
    """
    Generate personalised product category recommendations for a customer.

    Returns:
        {
          customer_id, name,
          already_purchased: [...],
          recommendations: [
            { category, source, purchase_count, reason }
          ]
        }
    """
    customer = db.session.get(Customer, customer_id)
    if not customer:
        return {"error": f"Customer {customer_id} not found"}

    bought = _get_customer_categories(customer_id)

    # Try collaborative first
    collab = _collaborative_recs(customer_id, bought, top_n=top_n)

    # Fill remaining slots from bestsellers (excluding already-bought + already in collab)
    collab_cats = {r["category"] for r in collab}
    bestsellers = [
        b for b in _get_global_bestsellers(top_n=10)
        if b["category"] not in bought and b["category"] not in collab_cats
    ]

    # Merge — collaborative recs first, then bestsellers
    combined = collab + bestsellers
    final = combined[:top_n]

    # Add human-readable reason
    for rec in final:
        if rec["source"] == "collaborative":
            rec["reason"] = (
                f"Customers with similar purchase patterns frequently buy "
                f"{rec['category']} products."
            )
        else:
            rec["reason"] = (
                f"{rec['category']} is among the most popular product "
                f"categories on the platform."
            )

    return {
        "customer_id":       customer_id,
        "name":              customer.name,
        "already_purchased": sorted(bought),
        "recommendations":   final,
        "recommendation_count": len(final),
        "method": "collaborative" if collab else "bestseller-fallback",
    }
