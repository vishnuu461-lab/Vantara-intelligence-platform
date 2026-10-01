# ============================================================
# ml/train_churn_model.py — Train the Churn Prediction Model
# ============================================================
# THIS SCRIPT TRAINS THE MACHINE LEARNING MODEL.
# Run it ONCE to create the trained model file.
#
# HOW TO RUN:
#   C:\Vantara-venv\Scripts\python.exe ml/train_churn_model.py
#
# WHAT IT DOES:
#   1. Creates realistic synthetic training data
#   2. Defines features (inputs) and labels (output)
#   3. Trains a Random Forest model
#   4. Evaluates accuracy
#   5. Saves the model to ml/models/churn_model.pkl
#
# WHY SYNTHETIC DATA?
#   We don't have thousands of real labeled examples with
#   known churn outcomes. Synthetic data lets us build and
#   test the pipeline. When you have real data later, just
#   replace the training data here.
#
# IMPORTANT NOTE:
#   This model is for LEARNING purposes. Real production
#   churn models need thousands of real labeled examples
#   and proper validation. This is a starting point.
# ============================================================

import sys
import os
import numpy as np
import joblib

# Add project root to path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)

# ============================================================
# STEP 1: Create Synthetic Training Data
# ============================================================
# We create 1000 fake customer records with known churn labels.
# The patterns we use are realistic and based on common
# business knowledge about customer churn.
#
# FEATURES (inputs to the model):
#   - total_orders
#   - total_spend
#   - days_since_last_purchase
#   - average_order_value
#   - website_visits
#   - complaints
#   - subscription_active (1 = active, 0 = inactive/cancelled)
#
# LABEL (what we're predicting):
#   - churned: 1 = churned, 0 = still active
# ============================================================

def create_training_data(n_samples=1000):
    """
    Creates synthetic training data with realistic patterns.

    Pattern logic:
    - High complaints + low purchases = likely churned
    - Recent purchases + Premium subscription = likely active
    - No purchases in 180+ days = likely churned
    - High spend + active subscription = likely active
    """
    np.random.seed(42)  # For reproducibility — same results every run

    data = []
    labels = []

    for i in range(n_samples):
        # Randomly create a customer profile
        # We bias toward patterns we know create churn

        # 40% of customers are "at-risk" profiles
        if np.random.random() < 0.4:
            # AT-RISK customer profile → likely to churn
            total_orders = np.random.randint(0, 5)
            total_spend = np.random.uniform(0, 15000)
            days_since_last = np.random.randint(90, 500)
            avg_order_value = np.random.uniform(500, 3000)
            website_visits = np.random.randint(0, 15)
            complaints = np.random.randint(1, 6)
            subscription_active = np.random.choice([0, 0, 1])  # Mostly inactive
        else:
            # HEALTHY customer profile → likely to stay
            total_orders = np.random.randint(5, 40)
            total_spend = np.random.uniform(10000, 200000)
            days_since_last = np.random.randint(1, 90)
            avg_order_value = np.random.uniform(2000, 10000)
            website_visits = np.random.randint(30, 200)
            complaints = np.random.randint(0, 2)
            subscription_active = np.random.choice([1, 1, 0])  # Mostly active

        features = [
            total_orders,
            total_spend,
            days_since_last,
            avg_order_value,
            website_visits,
            complaints,
            subscription_active
        ]
        data.append(features)

        # --- Determine churn label using business rules ---
        # These rules define "truth" in our synthetic dataset
        churn_score = 0

        if days_since_last > 180:     churn_score += 3
        if days_since_last > 90:      churn_score += 1
        if complaints >= 3:           churn_score += 2
        if complaints >= 1:           churn_score += 1
        if total_orders <= 2:         churn_score += 2
        if subscription_active == 0:  churn_score += 2
        if website_visits < 10:       churn_score += 1
        if total_spend < 5000:        churn_score += 1

        # Customer has churned if score is high enough
        # Add a small amount of noise (realistic — some active
        # customers look at-risk and vice versa)
        noise = np.random.choice([0, 0, 0, 1])  # 25% noise
        churned = 1 if (churn_score >= 5 and noise == 0) else 0
        labels.append(churned)

    return np.array(data), np.array(labels)


# ============================================================
# STEP 2: Train the Model
# ============================================================

def train_churn_model():
    print("=" * 55)
    print("  Vantara — Churn Model Training")
    print("=" * 55)

    # Create training data
    print("\n[1/5] Creating training data...")
    X, y = create_training_data(n_samples=1000)
    print(f"  Created {len(X)} training samples")
    print(f"  Churned customers: {y.sum()} ({y.mean()*100:.1f}%)")
    print(f"  Active customers:  {(y==0).sum()} ({(y==0).mean()*100:.1f}%)")

    # Split into training set (80%) and test set (20%)
    # We train on 80% and evaluate on the 20% the model never saw
    print("\n[2/5] Splitting into train/test sets (80/20)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,      # 20% for testing
        random_state=42,    # Same split every time
        stratify=y          # Keep same churn ratio in both splits
    )
    print(f"  Training samples: {len(X_train)}")
    print(f"  Testing samples:  {len(X_test)}")

    # Scale the features
    # StandardScaler makes all features have mean=0, std=1
    # This helps the model treat all features equally
    print("\n[3/5] Scaling features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    print("  Features scaled successfully")

    # Train the Random Forest model
    # n_estimators=100 means 100 decision trees vote together
    # random_state=42 ensures reproducibility
    print("\n[4/5] Training Random Forest model...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=8,
        min_samples_split=5,
        random_state=42,
        class_weight="balanced"  # Handles imbalanced data
    )
    model.fit(X_train_scaled, y_train)
    print("  Model trained successfully!")

    # Evaluate the model
    print("\n[5/5] Evaluating model...")
    y_pred = model.predict(X_test_scaled)
    accuracy = accuracy_score(y_test, y_pred)

    print(f"\n  Accuracy: {accuracy * 100:.2f}%")
    print("\n  Classification Report:")
    print(classification_report(
        y_test, y_pred,
        target_names=["Active (0)", "Churned (1)"]
    ))

    print("  Confusion Matrix:")
    cm = confusion_matrix(y_test, y_pred)
    print(f"  [[TN={cm[0][0]}  FP={cm[0][1]}]")
    print(f"   [FN={cm[1][0]}  TP={cm[1][1]}]]")
    print("  TN=Correctly predicted Active")
    print("  TP=Correctly predicted Churned")

    # --------------------------------------------------------
    # Feature Importance — which features matter most?
    # --------------------------------------------------------
    feature_names = [
        "total_orders", "total_spend", "days_since_last_purchase",
        "average_order_value", "website_visits", "complaints",
        "subscription_active"
    ]
    importances = model.feature_importances_
    print("\n  Feature Importances (higher = more influential):")
    for name, imp in sorted(
        zip(feature_names, importances),
        key=lambda x: x[1],
        reverse=True
    ):
        bar = "|" * int(imp * 40)
        print(f"  {name:<30} {imp:.3f}  {bar}")

    # Save the model and scaler
    os.makedirs("ml/models", exist_ok=True)
    joblib.dump(model, "ml/models/churn_model.pkl")
    joblib.dump(scaler, "ml/models/churn_scaler.pkl")

    print("\n" + "=" * 55)
    print("  Model saved to: ml/models/churn_model.pkl")
    print("  Scaler saved to: ml/models/churn_scaler.pkl")
    print("=" * 55)
    print("\nTraining complete! The Flask API can now use this model.")

    return model, scaler


if __name__ == "__main__":
    train_churn_model()
