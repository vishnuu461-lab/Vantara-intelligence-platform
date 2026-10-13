# ============================================================
# data/load_online_retail_ii.py
# ============================================================
# Downloads the UCI Online Retail II dataset via ucimlrepo,
# engineers customer-level features (RFM + derived metrics),
# and exports two artefacts:
#
#   data/online_retail_ii_customers.csv   ← Vantara upload CSV
#   data/online_retail_ii_raw.csv         ← raw transactions
#
# HOW TO RUN:
#   .venv\Scripts\python.exe data/load_online_retail_ii.py
#
# OUTPUT COLUMNS (matches Vantara upload schema):
#   customer_id, name, age, gender, location, email,
#   total_orders, total_spend, average_order_value,
#   last_purchase_date, website_visits, complaints,
#   subscription_status
#
# FEATURE-ENGINEERING NOTES:
#   • Recency / Frequency / Monetary from raw invoices
#   • Churn label  : recency > 90 days from dataset max-date
#   • Subscription : derived from purchase frequency quartile
#   • website_visits / complaints : synthetic proxies (see below)
#   • Cancelled invoices (InvoiceNo starting with 'C') removed
#   • Negative quantities removed (restocking/returns)
# ============================================================

import sys
import os
import hashlib
from datetime import timedelta

import numpy as np
import pandas as pd

# ── Path setup ────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
DATA_DIR = os.path.join(ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)

OUTPUT_CSV     = os.path.join(DATA_DIR, "online_retail_ii_customers.csv")
RAW_CSV        = os.path.join(DATA_DIR, "online_retail_ii_raw.csv")

SNAPSHOT_DATE_OFFSET_DAYS = 0   # "today" relative to max invoice date


# ============================================================
# STEP 1 — Download dataset
# ============================================================

def download_dataset() -> pd.DataFrame:
    """
    Download Online Retail II from UCI and return raw DataFrame.
    Strategy:
      1. Try ucimlrepo (fast, no file needed)
      2. Fall back to direct ZIP download from UCI static URL
      3. If both fail, load local excel if present
    """
    print("\n[1/5] Fetching Online Retail II from UCI repository …")

    xlsx_path = os.path.join(DATA_DIR, "online_retail_II.xlsx")
    zip_path  = os.path.join(DATA_DIR, "online_retail_ii.zip")
    UCI_ZIP   = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"

    # ── Try ucimlrepo first ────────────────────────────────────
    try:
        from ucimlrepo import fetch_ucirepo
        print("  Trying ucimlrepo …")
        dataset = fetch_ucirepo(id=502)
        df_X = dataset.data.features
        df_y = dataset.data.targets
        df   = pd.concat([df_X, df_y], axis=1) if df_y is not None else df_X.copy()
        print(f"  ✓  Loaded via ucimlrepo : {len(df):,} rows")
        return df
    except Exception as e:
        print(f"  ⚠  ucimlrepo failed ({e}) — falling back to direct download …")

    # ── Load xlsx if already present ──────────────────────────
    if not os.path.exists(xlsx_path):
        # Download ZIP
        if not os.path.exists(zip_path):
            print(f"  Downloading from {UCI_ZIP} …")
            import urllib.request
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode    = ssl.CERT_NONE
            urllib.request.urlretrieve(UCI_ZIP, zip_path)
            print(f"  ✓  Downloaded ZIP → {zip_path}")
        else:
            print(f"  ✓  ZIP already cached: {zip_path}")

        # Extract xlsx
        import zipfile
        print("  Extracting xlsx …")
        with zipfile.ZipFile(zip_path, "r") as z:
            names = z.namelist()
            print(f"     Contents: {names}")
            xlsx_names = [n for n in names if n.lower().endswith(".xlsx")]
            if not xlsx_names:
                raise FileNotFoundError(f"No .xlsx found in ZIP. Contents: {names}")
            z.extract(xlsx_names[0], DATA_DIR)
            extracted = os.path.join(DATA_DIR, xlsx_names[0])
            if extracted != xlsx_path:
                os.rename(extracted, xlsx_path)
        print(f"  ✓  Extracted → {xlsx_path}")
    else:
        print(f"  ✓  Using cached xlsx: {xlsx_path}")

    # ── Load both sheets ──────────────────────────────────────
    print("  Reading sheet 'Year 2009-2010' …")
    df1 = pd.read_excel(xlsx_path, sheet_name="Year 2009-2010", engine="openpyxl")
    print(f"     {len(df1):,} rows")
    print("  Reading sheet 'Year 2010-2011' …")
    df2 = pd.read_excel(xlsx_path, sheet_name="Year 2010-2011", engine="openpyxl")
    print(f"     {len(df2):,} rows")

    df = pd.concat([df1, df2], ignore_index=True)
    print(f"  ✓  Total raw rows : {len(df):,}")
    print(f"  ✓  Columns        : {list(df.columns)}")
    return df


# ============================================================
# STEP 2 — Clean transactional data
# ============================================================

def clean_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove:
      • Cancellations (InvoiceNo starts with 'C')
      • Rows with missing CustomerID
      • Rows with Quantity <= 0  (returns / restocking)
      • Rows with UnitPrice <= 0  (free items / adjustments)
    """
    print("\n[2/5] Cleaning transactions …")
    n0 = len(df)

    # Normalise column names
    df.columns = df.columns.str.strip()

    # Handle both possible spellings: Invoice / InvoiceNo
    if "Invoice" in df.columns and "InvoiceNo" not in df.columns:
        df = df.rename(columns={"Invoice": "InvoiceNo"})
    if "Customer ID" in df.columns and "CustomerID" not in df.columns:
        df = df.rename(columns={"Customer ID": "CustomerID"})
    if "Price" in df.columns and "UnitPrice" not in df.columns:
        df = df.rename(columns={"Price": "UnitPrice"})

    # Drop cancellations
    df = df[~df["InvoiceNo"].astype(str).str.startswith("C")]

    # Drop missing customer
    df = df[df["CustomerID"].notna()]

    # Positive quantity & price only
    df = df[(df["Quantity"] > 0) & (df["UnitPrice"] > 0)]

    # Parse datetime
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    df = df[df["InvoiceDate"].notna()]

    # Compute line revenue
    df["LineRevenue"] = df["Quantity"] * df["UnitPrice"]

    df["CustomerID"] = df["CustomerID"].astype(int).astype(str)

    print(f"  ✓  Rows before cleaning : {n0:,}")
    print(f"  ✓  Rows after  cleaning : {len(df):,}")
    print(f"  ✓  Unique customers     : {df['CustomerID'].nunique():,}")

    # Save raw (cleaned) CSV
    df.to_csv(RAW_CSV, index=False)
    print(f"  ✓  Raw cleaned CSV saved → {RAW_CSV}")
    return df


# ============================================================
# STEP 3 — Engineer customer-level features
# ============================================================

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate transaction-level data into one row per customer.

    Features computed:
      RFM:
        recency_days        — days since last purchase
        frequency           — number of distinct invoices
        monetary            — total spend (£)
      Derived:
        avg_order_value     — monetary / frequency
        total_items         — total quantity purchased
        unique_products     — distinct StockCode count
        unique_countries    — countries shopped from
      Synthetic proxies:
        website_visits      — proportional to frequency + recency
        complaints          — derived from return-pattern in cancelled
        subscription_status — by frequency quartile
    """
    print("\n[3/5] Engineering customer features …")

    snapshot = df["InvoiceDate"].max() + timedelta(days=SNAPSHOT_DATE_OFFSET_DAYS)
    print(f"  ✓  Snapshot date (reference 'today') : {snapshot.date()}")

    grp = df.groupby("CustomerID")

    rfm = pd.DataFrame({
        "recency_days"    : (snapshot - grp["InvoiceDate"].max()).dt.days,
        "frequency"       : grp["InvoiceNo"].nunique(),
        "monetary"        : grp["LineRevenue"].sum().round(2),
        "total_items"     : grp["Quantity"].sum(),
        "unique_products" : grp["StockCode"].nunique(),
        "last_invoice_dt" : grp["InvoiceDate"].max(),
    })

    rfm["avg_order_value"] = (rfm["monetary"] / rfm["frequency"]).round(2)

    # Country — take the most frequent one per customer
    country_mode = (
        df.groupby("CustomerID")["Country"]
        .agg(lambda x: x.mode().iloc[0] if len(x) > 0 else "United Kingdom")
    )
    rfm["country"] = country_mode

    # ── Subscription status from frequency quartile ──────────
    q1, q2, q3 = rfm["frequency"].quantile([0.25, 0.50, 0.75])
    def subscription_from_freq(freq):
        if freq >= q3:    return "Premium"
        elif freq >= q2:  return "Active"
        elif freq >= q1:  return "Active"
        else:             return "Inactive"

    rfm["subscription_status"] = rfm["frequency"].apply(subscription_from_freq)

    # ── Synthetic website_visits ──────────────────────────────
    # Idea: more frequent  + less recency → more site visits
    rng = np.random.default_rng(seed=42)
    freq_norm    = (rfm["frequency"] - rfm["frequency"].min()) / (rfm["frequency"].max() - rfm["frequency"].min() + 1e-9)
    rec_norm_inv = 1.0 - (rfm["recency_days"] - rfm["recency_days"].min()) / (rfm["recency_days"].max() - rfm["recency_days"].min() + 1e-9)
    base_visits  = (freq_norm * 80 + rec_norm_inv * 40).clip(1, 200)
    rfm["website_visits"] = (
        base_visits + rng.integers(0, 20, size=len(rfm))
    ).astype(int).clip(0, 250)

    # ── Synthetic complaints ──────────────────────────────────
    # Low-spend + high-recency customers get more complaints
    spend_norm  = (rfm["monetary"] - rfm["monetary"].min()) / (rfm["monetary"].max() - rfm["monetary"].min() + 1e-9)
    complaint_p = (0.5 - spend_norm * 0.4 + rec_norm_inv * 0.1 * 0).clip(0.02, 0.45)
    rfm["complaints"] = rng.binomial(n=6, p=complaint_p).clip(0, 6)

    # ── Churn label (for analysis; NOT uploaded to Vantara) ───
    # Customers inactive > 90 days  → churned
    rfm["churned"] = (rfm["recency_days"] > 90).astype(int)

    print(f"  ✓  Customers engineered : {len(rfm):,}")
    print(f"  ✓  Churned (recency>90) : {rfm['churned'].sum():,} "
          f"({rfm['churned'].mean()*100:.1f}%)")
    print(f"  ✓  Avg monetary (£)     : {rfm['monetary'].mean():.2f}")
    print(f"  ✓  Avg frequency        : {rfm['frequency'].mean():.1f}")

    return rfm


# ============================================================
# STEP 4 — Map to Vantara CSV schema
# ============================================================

def map_to_vantara_schema(rfm: pd.DataFrame) -> pd.DataFrame:
    """
    Produce a DataFrame matching the Vantara upload schema exactly:
      customer_id, name, age, gender, location, email,
      total_orders, total_spend, average_order_value,
      last_purchase_date, website_visits, complaints,
      subscription_status
    """
    print("\n[4/5] Mapping to Vantara schema …")

    rng = np.random.default_rng(seed=99)

    # ── Synthetic name  ───────────────────────────────────────
    # UK retail dataset has no real names; generate placeholder
    first_names = [
        "Oliver","Emma","Harry","Olivia","George","Ava","Jack","Isabella",
        "Charlie","Sophia","Thomas","Mia","James","Lily","Daniel","Amelia",
        "Henry","Grace","William","Ella","Noah","Chloe","Liam","Zoe",
        "Ethan","Ellie","Lucas","Freya","Mason","Layla"
    ]
    last_names = [
        "Smith","Jones","Williams","Brown","Taylor","Davies","Evans","Wilson",
        "Thomas","Johnson","Roberts","Walker","Wright","Thompson","Robinson",
        "White","Hughes","Edwards","Lewis","Clarke","Harrison","Bell","Wood",
        "Morris","Clarke","Green","Scott","Young","Hall","Turner"
    ]

    n = len(rfm)
    fn = rng.choice(first_names, n)
    ln = rng.choice(last_names, n)
    names = [f"{f} {l}" for f, l in zip(fn, ln)]

    # ── Synthetic age ───────────────────────────────────────────
    ages = rng.integers(18, 70, n)

    # ── Gender ─────────────────────────────────────────────────
    genders = rng.choice(["Male", "Female"], n, p=[0.38, 0.62])  # UK gift retail skews female

    # ── Email  ──────────────────────────────────────────────────
    def make_email(name, cid):
        slug = name.lower().replace(" ", ".")
        hash6 = hashlib.md5(cid.encode()).hexdigest()[:4]
        return f"{slug}.{hash6}@retaildata.io"

    emails = [make_email(nm, cid) for nm, cid in zip(names, rfm.index)]

    # ── Build the output DataFrame ───────────────────────────────
    out = pd.DataFrame({
        "customer_id"          : rfm.index,
        "name"                 : names,
        "age"                  : ages,
        "gender"               : genders,
        "location"             : rfm["country"].values,
        "email"                : emails,
        "total_orders"         : rfm["frequency"].values,
        "total_spend"          : rfm["monetary"].values,
        "average_order_value"  : rfm["avg_order_value"].values,
        "last_purchase_date"   : rfm["last_invoice_dt"].dt.strftime("%Y-%m-%d").values,
        "website_visits"       : rfm["website_visits"].values,
        "complaints"           : rfm["complaints"].values,
        "subscription_status"  : rfm["subscription_status"].values,
        # Extra analytical columns (not in Vantara schema — kept for reference)
        "_recency_days"        : rfm["recency_days"].values,
        "_monetary_gbp"        : rfm["monetary"].values,
        "_churned_label"       : rfm["churned"].values,
        "_unique_products"     : rfm["unique_products"].values,
    })

    print(f"  ✓  Output rows  : {len(out):,}")
    print(f"  ✓  Columns      : {list(out.columns)}")
    return out


# ============================================================
# STEP 5 — Save and print summary
# ============================================================

def save_and_summarise(out: pd.DataFrame):
    print("\n[5/5] Saving output CSV …")

    out.to_csv(OUTPUT_CSV, index=False)
    print(f"  ✓  Saved → {OUTPUT_CSV}")

    # Stats
    churn_col = out["_churned_label"]
    print("\n" + "=" * 60)
    print("  DATASET SUMMARY")
    print("=" * 60)
    print(f"  Total customers       : {len(out):,}")
    print(f"  Churned (recency>90d) : {churn_col.sum():,} ({churn_col.mean()*100:.1f}%)")
    print(f"  Avg total spend (£)   : {out['total_spend'].mean():,.2f}")
    print(f"  Avg orders/customer   : {out['total_orders'].mean():.1f}")
    print(f"  Avg AOV (£)           : {out['average_order_value'].mean():.2f}")
    print(f"  Premium subscribers   : {(out['subscription_status']=='Premium').sum():,}")
    print(f"  Active subscribers    : {(out['subscription_status']=='Active').sum():,}")
    print(f"  Inactive subscribers  : {(out['subscription_status']=='Inactive').sum():,}")
    print("=" * 60)

    print("\n  TOP 5 CUSTOMERS BY SPEND:")
    top5 = out.nlargest(5, "total_spend")[
        ["customer_id","name","total_spend","total_orders","subscription_status"]
    ]
    print(top5.to_string(index=False))

    print("\n  SAMPLE CHURN-RISK CUSTOMERS:")
    risky = out[out["_churned_label"]==1].nlargest(5, "total_spend")[
        ["customer_id","name","total_spend","_recency_days","subscription_status"]
    ]
    print(risky.to_string(index=False))

    print(f"\n  ✅ Ready to upload → {OUTPUT_CSV}")
    print(f"  ✅ Raw transactions  → {RAW_CSV}")


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("  Vantara × UCI Online Retail II — Data Loader")
    print("=" * 60)

    raw    = download_dataset()
    clean  = clean_transactions(raw)
    rfm    = engineer_features(clean)
    out    = map_to_vantara_schema(rfm)
    save_and_summarise(out)

    return out


if __name__ == "__main__":
    main()
