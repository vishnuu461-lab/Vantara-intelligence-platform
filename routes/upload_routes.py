# ============================================================
# routes/upload_routes.py — CSV Upload API
# ============================================================
# POST /api/upload  → Upload a CSV file of customers
#
# HOW IT WORKS:
#   1. Receive the uploaded CSV file
#   2. Read it using pandas
#   3. Validate and clean using data_cleaning.py
#   4. Insert valid rows into MySQL
#   5. Skip duplicates (customers that already exist)
#   6. Return a detailed report
# ============================================================

import os
import pandas as pd
from flask import Blueprint, jsonify, request
from extensions import db
from models.customer import Customer
from utils.data_cleaning import validate_and_clean

upload_bp = Blueprint("upload_bp", __name__)

# Max file size: 5 MB
MAX_FILE_SIZE_MB = 5
ALLOWED_EXTENSIONS = {"csv"}


def allowed_file(filename):
    """Check if the uploaded file has a .csv extension."""
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


# ============================================================
# ROUTE: POST /api/upload
# ============================================================
# PURPOSE : Upload a CSV file of customer data
# METHOD  : POST (multipart/form-data)
# KEY     : File must be sent with the key name "file"
#
# EXAMPLE using Postman:
#   Method : POST
#   URL    : http://localhost:5000/api/upload
#   Body   : form-data → Key: "file", Value: [select CSV file]
# ============================================================

@upload_bp.route("/api/upload", methods=["POST"])
def upload_customers():
    """
    Upload a CSV file and import customer data into MySQL.

    Expected CSV columns:
        customer_id (required), name (required),
        age, gender, location, email,
        total_orders, total_spend, average_order_value,
        last_purchase_date, website_visits, complaints,
        subscription_status

    Returns a detailed report of what was imported and skipped.
    """
    # --------------------------------------------------------
    # STEP 1: Check a file was actually sent
    # --------------------------------------------------------
    if "file" not in request.files:
        return jsonify({
            "success": False,
            "error": "No file provided.",
            "hint": "Send the CSV file with the key 'file' in form-data."
        }), 400

    file = request.files["file"]

    # Check the file has a name
    if file.filename == "":
        return jsonify({
            "success": False,
            "error": "No file selected."
        }), 400

    # Check it's a CSV file
    if not allowed_file(file.filename):
        return jsonify({
            "success": False,
            "error": f"Invalid file type '{file.filename}'. Only .csv files are allowed."
        }), 400

    # --------------------------------------------------------
    # STEP 2: Read the CSV into a pandas DataFrame
    # --------------------------------------------------------
    try:
        df = pd.read_csv(file)
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Could not read CSV file.",
            "message": str(e),
            "hint": "Make sure the file is a valid CSV with comma-separated values."
        }), 400

    # Check the file isn't empty
    if df.empty:
        return jsonify({
            "success": False,
            "error": "The uploaded CSV file is empty."
        }), 400

    # --------------------------------------------------------
    # STEP 3: Validate and clean the data
    # --------------------------------------------------------
    try:
        result = validate_and_clean(df)
    except ValueError as e:
        # validate_and_clean raises ValueError for missing required columns
        return jsonify({
            "success": False,
            "error": "CSV validation failed.",
            "message": str(e)
        }), 400

    valid_rows   = result["valid_rows"]
    skipped_rows = result["skipped_rows"]
    warnings     = result["warnings"]

    if not valid_rows:
        return jsonify({
            "success": False,
            "error": "No valid rows found in the CSV.",
            "skipped_rows": skipped_rows,
            "hint": "Check that customer_id and name columns are present and not empty."
        }), 400

    # --------------------------------------------------------
    # STEP 4: Insert valid rows into MySQL
    # --------------------------------------------------------
    inserted     = []
    duplicates   = []
    insert_errors = []

    for row_data in valid_rows:
        customer_id = row_data["customer_id"]

        # Check if this customer already exists
        existing = db.session.get(Customer, customer_id)
        if existing:
            duplicates.append({
                "customer_id": customer_id,
                "name": row_data["name"],
                "reason": "customer_id already exists in database"
            })
            continue

        # Try to insert the new customer
        try:
            new_customer = Customer(**row_data)
            db.session.add(new_customer)
            db.session.flush()   # flush = send to DB but don't commit yet
            inserted.append({
                "customer_id": customer_id,
                "name": row_data["name"]
            })
        except Exception as e:
            db.session.rollback()
            insert_errors.append({
                "customer_id": customer_id,
                "name": row_data.get("name", "?"),
                "error": str(e)
            })

    # Commit all successful inserts at once
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": "Database commit failed.",
            "message": str(e)
        }), 500

    # --------------------------------------------------------
    # STEP 5: Return the full import report
    # --------------------------------------------------------
    total_in_csv     = result["stats"]["total_rows_in_csv"]
    total_valid      = len(valid_rows)
    total_inserted   = len(inserted)
    total_duplicates = len(duplicates)
    total_skipped    = len(skipped_rows)
    total_errors     = len(insert_errors)

    success = total_inserted > 0

    return jsonify({
        "success": success,
        "message": (
            f"Import complete. {total_inserted} customers added, "
            f"{total_duplicates} duplicates skipped, "
            f"{total_skipped} invalid rows skipped."
        ),
        "report": {
            "total_rows_in_csv":  total_in_csv,
            "valid_rows":         total_valid,
            "inserted":           total_inserted,
            "duplicates_skipped": total_duplicates,
            "invalid_skipped":    total_skipped,
            "errors":             total_errors,
        },
        "inserted_customers":  inserted,
        "duplicates":          duplicates,
        "skipped_rows":        skipped_rows,
        "warnings":            warnings,
        "insert_errors":       insert_errors,
    }), 200 if success else 207
    # 200 = success, 207 = "Multi-Status" (some inserted, some skipped)
