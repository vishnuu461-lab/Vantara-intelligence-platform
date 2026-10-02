# ============================================================
# ml/train_clv_model.py — Train the CLV Prediction Model
# ============================================================
# MODEL: MLP Regressor (neural network)
#   - No tree C-extension DLLs → works under Windows App Control
#   - Comparable accuracy to Random Forest on this dataset
#   - Same 8 features as before — no changes to clv_service.py
#
# HOW TO RUN:
#   C:\Vantara-venv\Scripts\python.exe ml/train_clv_model.py
# ============================================================

import sys
import os
import numpy as np
import joblib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sklearn.neural_network import MLPRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score


# ── Training data ─────────────────────────────────────────

def create_clv_training_data(n_samples=1000):
    """
    Synthetic CLV training data.
    CLV = avg_order_value * purchases_per_month * 12 * loyalty_factor
    """
    np.random.seed(42)
    data, targets = [], []

    for _ in range(n_samples):
        total_orders        = np.random.randint(0, 40)
        total_spend         = np.random.uniform(0, 200000)
        avg_order_value     = (
            total_spend / total_orders if total_orders > 0
            else np.random.uniform(500, 5000)
        )
        website_visits      = np.random.randint(0, 200)
        complaints          = np.random.randint(0, 6)
        subscription_active = np.random.choice([0, 1], p=[0.3, 0.7])
        days_since_last     = np.random.randint(1, 400)
        purchases_per_month = np.random.uniform(0, 5)

        data.append([
            total_orders, total_spend, avg_order_value,
            website_visits, complaints, subscription_active,
            days_since_last, purchases_per_month
        ])

        # Business-realistic CLV formula
        annual_purchases = purchases_per_month * 12
        base_clv         = avg_order_value * annual_purchases

        loyalty_years = (
            np.random.uniform(1.5, 4.0) if subscription_active == 1
            else np.random.uniform(0.3, 1.5)
        )
        complaint_penalty = max(0, 1 - (complaints * 0.15))
        if days_since_last <= 30:    recency_factor = 1.2
        elif days_since_last <= 90:  recency_factor = 1.0
        elif days_since_last <= 180: recency_factor = 0.7
        else:                        recency_factor = 0.3

        clv = base_clv * loyalty_years * complaint_penalty * recency_factor
        clv = clv * np.random.uniform(0.85, 1.15)
        clv = max(0, round(clv, 2))
        targets.append(clv)

    return np.array(data), np.array(targets)


# ── Training ───────────────────────────────────────────────

def train_clv_model():
    print("=" * 55)
    print("  Vantara - CLV Model Training (MLP Regressor)")
    print("=" * 55)

    print("\n[1/5] Creating CLV training data...")
    X, y = create_clv_training_data(n_samples=1000)
    print(f"  {len(X)} samples | CLV range: Rs.{y.min():,.0f} – Rs.{y.max():,.0f}")
    print(f"  Avg CLV: Rs.{y.mean():,.0f}")

    print("\n[2/5] Splitting 80/20 train/test...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    print("\n[3/5] Scaling features...")
    scaler       = StandardScaler()
    X_train_s    = scaler.fit_transform(X_train)
    X_test_s     = scaler.transform(X_test)

    print("\n[4/5] Training MLP Regressor...")
    model = MLPRegressor(
        hidden_layer_sizes=(128, 64, 32),
        activation="relu",
        max_iter=500,
        early_stopping=True,
        validation_fraction=0.1,
        random_state=42,
        batch_size=32,
    )
    model.fit(X_train_s, y_train)
    print("  Model trained!")

    print("\n[5/5] Evaluating...")
    y_pred = model.predict(X_test_s)
    mae    = mean_absolute_error(y_test, y_pred)
    r2     = r2_score(y_test, y_pred)

    print(f"\n  R2 Score : {r2:.4f}")
    print(f"  MAE      : Rs.{mae:,.0f}")
    print("\n  Sample predictions:")
    for i in range(5):
        print(f"  Actual: Rs.{y_test[i]:>10,.0f}  |  Predicted: Rs.{y_pred[i]:>10,.0f}")

    os.makedirs("ml/models", exist_ok=True)
    joblib.dump(model,  "ml/models/clv_model.pkl")
    joblib.dump(scaler, "ml/models/clv_scaler.pkl")

    print("\n" + "=" * 55)
    print("  ✅ Saved: ml/models/clv_model.pkl  (MLP Regressor)")
    print("  ✅ Saved: ml/models/clv_scaler.pkl")
    print("=" * 55)
    return model, scaler


if __name__ == "__main__":
    train_clv_model()
