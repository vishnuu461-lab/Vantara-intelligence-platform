# ============================================================
# services/insights_service.py — AI Customer Insights
# ============================================================
# This service combines ALL predictions and analysis into
# one unified customer intelligence report.
#
# It calls:
#   - analytics_service → behavior analysis
#   - churn_service     → churn probability
#   - clv_service       → lifetime value prediction
#   - segmentation_service → customer segment
#
# Then it generates a smart, human-readable insight summary
# using rule-based logic.
#
# WHY RULE-BASED AND NOT AN LLM?
#   - No external API cost or dependency
#   - Works offline
#   - Fully explainable (important for business decisions)
#   - You can upgrade to an LLM later with one function swap
# ============================================================

from models.customer import Customer
from extensions import db
from services.analytics_service import analyze_customer_behavior
from services.churn_service import predict_churn
from services.clv_service import predict_clv
from services.segmentation_service import assign_segment


# ============================================================
# MAIN FUNCTION: Full Customer Intelligence Report
# ============================================================

def get_customer_insights(customer_id):
    """
    Generates a complete AI-powered intelligence report
    for a single customer by combining all available data.

    Args:
        customer_id (str): e.g., "C1001"

    Returns:
        dict: Full intelligence report, or None if not found
    """
    # --- Fetch customer ---
    customer = db.session.get(Customer, customer_id)
    if not customer:
        return None

    # --------------------------------------------------------
    # STEP 1: Gather all analysis results
    # --------------------------------------------------------

    # Behavior analysis (recency, frequency, spending level, etc.)
    behavior = analyze_customer_behavior(customer_id)

    # Churn prediction (churn probability + risk level)
    churn = predict_churn(customer_id)

    # CLV prediction (predicted lifetime value + tier)
    clv = predict_clv(customer_id)

    # Segment (High Value, Regular, New, Inactive, High Risk)
    segment_info = assign_segment(customer)

    # --------------------------------------------------------
    # STEP 2: Extract key signals for the AI summary
    # --------------------------------------------------------

    churn_prob   = churn.get("churn_probability", 0) if churn else 0
    risk_level   = churn.get("risk_level", "Unknown") if churn else "Unknown"
    clv_value    = clv.get("predicted_clv", 0) if clv else 0
    clv_tier     = clv.get("clv_tier", "Unknown") if clv else "Unknown"
    segment      = segment_info.get("segment", "Unknown")
    freq_label   = behavior.get("frequency_label", "Unknown") if behavior else "Unknown"
    spend_level  = behavior.get("spending_level", "Unknown") if behavior else "Unknown"
    days_inactive = behavior.get("days_since_last_purchase") if behavior else None
    fav_category = behavior.get("favorite_category", "N/A") if behavior else "N/A"
    complaints   = customer.complaints or 0

    # --------------------------------------------------------
    # STEP 3: Generate AI Summary Paragraph
    # --------------------------------------------------------
    summary = generate_ai_summary(
        customer=customer,
        risk_level=risk_level,
        churn_prob=churn_prob,
        clv_tier=clv_tier,
        clv_value=clv_value,
        segment=segment,
        freq_label=freq_label,
        spend_level=spend_level,
        days_inactive=days_inactive,
        fav_category=fav_category,
        complaints=complaints
    )

    # --------------------------------------------------------
    # STEP 4: Generate Recommendations
    # --------------------------------------------------------
    recommendations = generate_recommendations(
        risk_level=risk_level,
        clv_tier=clv_tier,
        segment=segment,
        freq_label=freq_label,
        complaints=complaints,
        days_inactive=days_inactive,
        fav_category=fav_category
    )

    # --------------------------------------------------------
    # STEP 5: Calculate overall customer health score (0-100)
    # --------------------------------------------------------
    health_score = calculate_health_score(
        churn_prob=churn_prob,
        freq_label=freq_label,
        complaints=complaints,
        days_inactive=days_inactive,
        subscription_status=customer.subscription_status
    )

    # --------------------------------------------------------
    # STEP 6: Build and return the full report
    # --------------------------------------------------------
    return {
        "customer_id":   customer_id,
        "name":          customer.name,
        "email":         customer.email,
        "location":      customer.location,
        "subscription":  customer.subscription_status,

        # AI Summary — the star of the show
        "ai_summary": summary,

        # Health Score
        "health_score": health_score,
        "health_label": get_health_label(health_score),

        # All predictions in one place
        "predictions": {
            "churn": {
                "probability":  churn_prob,
                "percentage":   f"{churn_prob * 100:.1f}%",
                "risk_level":   risk_level,
                "risk_color":   churn.get("risk_color", "gray") if churn else "gray",
            },
            "clv": {
                "predicted_value":   clv_value,
                "formatted":         f"Rs.{clv_value:,.0f}",
                "tier":              clv_tier,
                "tier_color":        clv.get("clv_color", "gray") if clv else "gray",
            },
            "segment": {
                "name":    segment,
                "code":    segment_info.get("segment_code", ""),
                "color":   segment_info.get("color", "#999"),
                "reason":  segment_info.get("reason", ""),
            }
        },

        # Behavior summary
        "behavior_summary": {
            "frequency":          freq_label,
            "spending_level":     spend_level,
            "days_since_purchase": days_inactive,
            "favorite_category":  fav_category,
            "total_orders":       customer.total_orders or 0,
            "total_spend":        customer.total_spend or 0,
        },

        # Actionable recommendations
        "recommendations": recommendations,

        # Metadata
        "report_generated": __import__("datetime").date.today().isoformat(),
        "disclaimer": (
            "This report uses ML predictions and rule-based analysis. "
            "Human judgment should supplement automated insights for "
            "important business decisions."
        )
    }


# ============================================================
# HELPER: Generate AI Summary Paragraph
# ============================================================

def generate_ai_summary(
    customer, risk_level, churn_prob, clv_tier, clv_value,
    segment, freq_label, spend_level, days_inactive,
    fav_category, complaints
):
    """
    Generates a professional, human-readable summary paragraph
    about a customer combining all available signals.
    """
    name = customer.name.split()[0]  # First name only
    parts = []

    # --- Opening: Who is this customer? ---
    if segment == "High Value":
        parts.append(
            f"{name} is one of Vantara's most valuable customers, "
            f"classified in the High Value segment."
        )
    elif segment == "High Risk":
        parts.append(
            f"{name} is currently flagged as a High Risk customer "
            f"requiring immediate attention."
        )
    elif segment == "New":
        parts.append(
            f"{name} is a recently acquired customer still in the "
            f"early stages of their journey."
        )
    elif segment == "Inactive":
        parts.append(
            f"{name} is currently inactive, with no recent purchasing activity."
        )
    else:
        parts.append(
            f"{name} is a Regular customer showing steady engagement."
        )

    # --- Churn Risk ---
    if risk_level == "High":
        parts.append(
            f"The churn model predicts a {churn_prob*100:.0f}% probability "
            f"of churn — this customer is at serious risk of leaving."
        )
    elif risk_level == "Medium":
        parts.append(
            f"There is a moderate churn risk ({churn_prob*100:.0f}%), "
            f"suggesting declining engagement that needs monitoring."
        )
    else:
        parts.append(
            f"Churn risk is low ({churn_prob*100:.0f}%), "
            f"indicating a stable and engaged relationship."
        )

    # --- CLV ---
    if clv_tier in ["Platinum", "Gold"]:
        parts.append(
            f"Predicted Customer Lifetime Value is Rs.{clv_value:,.0f} "
            f"({clv_tier} tier) — a high-priority customer for retention."
        )
    elif clv_tier in ["Silver", "Bronze"]:
        parts.append(
            f"Estimated CLV is Rs.{clv_value:,.0f} ({clv_tier} tier), "
            f"with potential to grow with the right engagement strategy."
        )
    else:
        parts.append(
            f"Predicted CLV is Rs.{clv_value:,.0f}, currently low "
            f"but improvable with targeted offers."
        )

    # --- Activity ---
    if days_inactive is None:
        parts.append("No purchase history on record yet.")
    elif days_inactive <= 30:
        parts.append(
            f"Very recently active — last purchase just {days_inactive} days ago."
        )
    elif days_inactive <= 90:
        parts.append(f"Active within the last 3 months ({days_inactive} days ago).")
    elif days_inactive > 365:
        parts.append(
            f"Customer has been inactive for {days_inactive} days — "
            f"re-engagement is urgently needed."
        )

    # --- Purchase pattern ---
    if fav_category and fav_category != "N/A":
        parts.append(
            f"Strongest interest is in {fav_category} products."
        )

    # --- Complaints ---
    if complaints >= 3:
        parts.append(
            f"With {complaints} complaints recorded, customer satisfaction "
            f"is a concern that needs direct attention."
        )
    elif complaints >= 1:
        parts.append(f"{complaints} complaint(s) on record.")

    return " ".join(parts)


# ============================================================
# HELPER: Generate Actionable Recommendations
# ============================================================

def generate_recommendations(
    risk_level, clv_tier, segment, freq_label,
    complaints, days_inactive, fav_category
):
    """
    Returns a list of specific, actionable business recommendations.
    """
    recs = []

    # Churn-based recommendations
    if risk_level == "High":
        recs.append({
            "priority": "🔴 URGENT",
            "action": "Personal outreach",
            "detail": (
                "Assign a customer success representative to contact "
                "this customer personally within 24 hours."
            )
        })
        recs.append({
            "priority": "🔴 URGENT",
            "action": "Retention offer",
            "detail": (
                "Offer a special discount (15-20%) or loyalty reward "
                "to re-engage this customer immediately."
            )
        })
    elif risk_level == "Medium":
        recs.append({
            "priority": "🟡 MODERATE",
            "action": "Re-engagement campaign",
            "detail": (
                "Send a personalized email with product recommendations "
                "based on past purchase history within this week."
            )
        })

    # CLV-based recommendations
    if clv_tier in ["Platinum", "Gold"]:
        recs.append({
            "priority": "🟢 OPPORTUNITY",
            "action": "VIP Programme enrollment",
            "detail": (
                "Invite this high-value customer to an exclusive VIP "
                "membership with early access to new products."
            )
        })

    # Complaint-based
    if complaints >= 2:
        recs.append({
            "priority": "🔴 URGENT",
            "action": "Customer service escalation",
            "detail": (
                f"Review {complaints} past complaint(s) and proactively "
                "resolve them. Offer compensation if appropriate."
            )
        })

    # Category-based upsell
    if fav_category and fav_category != "N/A":
        recs.append({
            "priority": "🟢 OPPORTUNITY",
            "action": f"Targeted {fav_category} promotion",
            "detail": (
                f"Send a curated {fav_category} product recommendation "
                f"email — this is their preferred category."
            )
        })

    # Frequency-based
    if freq_label in ["Low", "No Purchases"]:
        recs.append({
            "priority": "🟡 MODERATE",
            "action": "First/repeat purchase incentive",
            "detail": (
                "Offer a time-limited discount (e.g., 10% off next order) "
                "to encourage more frequent purchasing."
            )
        })

    # Default if no recommendations triggered
    if not recs:
        recs.append({
            "priority": "🟢 ROUTINE",
            "action": "Maintain engagement",
            "detail": (
                "Customer is healthy. Continue regular communication "
                "through newsletters and seasonal promotions."
            )
        })

    return recs


# ============================================================
# HELPER: Customer Health Score (0 to 100)
# ============================================================

def calculate_health_score(
    churn_prob, freq_label, complaints,
    days_inactive, subscription_status
):
    """
    Calculates a single 0-100 health score for a customer.
    Higher = healthier relationship.

    Components:
       Churn risk (40 pts) + Frequency (25 pts) +
       Recency (20 pts) + Complaints (15 pts)
    """
    score = 100

    # Churn risk penalty (up to -40)
    score -= int(churn_prob * 40)

    # Frequency penalty
    if freq_label == "No Purchases":   score -= 25
    elif freq_label == "Low":          score -= 15
    elif freq_label == "Medium":       score -= 5
    # High / Very High: no penalty

    # Recency penalty
    if days_inactive is None:           score -= 20
    elif days_inactive > 365:           score -= 20
    elif days_inactive > 180:           score -= 12
    elif days_inactive > 90:            score -= 5
    # Within 90 days: no penalty

    # Complaint penalty
    if complaints >= 4:    score -= 15
    elif complaints >= 2:  score -= 8
    elif complaints >= 1:  score -= 3

    # Subscription bonus/penalty
    if subscription_status == "Premium":           score += 5
    elif subscription_status in ["Inactive", "Cancelled"]: score -= 5

    return max(0, min(100, score))  # Keep between 0 and 100


def get_health_label(score):
    """Converts health score to a human-readable label."""
    if score >= 80: return "Excellent"
    elif score >= 60: return "Good"
    elif score >= 40: return "Fair"
    elif score >= 20: return "Poor"
    else: return "Critical"
