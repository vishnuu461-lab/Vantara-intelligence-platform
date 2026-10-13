# ============================================================
# data/test_vantara_with_retail_ii.py
# ============================================================
# End-to-end integration test of the Vantara platform using
# the UCI Online Retail II dataset.
#
# HOW TO RUN:
#   1. Make sure Flask server is running:
#        .venv\Scripts\python.exe app.py
#   2. Run this script:
#        .venv\Scripts\python.exe data/test_vantara_with_retail_ii.py
#
# WHAT IT TESTS:
#   Phase 1 — Data preparation  : load_online_retail_ii.py
#   Phase 2 — Bulk CSV upload  : POST /api/upload
#   Phase 3 — Customer CRUD    : GET /api/customers and single customer
#   Phase 4 — ML predictions   : churn, CLV, segmentation, next-purchase
#   Phase 5 — Analytics        : dashboard summary
#   Phase 6 — Quality report   : pass / fail table + CSV artefacts
# ============================================================

import sys
import os
import time
import json
import csv
import traceback
from datetime import datetime

import requests
import pandas as pd

# ── Config ────────────────────────────────────────────────────
BASE_URL   = "http://localhost:5000"
DATA_DIR   = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR   = os.path.dirname(DATA_DIR)

UPLOAD_CSV = os.path.join(DATA_DIR, "online_retail_ii_customers.csv")
REPORT_CSV = os.path.join(DATA_DIR, "vantara_test_report.csv")
DETAIL_CSV = os.path.join(DATA_DIR, "vantara_prediction_results.csv")

# How many customers to upload in each batch (API upload endpoint)
UPLOAD_BATCH_SIZE = 200

# How many customers to run ML predictions on (pick diverse sample)
PREDICTION_SAMPLE  = 20

# ── Helpers ───────────────────────────────────────────────────

def hdr(title: str):
    print("\n" + "=" * 65)
    print(f"  {title}")
    print("=" * 65)

def ok(msg):  print(f"  ✅  {msg}")
def fail(msg): print(f"  ❌  {msg}")
def info(msg): print(f"  ℹ️   {msg}")


# ============================================================
# PHASE 1 — Prepare the UCI data (run loader if needed)
# ============================================================

def phase1_prepare_data() -> pd.DataFrame:
    hdr("PHASE 1 — Prepare UCI Online Retail II Data")

    if not os.path.exists(UPLOAD_CSV):
        info("CSV not found — running data loader …")
        sys.path.insert(0, ROOT_DIR)
        from data.load_online_retail_ii import main as load_main
        load_main()
    else:
        info(f"CSV already exists: {UPLOAD_CSV}")

    df = pd.read_csv(UPLOAD_CSV)
    ok(f"Loaded {len(df):,} customer rows")
    # Quick sanity checks
    assert "customer_id" in df.columns, "Missing customer_id column!"
    assert "name"         in df.columns, "Missing name column!"
    ok("Schema validated (customer_id, name present)")
    return df


# ============================================================
# PHASE 2 — Bulk CSV upload via REST API
# ============================================================

def phase2_upload(df: pd.DataFrame, results: list) -> list:
    hdr("PHASE 2 — Bulk CSV Upload  (POST /api/upload)")

    # Keep only Vantara-compatible columns (drop _* analytics cols)
    vantara_cols = [
        "customer_id","name","age","gender","location","email",
        "total_orders","total_spend","average_order_value",
        "last_purchase_date","website_visits","complaints",
        "subscription_status"
    ]
    upload_df = df[[c for c in vantara_cols if c in df.columns]].copy()

    # Upload in batches to stay within the 5 MB limit
    total_inserted = 0
    total_dupes    = 0
    total_skipped  = 0
    batch_num      = 0

    for start in range(0, len(upload_df), UPLOAD_BATCH_SIZE):
        batch  = upload_df.iloc[start : start + UPLOAD_BATCH_SIZE]
        batch_num += 1

        # Write batch to temp CSV string
        csv_content = batch.to_csv(index=False)
        files = {"file": (f"batch_{batch_num}.csv",
                          csv_content.encode("utf-8"),
                          "text/csv")}

        try:
            resp = requests.post(f"{BASE_URL}/api/upload", files=files, timeout=30)
        except requests.exceptions.ConnectionError:
            fail(f"Cannot connect to {BASE_URL}. Is Flask running?")
            results.append({"test": "POST /api/upload", "status": "FAIL",
                             "detail": "Connection refused"})
            return results

        if resp.status_code in (200, 207):
            data = resp.json()
            ins  = data.get("report", {}).get("inserted", 0)
            dup  = data.get("report", {}).get("duplicates_skipped", 0)
            skp  = data.get("report", {}).get("invalid_skipped", 0)
            total_inserted += ins
            total_dupes    += dup
            total_skipped  += skp
            print(f"  Batch {batch_num:>3} ({len(batch):>3} rows) → "
                  f"inserted={ins:>3} | dupes={dup:>3} | skipped={skp:>3}")
        else:
            fail(f"Batch {batch_num} HTTP {resp.status_code}: {resp.text[:200]}")

    info(f"Upload complete — inserted={total_inserted} | "
         f"dupes={total_dupes} | invalid={total_skipped}")

    if total_inserted + total_dupes > 0:
        ok("Upload phase PASSED")
        results.append({"test": "POST /api/upload (batch)",
                         "status": "PASS",
                         "detail": f"inserted={total_inserted} dupes={total_dupes}"})
    else:
        fail("No customers were inserted or found")
        results.append({"test": "POST /api/upload (batch)",
                         "status": "FAIL",
                         "detail": "0 customers in DB after upload"})
    return results


# ============================================================
# PHASE 3 — Customer CRUD queries
# ============================================================

def phase3_customer_queries(df: pd.DataFrame, results: list) -> list:
    hdr("PHASE 3 — Customer CRUD  (GET /api/customers)")

    # 3a — List all customers
    try:
        resp = requests.get(f"{BASE_URL}/api/customers", timeout=15)
        if resp.status_code == 200:
            customers = resp.json()
            ok(f"GET /api/customers → {len(customers):,} customers returned")
            results.append({"test": "GET /api/customers", "status": "PASS",
                             "detail": f"{len(customers)} records"})
        else:
            fail(f"GET /api/customers → HTTP {resp.status_code}")
            results.append({"test": "GET /api/customers", "status": "FAIL",
                             "detail": resp.text[:200]})
            customers = []
    except Exception as e:
        fail(f"GET /api/customers → {e}")
        results.append({"test": "GET /api/customers", "status": "ERROR",
                         "detail": str(e)})
        customers = []

    # 3b — Fetch a specific customer
    sample_id = str(df["customer_id"].iloc[0])
    try:
        resp = requests.get(f"{BASE_URL}/api/customers/{sample_id}", timeout=10)
        if resp.status_code == 200:
            c = resp.json()
            ok(f"GET /api/customers/{sample_id} → {c.get('name','?')} "
               f"(spend={c.get('total_spend','?')})")
            results.append({"test": f"GET /api/customers/{{id}}",
                             "status": "PASS",
                             "detail": f"id={sample_id}"})
        else:
            fail(f"GET /api/customers/{sample_id} → HTTP {resp.status_code}")
            results.append({"test": "GET /api/customers/{id}", "status": "FAIL",
                             "detail": resp.text[:200]})
    except Exception as e:
        fail(f"GET /api/customers/{sample_id} → {e}")
        results.append({"test": "GET /api/customers/{id}", "status": "ERROR",
                         "detail": str(e)})

    return results


# ============================================================
# PHASE 4 — ML Predictions on sampled customers
# ============================================================

def phase4_ml_predictions(df: pd.DataFrame, results: list) -> list:
    hdr("PHASE 4 — ML Predictions on Retail II Customers")

    # Pick a diverse sample: spend quartiles + churn risk variety
    sample_df = df.sample(min(PREDICTION_SAMPLE, len(df)), random_state=42)
    info(f"Running predictions on {len(sample_df)} sampled customers …")

    prediction_rows = []
    churn_pass = 0; clv_pass = 0; seg_pass = 0; nxt_pass = 0
    churn_fail = 0; clv_fail = 0; seg_fail = 0; nxt_fail = 0

    ENDPOINTS = {
        "churn"        : "/api/predict/churn/{cid}",
        "clv"          : "/api/predict/clv/{cid}",
        "segment"      : "/api/predict/segment/{cid}",
        "next_purchase": "/api/predict/next-purchase/{cid}",
    }

    for _, row in sample_df.iterrows():
        cid = str(row["customer_id"])
        pred_row = {
            "customer_id"       : cid,
            "name"              : row.get("name","?"),
            "total_spend"       : row.get("total_spend", 0),
            "total_orders"      : row.get("total_orders", 0),
            "subscription_status": row.get("subscription_status","?"),
            "_churned_label"    : row.get("_churned_label", "?"),
            "_recency_days"     : row.get("_recency_days", "?"),
        }

        # Churn prediction  → /api/customers/<id>/churn
        try:
            r = requests.get(
                f"{BASE_URL}/api/customers/{cid}/churn", timeout=10)
            if r.status_code == 200:
                d = r.json().get("churn_prediction", r.json())
                pred_row["churn_prob"]  = d.get("churn_probability","?")
                pred_row["churn_risk"]  = d.get("risk_level","?")
                pred_row["churn_model"] = d.get("model_used","?")
                churn_pass += 1
            else:
                pred_row["churn_prob"] = f"HTTP {r.status_code}"
                pred_row["churn_risk"] = "—"
                pred_row["churn_model"]= "—"
                churn_fail += 1
        except Exception as e:
            pred_row["churn_prob"] = str(e)[:40]
            pred_row["churn_risk"] = "—"
            pred_row["churn_model"]= "—"
            churn_fail += 1

        # CLV prediction  → /api/customers/<id>/clv
        try:
            r = requests.get(
                f"{BASE_URL}/api/customers/{cid}/clv", timeout=10)
            if r.status_code == 200:
                d = r.json().get("clv_prediction", r.json())
                pred_row["clv_1yr"]     = d.get("clv_1_year", d.get("predicted_clv","?"))
                pred_row["clv_3yr"]     = d.get("clv_3_year", d.get("clv_3yr","?"))
                pred_row["clv_segment"] = d.get("clv_segment", d.get("segment","?"))
                clv_pass += 1
            else:
                pred_row["clv_1yr"]     = f"HTTP {r.status_code}"
                pred_row["clv_3yr"]     = "—"
                pred_row["clv_segment"] = "—"
                clv_fail += 1
        except Exception as e:
            pred_row["clv_1yr"]     = str(e)[:40]
            pred_row["clv_3yr"]     = "—"
            pred_row["clv_segment"] = "—"
            clv_fail += 1

        # Segmentation  → /api/customers/<id>/segment
        try:
            r = requests.get(
                f"{BASE_URL}/api/customers/{cid}/segment", timeout=10)
            if r.status_code == 200:
                d = r.json().get("segment_info", r.json())
                pred_row["segment"]       = d.get("segment", d.get("cluster","?"))
                pred_row["segment_label"] = d.get("segment_label", d.get("label","?"))
                seg_pass += 1
            else:
                pred_row["segment"]       = f"HTTP {r.status_code}"
                pred_row["segment_label"] = "—"
                seg_fail += 1
        except Exception as e:
            pred_row["segment"]       = str(e)[:40]
            pred_row["segment_label"] = "—"
            seg_fail += 1

        # Next purchase date  → /api/customers/<id>/next-purchase
        try:
            r = requests.get(
                f"{BASE_URL}/api/customers/{cid}/next-purchase", timeout=10)
            if r.status_code == 200:
                d = r.json().get("next_purchase", r.json())
                pred_row["next_purchase"] = d.get("predicted_next_purchase",
                                             d.get("next_purchase_date","?"))
                pred_row["days_to_next"]  = d.get("days_until_next_purchase",
                                             d.get("days_to_next","?"))
                nxt_pass += 1
            else:
                pred_row["next_purchase"] = f"HTTP {r.status_code}"
                pred_row["days_to_next"]  = "—"
                nxt_fail += 1
        except Exception as e:
            pred_row["next_purchase"] = str(e)[:40]
            pred_row["days_to_next"]  = "—"
            nxt_fail += 1

        prediction_rows.append(pred_row)

    # Print summary table
    print(f"\n  {'CID':<8} {'Name':<18} {'Spend(£)':<10} "
          f"{'Churn%':<8} {'Risk':<8} {'Segment':<22} {'CLV 1yr':<10}")
    print(f"  {'-'*8} {'-'*18} {'-'*10} {'-'*8} {'-'*8} {'-'*22} {'-'*10}")
    for p in prediction_rows:
        churn_pct = f"{float(p.get('churn_prob',0))*100:.0f}%" \
            if isinstance(p.get("churn_prob"), (int, float)) else str(p.get("churn_prob","?"))
        clv = f"£{p.get('clv_1yr','?'):,.0f}" \
            if isinstance(p.get("clv_1yr"), (int, float)) else str(p.get("clv_1yr","?"))
        print(f"  {str(p['customer_id']):<8} "
              f"{str(p['name'])[:18]:<18} "
              f"£{float(p.get('total_spend',0)):>8,.0f}  "
              f"{churn_pct:<8} "
              f"{str(p.get('churn_risk','?')):<8} "
              f"{str(p.get('segment_label','?'))[:22]:<22} "
              f"{clv:<10}")

    # Record pass/fail
    for test, passed, failed in [
        ("Churn prediction",     churn_pass, churn_fail),
        ("CLV prediction",       clv_pass,   clv_fail),
        ("Segmentation",         seg_pass,   seg_fail),
        ("Next-purchase predict",nxt_pass,   nxt_fail),
    ]:
        status = "PASS" if failed == 0 else ("PARTIAL" if passed > 0 else "FAIL")
        results.append({"test": test, "status": status,
                         "detail": f"pass={passed} fail={failed}"})
        (ok if failed == 0 else fail)(
            f"{test}: {passed}/{passed+failed} passed")

    # Save detailed results CSV
    pd.DataFrame(prediction_rows).to_csv(DETAIL_CSV, index=False)
    ok(f"Prediction results saved → {DETAIL_CSV}")

    return results


# ============================================================
# PHASE 5 — Dashboard / Analytics
# ============================================================

def phase5_analytics(results: list) -> list:
    hdr("PHASE 5 — Dashboard & Analytics APIs")

    endpoints = {
        "Dashboard"            : "/api/dashboard",
        "Analysis summary"     : "/api/analysis/summary",
        "All segments"         : "/api/segments",
        "Model info"           : "/api/model/info",
        "All anomalies"        : "/api/anomalies",
    }

    for label, path in endpoints.items():
        try:
            r = requests.get(f"{BASE_URL}{path}", timeout=15)
            if r.status_code == 200:
                data = r.json()
                keys = list(data.keys())[:5] if isinstance(data, dict) else f"[{len(data)} items]"
                ok(f"{label} → HTTP 200  keys={keys}")
                results.append({"test": label, "status": "PASS",
                                 "detail": f"HTTP 200"})
            else:
                fail(f"{label} → HTTP {r.status_code}")
                results.append({"test": label, "status": "FAIL",
                                 "detail": f"HTTP {r.status_code}"})
        except Exception as e:
            fail(f"{label} → {e}")
            results.append({"test": label, "status": "ERROR",
                             "detail": str(e)})

    return results


# ============================================================
# PHASE 6 — Quality / Accuracy Analysis
# ============================================================

def phase6_quality_analysis(df: pd.DataFrame, results: list):
    hdr("PHASE 6 — Prediction Quality Analysis")

    if not os.path.exists(DETAIL_CSV):
        info("No prediction results file found — skipping quality analysis.")
        return results

    pred_df = pd.read_csv(DETAIL_CSV)

    # Only rows where churn_prob is numeric
    pred_df["churn_prob_num"] = pd.to_numeric(pred_df["churn_prob"], errors="coerce")
    pred_df["true_churn"]     = pd.to_numeric(pred_df.get("_churned_label", 0),
                                               errors="coerce").fillna(0).astype(int)

    valid = pred_df[pred_df["churn_prob_num"].notna()].copy()
    if len(valid) >= 2:
        # Use 0.5 threshold
        pred_binary = (valid["churn_prob_num"] >= 0.5).astype(int)
        correct     = (pred_binary == valid["true_churn"]).sum()
        accuracy    = correct / len(valid)
        ok(f"Churn accuracy on sample (thresh 0.5): "
           f"{correct}/{len(valid)} = {accuracy:.1%}")

        tp = ((pred_binary == 1) & (valid["true_churn"] == 1)).sum()
        fp = ((pred_binary == 1) & (valid["true_churn"] == 0)).sum()
        fn = ((pred_binary == 0) & (valid["true_churn"] == 1)).sum()
        tn = ((pred_binary == 0) & (valid["true_churn"] == 0)).sum()

        print(f"\n  Confusion Matrix:")
        print(f"    {'':20} Predicted=0  Predicted=1")
        print(f"    {'Actual=0 (Active)':<20} TN={tn:<8} FP={fp}")
        print(f"    {'Actual=1 (Churned)':<20} FN={fn:<8} TP={tp}")

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1        = (2 * precision * recall / (precision + recall)
                     if (precision + recall) > 0 else 0.0)
        print(f"\n  Precision : {precision:.3f}")
        print(f"  Recall    : {recall:.3f}")
        print(f"  F1 Score  : {f1:.3f}")

        results.append({"test": "Churn quality (sample)",
                         "status": "PASS" if accuracy >= 0.5 else "WARN",
                         "detail": f"accuracy={accuracy:.2%} F1={f1:.3f}"})
    else:
        info("Not enough numeric churn predictions for accuracy calc.")

    # CLV distribution
    pred_df["clv_num"] = pd.to_numeric(pred_df.get("clv_1yr", None), errors="coerce")
    valid_clv = pred_df[pred_df["clv_num"].notna()]
    if len(valid_clv) > 0:
        print(f"\n  CLV 1-year distribution (£):")
        print(f"    Min  : £{valid_clv['clv_num'].min():,.0f}")
        print(f"    Mean : £{valid_clv['clv_num'].mean():,.0f}")
        print(f"    Max  : £{valid_clv['clv_num'].max():,.0f}")

    return results


# ============================================================
# FINAL REPORT
# ============================================================

def print_final_report(results: list):
    hdr("FINAL TEST REPORT")

    pass_n  = sum(1 for r in results if r["status"] == "PASS")
    fail_n  = sum(1 for r in results if r["status"] == "FAIL")
    warn_n  = sum(1 for r in results if r["status"] in ("WARN","PARTIAL","ERROR"))
    total_n = len(results)

    print(f"\n  {'TEST':<40} {'STATUS':<10} {'DETAIL'}")
    print(f"  {'-'*40} {'-'*10} {'-'*30}")
    for r in results:
        status_icon = "✅" if r["status"] == "PASS" else ("⚠️ " if r["status"] in ("WARN","PARTIAL") else "❌")
        print(f"  {r['test']:<40} {status_icon} {r['status']:<8} {r.get('detail','')}")

    print(f"\n  {'='*65}")
    print(f"  Results: {pass_n} PASS | {fail_n} FAIL | {warn_n} WARN  "
          f"(total: {total_n})")

    pct = pass_n / total_n * 100 if total_n else 0
    print(f"  Pass rate: {pct:.0f}%")

    if fail_n == 0:
        print("  🎉  ALL TESTS PASSED! Vantara handles UCI Retail II perfectly.")
    elif fail_n <= 2:
        print("  🟡  Mostly passing — minor issues detected.")
    else:
        print("  🔴  Multiple failures — check Flask server and DB connection.")
    print(f"  {'='*65}")

    # Save report CSV
    pd.DataFrame(results).to_csv(REPORT_CSV, index=False)
    print(f"\n  Report saved → {REPORT_CSV}")


# ============================================================
# MAIN
# ============================================================

def main():
    print("\n" + "=" * 65)
    print("  Vantara × UCI Online Retail II — Integration Test Suite")
    print(f"  Target server : {BASE_URL}")
    print(f"  Started       : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)

    results = []

    try:
        df = phase1_prepare_data()
        results = phase2_upload(df, results)
        results = phase3_customer_queries(df, results)
        results = phase4_ml_predictions(df, results)
        results = phase5_analytics(results)
        results = phase6_quality_analysis(df, results)
    except Exception as e:
        fail(f"Test suite error: {e}")
        traceback.print_exc()

    print_final_report(results)


if __name__ == "__main__":
    main()
