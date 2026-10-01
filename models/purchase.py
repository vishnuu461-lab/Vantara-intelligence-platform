# ============================================================
# models/purchase.py — Purchase/Transaction Database Table
# ============================================================
from datetime import datetime, timezone
from extensions import db   # Import db from extensions.py (not app.py)


class Purchase(db.Model):
    """
    Represents a single purchase/transaction.
    Maps to the 'purchases' table in MySQL.
    """

    __tablename__ = "purchases"

    # --- Primary Key (auto-increments: 1, 2, 3 ...) ---
    purchase_id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # --- Foreign Key: links this purchase to a customer ---
    # Every purchase MUST belong to an existing customer
    customer_id = db.Column(
        db.String(20),
        db.ForeignKey("customers.customer_id"),
        nullable=False
    )

    # --- Purchase Details ---
    product_name = db.Column(db.String(150), nullable=False)
    product_category = db.Column(db.String(100), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    purchase_date = db.Column(db.Date, nullable=False)

    # --- Timestamp ---
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        """Converts Purchase object to a dictionary for JSON responses."""
        return {
            "purchase_id": self.purchase_id,
            "customer_id": self.customer_id,
            "product_name": self.product_name,
            "product_category": self.product_category,
            "amount": self.amount,
            "purchase_date": (
                self.purchase_date.isoformat()
                if self.purchase_date else None
            ),
            "created_at": (
                self.created_at.isoformat()
                if self.created_at else None
            ),
        }

    def __repr__(self):
        return f"<Purchase #{self.purchase_id} - {self.product_name} (₹{self.amount})>"
