# ============================================================
# test_all_apis.py — Full API Test Suite for Vantara Backend
# ============================================================
# Run this script while app.py is running to verify ALL APIs.
#
# HOW TO RUN:
#   1. Start Flask: C:\Vantara-venv\Scripts\python.exe app.py
#   2. In a new terminal:
#      C:\Vantara-venv\Scripts\python.exe test_all_apis.py
#
# WHAT IT TESTS:
#   - Health & DB endpoints
#   - Customer CRUD APIs
#   - Dashboard API
#   - Behavior Analysis
#   - Churn Prediction (ML)
#   - CLV Prediction (ML)
#   - Segmentation
#   - Customer Insights (AI)
#   - Analysis Summary
# ============================================================

import urllib.request
import urllib.error
import json
import sys

BASE_URL = "http://localhost:5000"

# Test counters
passed = 0
failed = 0
results = []


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get(endpoint, label):
    """Make a GET request and return parsed JSON."""
    url = f"{BASE_URL}{endpoint}"
    try:
        res  = urllib.request.urlopen(url, timeout=10)
        data = json.loads(res.read())
        return data, res.getcode()
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code
    except Exception as ex:
        return {"error": str(ex)}, 0


def check(label, condition, detail=""):
    """Record a pass or fail for a test."""
    global passed, failed
    status = "PASS" if condition else "FAIL"
    if condition:
        passed += 1
    else:
        failed += 1
    results.append((status, label, detail))


def section(title):
    print(f"\n  {'-'*50}")
    print(f"  {title}")
    print(f"  {'-'*50}")


# ============================================================
# RUN ALL TESTS
# ============================================================

print("=" * 58)
print("  VANTARA BACKEND — FULL API TEST SUITE")
print("=" * 58)

# ────────────────────────────────────────────
# 1. HEALTH CHECKS
# ────────────────────────────────────────────
section("1. HEALTH & DATABASE ENDPOINTS")

data, code = get("/api/health", "Health")
check("GET /api/health returns 200", code == 200)
check("Health status is 'healthy'", data.get("status") == "healthy")

data, code = get("/api/db-test", "DB Test")
check("GET /api/db-test returns 200", code == 200)
check("DB test returns customer count",
      "total_customers" in data or "customers" in data or data.get("success") is not False)

# ────────────────────────────────────────────
# 2. CUSTOMER CRUD APIs
# ────────────────────────────────────────────
section("2. CUSTOMER APIs")

# GET all customers
data, code = get("/api/customers", "Get All")
check("GET /api/customers returns 200", code == 200)
check("Returns customer list", "customers" in data)
check("Returns pagination info", "pagination" in data)
total = data.get("pagination", {}).get("total_customers", 0)
check(f"Has customers in DB ({total} total)", total > 0)

# GET with filter
data, code = get("/api/customers?location=Mumbai", "Filter by city")
check("GET /api/customers?location=Mumbai works", code == 200)

data, code = get("/api/customers?status=Premium", "Filter by status")
check("GET /api/customers?status=Premium works", code == 200)

# GET one customer
data, code = get("/api/customers/C1001", "Get One")
check("GET /api/customers/C1001 returns 200", code == 200)
check("Returns customer object", "customer" in data)
check("Returns purchase history", "purchase_history" in data)
check("Customer name is correct",
      data.get("customer", {}).get("name") == "Ananya Sharma")

# GET non-existent customer
data, code = get("/api/customers/XXXXX", "Not Found")
check("GET /api/customers/XXXXX returns 404", code == 404)
check("Returns error message", "error" in data)

# ────────────────────────────────────────────
# 3. DASHBOARD API
# ────────────────────────────────────────────
section("3. DASHBOARD API")

data, code = get("/api/dashboard", "Dashboard")
check("GET /api/dashboard returns 200", code == 200)
check("Has customer_overview", "customer_overview" in data.get("dashboard", {}))
check("Has revenue_summary",   "revenue_summary"   in data.get("dashboard", {}))
check("Has risk_and_value",    "risk_and_value"    in data.get("dashboard", {}))
check("Has purchase_insights", "purchase_insights" in data.get("dashboard", {}))
check("Total customers > 0",
      data.get("dashboard", {}).get("customer_overview", {}).get("total_customers", 0) > 0)
check("Total revenue > 0",
      data.get("dashboard", {}).get("revenue_summary", {}).get("total_revenue", 0) > 0)

# ────────────────────────────────────────────
# 4. BEHAVIOR ANALYSIS
# ────────────────────────────────────────────
section("4. BEHAVIOR ANALYSIS API")

data, code = get("/api/customers/C1004/behavior", "Behavior")
check("GET /api/customers/C1004/behavior returns 200", code == 200)
check("Has behavior_analysis key", "behavior_analysis" in data)
b = data.get("behavior_analysis", {})
check("Has recency_label",     "recency_label"     in b)
check("Has frequency_label",   "frequency_label"   in b)
check("Has spending_level",    "spending_level"    in b)
check("Has favorite_category", "favorite_category" in b)
check("Has insight text",      bool(b.get("insight")))

# ────────────────────────────────────────────
# 5. CHURN PREDICTION (ML)
# ────────────────────────────────────────────
section("5. CHURN PREDICTION API (ML)")

data, code = get("/api/customers/C1001/churn", "Churn Low")
check("GET /api/customers/C1001/churn returns 200", code == 200)
c = data.get("churn_prediction", {})
check("Has churn_probability", "churn_probability" in c)
check("Probability is between 0 and 1",
      0 <= c.get("churn_probability", -1) <= 1)
check("C1001 (premium, high spend) is Low/Medium risk",
      c.get("risk_level") in ["Low", "Medium"])
check("Uses ML model",
      "Random Forest" in c.get("model_used", ""))

data, code = get("/api/customers/C1010/churn", "Churn High")
c2 = data.get("churn_prediction", {})
check("C1010 (cancelled, 1 order) is High risk",
      c2.get("risk_level") == "High")

# ────────────────────────────────────────────
# 6. CLV PREDICTION (ML)
# ────────────────────────────────────────────
section("6. CLV PREDICTION API (ML)")

data, code = get("/api/customers/C1004/clv", "CLV")
check("GET /api/customers/C1004/clv returns 200", code == 200)
v = data.get("clv_prediction", {})
check("Has predicted_clv",        "predicted_clv"        in v)
check("Has clv_tier",             "clv_tier"             in v)
check("Has recommended_action",   "recommended_action"   in v)
check("CLV is a positive number", v.get("predicted_clv", -1) >= 0)
check("Uses ML model",            "Random Forest" in v.get("model_used", ""))
check("C1004 (top spend) is Gold or Platinum",
      v.get("clv_tier") in ["Gold", "Platinum"])

# ────────────────────────────────────────────
# 7. SEGMENTATION
# ────────────────────────────────────────────
section("7. SEGMENTATION API")

data, code = get("/api/segments", "Segments")
check("GET /api/segments returns 200", code == 200)
s = data.get("segmentation", {})
check("Has total_customers",       "total_customers"       in s)
check("Has summary breakdown",     "summary"               in s)
check("Has customers_by_segment",  "customers_by_segment"  in s)
check("Has all 5 segments", all(
    seg in s.get("summary", {})
    for seg in ["High Value", "Regular", "New", "Inactive", "High Risk"]
))
check("High Value count > 0",
      s.get("summary", {}).get("High Value", {}).get("count", 0) > 0)

# Single customer segment
data, code = get("/api/customers/C1004/segment", "Single Segment")
check("GET /api/customers/C1004/segment returns 200", code == 200)
check("Segment name is High Value",
      data.get("segment_info", {}).get("segment") == "High Value")

# ────────────────────────────────────────────
# 8. AI INSIGHTS
# ────────────────────────────────────────────
section("8. AI INSIGHTS API")

data, code = get("/api/customers/C1001/insights", "Insights C1001")
check("GET /api/customers/C1001/insights returns 200", code == 200)
r = data.get("intelligence_report", {})
check("Has ai_summary",        bool(r.get("ai_summary")))
check("Has health_score",      "health_score"    in r)
check("Has predictions block", "predictions"     in r)
check("Has recommendations",   len(r.get("recommendations", [])) > 0)
check("Health score is 0-100", 0 <= r.get("health_score", -1) <= 100)
check("C1001 is Excellent or Good",
      r.get("health_label") in ["Excellent", "Good"])

data, code = get("/api/customers/C1010/insights", "Insights C1010")
r2 = data.get("intelligence_report", {})
check("C1010 health score is Poor or Critical",
      r2.get("health_label") in ["Poor", "Critical"])

# ────────────────────────────────────────────
# 9. ANALYSIS SUMMARY
# ────────────────────────────────────────────
section("9. ANALYSIS SUMMARY API")

data, code = get("/api/analysis/summary", "Summary")
check("GET /api/analysis/summary returns 200", code == 200)
sm = data.get("summary", {})
check("Has total_customers_analyzed", "total_customers_analyzed" in sm)
check("Has total_revenue",            "total_revenue"            in sm)
check("Has average_spend",            "average_spend_per_customer" in sm)
check("Revenue is positive",          sm.get("total_revenue", 0) > 0)

# ============================================================
# FINAL REPORT
# ============================================================
print(f"\n{'='*58}")
print(f"  TEST RESULTS SUMMARY")
print(f"{'='*58}")

max_label = max(len(r[1]) for r in results)
for status, label, detail in results:
    mark = "[PASS]" if status == "PASS" else "[FAIL]"
    print(f"  {mark}  {label}")

print(f"\n{'='*58}")
print(f"  Total : {passed + failed}")
print(f"  Passed: {passed}")
print(f"  Failed: {failed}")
pct = round(passed / (passed + failed) * 100, 1) if (passed + failed) > 0 else 0
print(f"  Score : {pct}%")
print(f"{'='*58}")

if failed == 0:
    print("\n  ALL TESTS PASSED! Backend is fully operational.")
else:
    print(f"\n  {failed} test(s) failed. Check the output above.")

sys.exit(0 if failed == 0 else 1)
