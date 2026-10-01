# ============================================================
# ml/train_clv_model.py — Train the CLV Prediction Model
# ============================================================
# THIS SCRIPT TRAINS THE CLV REGRESSION MODEL.
# Run it ONCE to create the trained model file.
#
# HOW TO RUN:
#   C:\Vantara-venv\Scripts\python.exe ml/train_clv_model.py
#
# WHAT IS CLV?
#   Customer Lifetime Value = how much revenue a customer
#   is predicted to generate over their remaining time
#   with the business.
#
# MODEL USED: Random Forest Regressor
#   - Regression (not classification) because CLV is a
#     continuous number, not a category like "High/Low"
#   - Random Forest is robust and handles non-linear
#     relationships well
#
# FEATURES USED:
#   - total_orders
#   - total_spend (current)
#   - average_order_value
#   - website_visits
#   - complaints
#   - subscription_active
#   - days_since_last_purchase
#   - purchases_per_month (frequency)
#
# NOTE ON ACCURACY:
#   Real CLV models need months/years of transaction history.
#   This model uses synthetic data to demonstrate the pipeline.
#   Accuracy will improve greatly with real business data.
# ============================================================

import sys
import os
import numpy as np
import joblib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score


# ============================================================
# STEP 1: Create Synthetic CLV Training Data
# ============================================================

def create_clv_training_data(n_samples=1000):
    """
    Creates synthetic training data for CLV prediction.

    The CLV value is calculated using a realistic formula:
      CLV = avg_order_value * purchases_per_month * 12 * loyalty_factor

    This simulates 12 months of predicted future value.
    loyalty_factor is higher for engaged, low-complaint customers.
    """
    np.random.seed(42)

    data = []
    targets = []  # CLV values (what we want to predict)

    for _ in range(n_samples):
        # Generate customer features
        total_orders = np.random.randint(0, 40)
        total_spend = np.random.uniform(0, 200000)
        avg_order_value = (
            total_spend / total_orders if total_orders > 0
            else np.random.uniform(500, 5000)
        )
        website_visits = np.random.randint(0, 200)
        complaints = np.random.randint(0, 6)
        subscription_active = np.random.choice([0, 1], p=[0.3, 0.7])
        days_since_last = np.random.randint(1, 400)
        purchases_per_month = np.random.uniform(0, 5)

        features = [
            total_orders,
            total_spend,
            avg_order_value,
            website_visits,
            complaints,
            subscription_active,
            days_since_last,
            purchases_per_month
        ]
        data.append(features)

        # --------------------------------------------------------
        # Calculate CLV using a business-realistic formula
        # --------------------------------------------------------

        # Base: expected purchases per year × avg order value
        annual_purchases = purchases_per_month * 12
        base_clv = avg_order_value * annual_purchases

        # Loyalty multiplier: engaged customers stay longer
        if subscription_active == 1:
            loyalty_years = np.random.uniform(1.5, 4.0)
        else:
            loyalty_years = np.random.uniform(0.3, 1.5)

        # Penalty for complaints (unhappy customers leave sooner)
        complaint_penalty = max(0, 1 - (complaints * 0.15))

        # Recency boost (recently active = more likely to continue)
        if days_since_last <= 30:
            recency_factor = 1.2
        elif days_since_last <= 90:
            recency_factor = 1.0
        elif days_since_last <= 180:
            recency_factor = 0.7
        else:
            recency_factor = 0.3

        # Final CLV formula
        clv = (
            base_clv
            * loyalty_years
            * complaint_penalty
            * recency_factor
        )

        # Add realistic noise (real CLV is never perfectly predictable)
        clv = clv * np.random.uniform(0.85, 1.15)
        clv = max(0, round(clv, 2))  # CLV cannot be negative

        targets.append(clv)

    return np.array(data), np.array(targets)


# ============================================================
# STEP 2: Train the Model
# ============================================================

def train_clv_model():
    print("=" * 55)
    print("  Vantara - CLV Model Training")
    print("=" * 55)

    # Create training data
    print("\n[1/5] Creating CLV training data...")
    X, y = create_clv_training_data(n_samples=1000)
    print(f"  Created {len(X)} training samples")
    print(f"  CLV range: Rs.{y.min():,.0f} to Rs.{y.max():,.0f}")
    print(f"  Average CLV: Rs.{y.mean():,.0f}")

    # Train/test split
    print("\n[2/5] Splitting into train/test sets (80/20)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=42
    )
    print(f"  Training samples: {len(X_train)}")
    print(f"  Testing samples:  {len(X_test)}")

    # Scale features
    print("\n[3/5] Scaling features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    print("  Features scaled successfully")

    # Train the Random Forest Regressor
    print("\n[4/5] Training Random Forest Regressor...")
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        random_state=42,
        n_jobs=-1   # Use all CPU cores for faster training
    )
    model.fit(X_train_scaled, y_train)
    print("  Model trained successfully!")

    # Evaluate
    print("\n[5/5] Evaluating model...")
    y_pred = model.predict(X_test_scaled)

    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    print(f"\n  R2 Score:  {r2:.4f}  (1.0 = perfect, 0 = random)")
    print(f"  MAE:       Rs.{mae:,.0f}  (average prediction error)")
    print(f"\n  Sample Predictions vs Actual:")
    for i in range(5):
        print(
            f"  Actual: Rs.{y_test[i]:>10,.0f}  |  "
            f"Predicted: Rs.{y_pred[i]:>10,.0f}"
        )

    # Feature importance
    feature_names = [
        "total_orders", "total_spend", "avg_order_value",
        "website_visits", "complaints", "subscription_active",
        "days_since_last", "purchases_per_month"
    ]
    importances = model.feature_importances_
    print("\n  Feature Importances:")
    for name, imp in sorted(
        zip(feature_names, importances),
        key=lambda x: x[1], reverse=True
    ):
        bar = "|" * int(imp * 40)
        print(f"  {name:<25} {imp:.3f}  {bar}")

    # Save model and scaler
    os.makedirs("ml/models", exist_ok=True)
    joblib.dump(model, "ml/models/clv_model.pkl")
    joblib.dump(scaler, "ml/models/clv_scaler.pkl")

    print("\n" + "=" * 55)
    print("  Model saved to: ml/models/clv_model.pkl")
    print("  Scaler saved to: ml/models/clv_scaler.pkl")
    print("=" * 55)
    print("\nTraining complete! The Flask API can now use this model.")

    return model, scaler


if __name__ == "__main__":
    train_clv_model()
