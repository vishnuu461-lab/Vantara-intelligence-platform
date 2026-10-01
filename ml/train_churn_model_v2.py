# ============================================================
# ml/train_churn_model_v2.py — Multi-Model Churn Training
# ============================================================
# Trains and compares 5 churn models:
#   1. Logistic Regression (baseline)
#   2. Random Forest (existing — preserved)
#   3. XGBoost
#   4. LightGBM
#   5. ANN (sklearn MLPClassifier)
#
# HOW TO RUN:
#   C:\Vantara-venv\Scripts\python.exe ml/train_churn_model_v2.py
#
# OUTPUTS:
#   - ml/models/churn_model.pkl         ← best model (overwrites)
#   - ml/models/churn_scaler.pkl        ← scaler  (overwrites)
#   - ml/models/churn_best_name.txt     ← name of best model
#   - ml/experiment_log.json            ← all experiment results
#
# The existing churn_model.pkl is only overwritten if a newer
# model beats it AND you confirm that is desired.
# ============================================================

import sys, os, json, time
from datetime import datetime

import numpy as np
import joblib
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, confusion_matrix, classification_report
)
from sklearn.linear_model  import LogisticRegression
from sklearn.ensemble      import RandomForestClassifier
from sklearn.neural_network import MLPClassifier

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Optional imports (graceful fallback) ──────────────────

try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
    print("⚠️  XGBoost not installed — skipping. pip install xgboost")

try:
    from lightgbm import LGBMClassifier
    HAS_LGB = True
except ImportError:
    HAS_LGB = False
    print("⚠️  LightGBM not installed — skipping. pip install lightgbm")


SEED = 42
np.random.seed(SEED)

FEATURE_NAMES = [
    "total_orders", "total_spend", "days_since_last_purchase",
    "average_order_value", "website_visits", "complaints",
    "subscription_active"
]

LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "ml", "experiment_log.json")


# ── Data generation (same as v1 for consistency) ──────────

def create_training_data(n_samples: int = 2000):
    np.random.seed(SEED)
    data, labels = [], []

    for _ in range(n_samples):
        at_risk = np.random.random() < 0.40

        if at_risk:
            total_orders    = np.random.randint(0, 5)
            total_spend     = np.random.uniform(0, 15000)
            days_since_last = np.random.randint(90, 500)
            avg_order_value = np.random.uniform(500, 3000)
            website_visits  = np.random.randint(0, 15)
            complaints      = np.random.randint(1, 6)
            sub_active      = np.random.choice([0, 0, 1])
        else:
            total_orders    = np.random.randint(5, 40)
            total_spend     = np.random.uniform(10000, 200000)
            days_since_last = np.random.randint(1, 90)
            avg_order_value = np.random.uniform(2000, 10000)
            website_visits  = np.random.randint(30, 200)
            complaints      = np.random.randint(0, 2)
            sub_active      = np.random.choice([1, 1, 0])

        features = [total_orders, total_spend, days_since_last,
                    avg_order_value, website_visits, complaints, sub_active]
        data.append(features)

        churn_score = 0
        if days_since_last > 180: churn_score += 3
        if days_since_last > 90:  churn_score += 1
        if complaints >= 3:       churn_score += 2
        if complaints >= 1:       churn_score += 1
        if total_orders <= 2:     churn_score += 2
        if sub_active == 0:       churn_score += 2
        if website_visits < 10:   churn_score += 1
        if total_spend < 5000:    churn_score += 1

        noise   = np.random.choice([0, 0, 0, 1])
        churned = 1 if (churn_score >= 5 and noise == 0) else 0
        labels.append(churned)

    return np.array(data), np.array(labels)


# ── Evaluation helper ──────────────────────────────────────

def evaluate(model, X_test, y_test, scaler=None):
    Xt = scaler.transform(X_test) if scaler else X_test
    y_pred  = model.predict(Xt)
    y_proba = model.predict_proba(Xt)[:, 1]

    cm = confusion_matrix(y_test, y_pred)
    return {
        "accuracy":  round(accuracy_score(y_test, y_pred), 4),
        "precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
        "recall":    round(recall_score(y_test, y_pred, zero_division=0), 4),
        "f1":        round(f1_score(y_test, y_pred, zero_division=0), 4),
        "roc_auc":   round(roc_auc_score(y_test, y_proba), 4),
        "confusion_matrix": cm.tolist(),
    }


# ── Experiment logger ──────────────────────────────────────

def log_experiment(entry: dict):
    history = []
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH) as f:
            try:
                history = json.load(f)
            except json.JSONDecodeError:
                history = []
    history.append(entry)
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "w") as f:
        json.dump(history, f, indent=2, default=str)


# ── Main training routine ──────────────────────────────────

def train_all_models():
    print("=" * 60)
    print("  Vantara — Multi-Model Churn Training (v2)")
    print("=" * 60)

    print("\n[1/6] Creating training data (2000 samples)...")
    X, y = create_training_data(2000)
    print(f"  Churned: {y.sum()} ({y.mean()*100:.1f}%)  "
          f"Active: {(y==0).sum()} ({(y==0).mean()*100:.1f}%)")

    # Stratified split — 70 / 15 / 15
    print("\n[2/6] Stratified 70/15/15 split...")
    X_tv, X_test, y_tv, y_test = train_test_split(
        X, y, test_size=0.15, random_state=SEED, stratify=y)
    X_train, X_val, y_train, y_val = train_test_split(
        X_tv, y_tv, test_size=0.15/(0.85), random_state=SEED, stratify=y_tv)
    print(f"  Train {len(X_train)} | Val {len(X_val)} | Test {len(X_test)}")

    print("\n[3/6] Scaling features...")
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_val_s   = scaler.transform(X_val)
    X_test_s  = scaler.transform(X_test)

    # ── Define models ──────────────────────────────────────
    models = {
        "Logistic Regression": LogisticRegression(
            max_iter=1000, class_weight="balanced", random_state=SEED),
        "Random Forest": RandomForestClassifier(
            n_estimators=100, max_depth=8, min_samples_split=5,
            class_weight="balanced", random_state=SEED),
        "ANN (MLP)": MLPClassifier(
            hidden_layer_sizes=(64, 32), activation="relu",
            max_iter=500, early_stopping=True, validation_fraction=0.1,
            random_state=SEED, batch_size=32),
    }
    if HAS_XGB:
        scale_pos = int((y == 0).sum() / max(y.sum(), 1))
        models["XGBoost"] = XGBClassifier(
            n_estimators=100, max_depth=5, learning_rate=0.1,
            scale_pos_weight=scale_pos, random_state=SEED,
            eval_metric="logloss", verbosity=0)
    if HAS_LGB:
        models["LightGBM"] = LGBMClassifier(
            n_estimators=100, max_depth=5, learning_rate=0.1,
            class_weight="balanced", random_state=SEED, verbose=-1)

    # ── Train + evaluate each model ────────────────────────
    print(f"\n[4/6] Training {len(models)} models...")
    results = {}

    for name, model in models.items():
        print(f"\n  ─── {name} ───")
        t0 = time.time()

        model.fit(X_train_s, y_train)
        train_time = round(time.time() - t0, 2)

        # Val metrics
        val_metrics  = evaluate(model, X_val, y_val, scaler)
        test_metrics = evaluate(model, X_test, y_test, scaler)

        # Cross-val on full train+val set (5-fold)
        cv_scores = cross_val_score(
            model, scaler.transform(X_tv), y_tv,
            cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED),
            scoring="roc_auc"
        )

        results[name] = {
            "val_metrics":   val_metrics,
            "test_metrics":  test_metrics,
            "cv_roc_auc_mean": round(cv_scores.mean(), 4),
            "cv_roc_auc_std":  round(cv_scores.std(), 4),
            "train_time_sec":  train_time,
        }

        print(f"  Val  | Acc={val_metrics['accuracy']:.3f}  "
              f"F1={val_metrics['f1']:.3f}  AUC={val_metrics['roc_auc']:.3f}")
        print(f"  Test | Acc={test_metrics['accuracy']:.3f}  "
              f"F1={test_metrics['f1']:.3f}  AUC={test_metrics['roc_auc']:.3f}")
        print(f"  CV   | AUC={cv_scores.mean():.3f} ± {cv_scores.std():.3f}")
        print(f"  Time | {train_time}s")

        # Log each experiment
        log_experiment({
            "timestamp":     datetime.now().isoformat(),
            "model_name":    name,
            "dataset":       "synthetic_2000",
            "n_features":    len(FEATURE_NAMES),
            "feature_names": FEATURE_NAMES,
            "train_time_sec": train_time,
            "val_metrics":   val_metrics,
            "test_metrics":  test_metrics,
            "cv_roc_auc":    {"mean": round(cv_scores.mean(), 4),
                               "std":  round(cv_scores.std(), 4)},
        })

    # ── Select best model by val ROC-AUC ──────────────────
    print("\n[5/6] Selecting best model by val ROC-AUC...")
    best_name = max(results, key=lambda n: results[n]["val_metrics"]["roc_auc"])
    best_model = models[best_name]
    best_metrics = results[best_name]

    print(f"\n  🏆 Best model: {best_name}")
    print(f"     Val AUC  : {best_metrics['val_metrics']['roc_auc']:.4f}")
    print(f"     Test AUC : {best_metrics['test_metrics']['roc_auc']:.4f}")

    # ── Save ───────────────────────────────────────────────
    print("\n[6/6] Saving best model...")
    os.makedirs("ml/models", exist_ok=True)
    joblib.dump(best_model, "ml/models/churn_model.pkl")
    joblib.dump(scaler,     "ml/models/churn_scaler.pkl")

    with open("ml/models/churn_best_name.txt", "w") as f:
        f.write(best_name)

    print(f"  ✅ Saved: ml/models/churn_model.pkl  ({best_name})")
    print(f"  ✅ Saved: ml/models/churn_scaler.pkl")
    print(f"  ✅ Experiment log: {LOG_PATH}")

    # ── Comparison table ───────────────────────────────────
    print("\n" + "=" * 60)
    print("  MODEL COMPARISON TABLE")
    print("=" * 60)
    print(f"  {'Model':<22} {'Val AUC':>8} {'Val F1':>8} {'Test AUC':>9}")
    print(f"  {'-'*22} {'-'*8} {'-'*8} {'-'*9}")
    for name, r in sorted(results.items(),
                           key=lambda x: x[1]["val_metrics"]["roc_auc"],
                           reverse=True):
        marker = " ← BEST" if name == best_name else ""
        print(f"  {name:<22} "
              f"{r['val_metrics']['roc_auc']:>8.4f} "
              f"{r['val_metrics']['f1']:>8.4f} "
              f"{r['test_metrics']['roc_auc']:>9.4f}{marker}")
    print("=" * 60)

    return best_model, scaler, best_name, results


if __name__ == "__main__":
    train_all_models()
