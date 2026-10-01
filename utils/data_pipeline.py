# ============================================================
# utils/data_pipeline.py — Online Retail II Dataset Pipeline
# ============================================================
# Processes the Online Retail II dataset (UCI/Kaggle).
# Handles both Year 2009-2010 and 2010-2011 sheets.
#
# USAGE:
#   from utils.data_pipeline import load_online_retail_ii
#   df = load_online_retail_ii("path/to/online_retail_II.xlsx")
#
# VALIDATION CHECKS:
#   - Schema / required columns
#   - Null-rate per column
#   - Date-range validation
#   - Missing CustomerID handling
#   - Duplicate transaction removal
#   - Negative Quantity (returns) separation
#   - Zero/negative price filtering
#   - Administrative StockCode filtering
#   - Product description standardisation
#   - Outlier detection (IQR-based)
#   - Chronological sorting
# ============================================================

import re
import logging
import numpy as np
import pandas as pd
from datetime import datetime, date

logger = logging.getLogger(__name__)

# ── Schema ────────────────────────────────────────────────

REQUIRED_COLS = {
    "Invoice":       str,
    "StockCode":     str,
    "Description":   str,
    "Quantity":      float,
    "InvoiceDate":   "datetime",
    "Price":         float,
    "Customer ID":   str,
    "Country":       str,
}

# Administrative / non-product StockCodes to filter
ADMIN_STOCKCODES = {
    "POST", "D", "M", "BANK CHARGES", "PADS", "DOT",
    "CRUK", "AMAZONFEE", "DCGS", "S", "B", "C2",
}
ADMIN_STOCKCODE_PATTERN = re.compile(r'^[A-Z]+$')   # All-letter codes = likely admin


# ══════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════

def load_online_retail_ii(filepath: str) -> dict:
    """
    Load, clean, and validate the Online Retail II dataset.

    Args:
        filepath: Path to the .xlsx file

    Returns:
        {
          "transactions":  pd.DataFrame  ← clean sales (no returns)
          "returns":       pd.DataFrame  ← negative-quantity rows
          "report":        dict          ← validation report
        }
    """
    report = {
        "filepath": filepath,
        "processed_at": datetime.now().isoformat(),
        "steps": [],
    }

    def step(msg, count=None):
        entry = {"step": msg}
        if count is not None:
            entry["rows"] = count
        report["steps"].append(entry)
        logger.info(msg + (f" ({count} rows)" if count is not None else ""))

    # ── 1. Load both sheets ────────────────────────────────
    step("Loading Excel file — both sheets")
    try:
        xl = pd.ExcelFile(filepath, engine="openpyxl")
        sheets = xl.sheet_names[:2]   # Year 2009-10 and 2010-11
        dfs = [xl.parse(s) for s in sheets]
        df  = pd.concat(dfs, ignore_index=True)
        step(f"Loaded sheets: {sheets}", len(df))
    except Exception as e:
        raise ValueError(f"Failed to load {filepath}: {e}")

    # ── 2. Schema check ────────────────────────────────────
    step("Schema validation")
    _validate_schema(df, report)

    # Normalise column names (strip whitespace)
    df.columns = [c.strip() for c in df.columns]

    # ── 3. Null-rate check ─────────────────────────────────
    step("Null-rate check")
    null_rates = (df.isnull().sum() / len(df) * 100).round(2)
    report["null_rates"] = null_rates.to_dict()
    for col, rate in null_rates.items():
        if rate > 50:
            logger.warning(f"Column '{col}' has {rate:.1f}% null values")

    # ── 4. Missing Customer ID → label & keep separate ─────
    missing_cid = df["Customer ID"].isna()
    report["missing_customer_id_count"] = int(missing_cid.sum())
    step(f"Removed {missing_cid.sum()} rows with missing Customer ID")
    df = df[~missing_cid].copy()
    df["Customer ID"] = df["Customer ID"].astype(str).str.strip()

    # ── 5. Parse dates ─────────────────────────────────────
    step("Parsing InvoiceDate")
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    bad_dates = df["InvoiceDate"].isna().sum()
    if bad_dates > 0:
        logger.warning(f"{bad_dates} rows have unparseable dates — dropped")
        df = df.dropna(subset=["InvoiceDate"])

    # ── 6. Date-range validation ───────────────────────────
    step("Date-range validation")
    d_min, d_max = df["InvoiceDate"].min(), df["InvoiceDate"].max()
    report["date_range"] = {"from": str(d_min), "to": str(d_max)}
    if d_min.year < 2000 or d_max.year > 2025:
        logger.warning(f"Suspicious date range: {d_min} → {d_max}")

    # ── 7. Chronological sort ──────────────────────────────
    step("Chronological sort")
    df.sort_values("InvoiceDate", inplace=True)
    df.reset_index(drop=True, inplace=True)

    # ── 8. Duplicate transaction removal ───────────────────
    before = len(df)
    df.drop_duplicates(
        subset=["Invoice", "StockCode", "Customer ID", "Quantity", "Price"],
        keep="first", inplace=True
    )
    dupes = before - len(df)
    report["duplicates_removed"] = dupes
    step(f"Removed {dupes} duplicate transactions", len(df))

    # ── 9. Separate returns (negative Quantity) ────────────
    returns_df = df[df["Quantity"] < 0].copy()
    df = df[df["Quantity"] > 0].copy()
    report["return_rows"] = len(returns_df)
    step(f"Separated {len(returns_df)} return rows (negative Quantity)", len(df))

    # ── 10. Zero / negative price filtering ───────────────
    before = len(df)
    df = df[df["Price"] > 0].copy()
    report["zero_price_removed"] = before - len(df)
    step(f"Removed {before - len(df)} zero/negative price rows", len(df))

    # ── 11. Administrative StockCode filtering ─────────────
    before = len(df)
    df = df[~df["StockCode"].isin(ADMIN_STOCKCODES)]
    # Also remove purely alphabetic codes (e.g. "PADS", "M")
    df = df[~df["StockCode"].str.match(r'^[A-Za-z]+$', na=False)]
    report["admin_stockcodes_removed"] = before - len(df)
    step(f"Removed {before - len(df)} admin-StockCode rows", len(df))

    # ── 12. Description standardisation ───────────────────
    step("Standardising product descriptions")
    df["Description"] = (
        df["Description"]
        .fillna("UNKNOWN")
        .str.upper()
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
    )

    # ── 13. Outlier detection (IQR) ───────────────────────
    step("Outlier detection (IQR-based flagging)")
    df = _flag_outliers(df, report)

    # ── 14. Compute LineValue ──────────────────────────────
    df["LineValue"] = df["Quantity"] * df["Price"]

    report["final_transaction_count"] = len(df)
    report["final_customer_count"]    = df["Customer ID"].nunique()
    report["final_product_count"]     = df["StockCode"].nunique()

    step("Pipeline complete", len(df))
    return {
        "transactions": df,
        "returns":      returns_df,
        "report":       report,
    }


def build_customer_features(df: pd.DataFrame,
                              cutoff_date: date = None) -> pd.DataFrame:
    """
    Aggregate transaction-level data into customer-level RFM features.
    Respects point-in-time cutoff to prevent leakage.

    Args:
        df: clean transactions dataframe (from load_online_retail_ii)
        cutoff_date: exclude transactions after this date

    Returns:
        DataFrame with one row per customer
    """
    if cutoff_date:
        df = df[df["InvoiceDate"].dt.date <= cutoff_date].copy()

    snapshot = df["InvoiceDate"].max().date() if cutoff_date is None else cutoff_date

    cust = df.groupby("Customer ID").agg(
        last_purchase_date=("InvoiceDate", "max"),
        first_purchase_date=("InvoiceDate", "min"),
        frequency=("Invoice", "nunique"),
        monetary=("LineValue", "sum"),
        total_items=("Quantity", "sum"),
        avg_basket_value=("LineValue", "mean"),
        unique_products=("StockCode", "nunique"),
        unique_categories=("Description", "nunique"),
        country=("Country", lambda x: x.mode()[0] if len(x) > 0 else "Unknown"),
    ).reset_index()

    cust["recency_days"] = (
        pd.to_datetime(snapshot) - cust["last_purchase_date"]
    ).dt.days

    cust["customer_lifespan_days"] = (
        cust["last_purchase_date"] - cust["first_purchase_date"]
    ).dt.days.clip(lower=0)

    cust["avg_order_value"] = cust["monetary"] / cust["frequency"].clip(lower=1)

    cust["purchase_rate"] = (
        cust["frequency"] / (cust["customer_lifespan_days"] / 30.0).clip(lower=1)
    ).round(4)

    # Historical CLV (simple heuristic)
    cust["historical_clv"] = cust["monetary"] * (1 + cust["frequency"] / 10.0)

    return cust


# ── Helpers ───────────────────────────────────────────────

def _validate_schema(df: pd.DataFrame, report: dict):
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    report["schema_check"] = "PASSED"


def _flag_outliers(df: pd.DataFrame, report: dict) -> pd.DataFrame:
    outlier_counts = {}
    for col in ["Quantity", "Price"]:
        q1, q3  = df[col].quantile([0.25, 0.75])
        iqr     = q3 - q1
        lo, hi  = q1 - 3 * iqr, q3 + 3 * iqr
        mask    = (df[col] < lo) | (df[col] > hi)
        outlier_counts[col] = int(mask.sum())
        df[f"{col}_outlier"] = mask

    report["outliers_flagged"] = outlier_counts
    total = sum(outlier_counts.values())
    logger.info(f"Flagged {total} outlier rows (not removed — flagged only)")
    return df
