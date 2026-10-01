# ============================================================
# utils/data_cleaning.py — CSV Data Validation & Cleaning
# ============================================================
# This file handles all data validation and cleaning logic
# for CSV uploads.
#
# WHY SEPARATE FROM THE ROUTE?
#   Routes handle HTTP. Cleaning logic belongs here.
#   This keeps code modular and easy to test independently.
#
# WHAT IT DOES:
#   1. Checks required columns exist
#   2. Validates data types (numbers are numbers, etc.)
#   3. Cleans common issues (extra spaces, wrong case, etc.)
#   4. Flags rows with problems
#   5. Returns clean rows + a report of issues found
# ============================================================

import pandas as pd
from datetime import datetime


# ============================================================
# REQUIRED AND OPTIONAL COLUMNS
# ============================================================

REQUIRED_COLUMNS = ["customer_id", "name"]

OPTIONAL_COLUMNS = [
    "age", "gender", "location", "email",
    "total_orders", "total_spend", "average_order_value",
    "last_purchase_date", "website_visits", "complaints",
    "subscription_status"
]

ALL_EXPECTED_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS

VALID_SUBSCRIPTION_STATUSES = ["Active", "Inactive", "Premium", "Cancelled"]
VALID_GENDERS               = ["Male", "Female", "Other", "M", "F"]


# ============================================================
# MAIN FUNCTION: Validate and Clean a DataFrame
# ============================================================

def validate_and_clean(df):
    """
    Validates and cleans a pandas DataFrame from a CSV upload.

    Args:
        df (pd.DataFrame): Raw data from uploaded CSV

    Returns:
        dict: {
            "valid_rows": list of cleaned dicts ready for DB insert,
            "skipped_rows": list of invalid rows with reasons,
            "warnings": list of non-critical issues that were fixed,
            "stats": summary counts
        }
    """
    valid_rows   = []
    skipped_rows = []
    warnings     = []

    # --------------------------------------------------------
    # STEP 1: Normalize column names
    # Remove extra spaces, convert to lowercase
    # e.g., "Customer ID " → "customer_id"
    # --------------------------------------------------------
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("-", "_")
    )

    # --------------------------------------------------------
    # STEP 2: Check required columns exist
    # --------------------------------------------------------
    missing_required = [
        col for col in REQUIRED_COLUMNS
        if col not in df.columns
    ]
    if missing_required:
        raise ValueError(
            f"CSV is missing required columns: {missing_required}. "
            f"Required columns are: {REQUIRED_COLUMNS}"
        )

    # --------------------------------------------------------
    # STEP 3: Warn about unexpected columns (not an error)
    # --------------------------------------------------------
    unknown_cols = [
        col for col in df.columns
        if col not in ALL_EXPECTED_COLUMNS
    ]
    if unknown_cols:
        warnings.append(
            f"These columns were ignored (not recognized): {unknown_cols}"
        )

    # Fill missing optional columns with None/NaN
    for col in OPTIONAL_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # --------------------------------------------------------
    # STEP 4: Process each row
    # --------------------------------------------------------
    for index, row in df.iterrows():
        row_num   = index + 2   # +2 because row 1 is header, index starts at 0
        row_errors = []
        row_warnings = []
        cleaned   = {}

        # --- customer_id ---
        cid = str(row.get("customer_id", "")).strip()
        if not cid or cid.lower() in ["nan", "none", ""]:
            row_errors.append("customer_id is missing or empty")
        else:
            cleaned["customer_id"] = cid

        # --- name ---
        name = str(row.get("name", "")).strip()
        if not name or name.lower() in ["nan", "none", ""]:
            row_errors.append("name is missing or empty")
        else:
            # Capitalize name properly (e.g., "john doe" → "John Doe")
            cleaned["name"] = name.title()
            if name != cleaned["name"]:
                row_warnings.append(f"name capitalized: '{name}' → '{cleaned['name']}'")

        # If required fields are missing, skip this row entirely
        if row_errors:
            skipped_rows.append({
                "row": row_num,
                "data": row.to_dict(),
                "errors": row_errors
            })
            continue

        # --- age ---
        age = parse_int(row.get("age"))
        if age is not None:
            if age < 0 or age > 120:
                row_warnings.append(f"age {age} looks unusual — accepted anyway")
            cleaned["age"] = age
        else:
            cleaned["age"] = None

        # --- gender ---
        gender = str(row.get("gender", "")).strip()
        if gender and gender.lower() not in ["nan", "none", ""]:
            # Normalize M/F → Male/Female
            gender_map = {"m": "Male", "f": "Female"}
            gender_normalized = gender_map.get(gender.lower(), gender.title())
            cleaned["gender"] = gender_normalized
        else:
            cleaned["gender"] = None

        # --- location ---
        location = str(row.get("location", "")).strip()
        cleaned["location"] = location.title() if location and location.lower() not in ["nan", "none"] else None

        # --- email ---
        email = str(row.get("email", "")).strip().lower()
        if email and email not in ["nan", "none", ""]:
            if "@" not in email or "." not in email:
                row_warnings.append(f"email '{email}' looks invalid — accepted anyway")
            cleaned["email"] = email
        else:
            cleaned["email"] = None

        # --- total_orders ---
        cleaned["total_orders"] = parse_int(row.get("total_orders")) or 0

        # --- total_spend ---
        cleaned["total_spend"] = parse_float(row.get("total_spend")) or 0.0

        # --- average_order_value ---
        aov = parse_float(row.get("average_order_value"))
        if aov is None and cleaned["total_orders"] > 0 and cleaned["total_spend"] > 0:
            # Auto-calculate if not provided
            aov = round(cleaned["total_spend"] / cleaned["total_orders"], 2)
            row_warnings.append("average_order_value was calculated from total_spend/total_orders")
        cleaned["average_order_value"] = aov or 0.0

        # --- last_purchase_date ---
        last_purchase_date = parse_date(row.get("last_purchase_date"))
        cleaned["last_purchase_date"] = last_purchase_date

        # --- website_visits ---
        cleaned["website_visits"] = parse_int(row.get("website_visits")) or 0

        # --- complaints ---
        cleaned["complaints"] = parse_int(row.get("complaints")) or 0

        # --- subscription_status ---
        status = str(row.get("subscription_status", "")).strip()
        if status and status not in ["nan", "None", ""]:
            # Match to valid status (case-insensitive)
            matched = next(
                (v for v in VALID_SUBSCRIPTION_STATUSES
                 if v.lower() == status.lower()), None
            )
            if matched:
                cleaned["subscription_status"] = matched
            else:
                row_warnings.append(
                    f"subscription_status '{status}' not recognized — set to 'Active'"
                )
                cleaned["subscription_status"] = "Active"
        else:
            cleaned["subscription_status"] = "Active"

        # Collect row-level warnings
        if row_warnings:
            warnings.append(f"Row {row_num} ({cleaned.get('name', '?')}): {'; '.join(row_warnings)}")

        valid_rows.append(cleaned)

    return {
        "valid_rows": valid_rows,
        "skipped_rows": skipped_rows,
        "warnings": warnings,
        "stats": {
            "total_rows_in_csv":   len(df),
            "valid_rows":          len(valid_rows),
            "skipped_rows":        len(skipped_rows),
            "warnings":            len(warnings),
        }
    }


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def parse_int(value):
    """Safely convert a value to int. Returns None if invalid."""
    try:
        if pd.isna(value):
            return None
        return int(float(str(value).strip()))
    except (ValueError, TypeError):
        return None


def parse_float(value):
    """Safely convert a value to float. Returns None if invalid."""
    try:
        if pd.isna(value):
            return None
        return float(str(value).strip().replace(",", ""))
    except (ValueError, TypeError):
        return None


def parse_date(value):
    """
    Safely parse a date string. Tries multiple common formats.
    Returns a date object or None.
    """
    if not value or (isinstance(value, float) and pd.isna(value)):
        return None

    date_str = str(value).strip()
    if not date_str or date_str.lower() in ["nan", "none", "nat", ""]:
        return None

    # Try these formats in order
    formats = [
        "%Y-%m-%d",    # 2024-12-15
        "%d/%m/%Y",    # 15/12/2024
        "%m/%d/%Y",    # 12/15/2024
        "%d-%m-%Y",    # 15-12-2024
        "%Y/%m/%d",    # 2024/12/15
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    return None   # Could not parse — return None
