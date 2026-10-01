# ============================================================
# models/customer.py — Customer Database Table
# ============================================================
from datetime import datetime, timezone
from extensions import db   # Import db from extensions.py (not app.py)


class Customer(db.Model):
    """
    Represents a customer in the Vantara platform.
    Maps to the 'customers' table in MySQL.
    """

    __tablename__ = "customers"

    # --- Primary Key ---
    customer_id = db.Column(db.String(20), primary_key=True)

    # --- Personal Information ---
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)

    # --- Purchase Metrics ---
    total_orders = db.Column(db.Integer, default=0)
    total_spend = db.Column(db.Float, default=0.0)
    average_order_value = db.Column(db.Float, default=0.0)
    last_purchase_date = db.Column(db.Date, nullable=True)

    # --- Engagement Metrics ---
    website_visits = db.Column(db.Integer, default=0)
    complaints = db.Column(db.Integer, default=0)
    subscription_status = db.Column(db.String(20), default="Active")

    # --- Timestamps ---
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # --- Relationship: One Customer → Many Purchases ---
    purchases = db.relationship(
        "Purchase",
        backref="customer",
        lazy=True,
        cascade="all, delete-orphan"
    )

    def to_dict(self):
        """Converts Customer object to a dictionary for JSON responses."""
        return {
            "customer_id": self.customer_id,
            "name": self.name,
            "age": self.age,
            "gender": self.gender,
            "location": self.location,
            "email": self.email,
            "total_orders": self.total_orders,
            "total_spend": self.total_spend,
            "average_order_value": self.average_order_value,
            "last_purchase_date": (
                self.last_purchase_date.isoformat()
                if self.last_purchase_date else None
            ),
            "website_visits": self.website_visits,
            "complaints": self.complaints,
            "subscription_status": self.subscription_status,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at else None
            ),
        }

    def __repr__(self):
        return f"<Customer {self.customer_id} - {self.name}>"
