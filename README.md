# Vantara – Customer Intelligence Platform

> A modular, ML-powered customer analytics backend built with Python, Flask, and MySQL.

---

## Project Overview

Vantara is a **Customer Intelligence Platform** backend that helps businesses understand their customers better using data analytics and machine learning.

### What It Does

| Feature | Description |
|---|---|
| Customer Management | Full CRUD API for customer records |
| Dashboard Analytics | Real-time business summary metrics |
| Behavior Analysis | Recency, Frequency, Spending level per customer |
| Churn Prediction | ML model (Random Forest) predicts churn probability |
| CLV Prediction | ML model predicts Customer Lifetime Value |
| Segmentation | Groups customers into High Value / Regular / New / Inactive / High Risk |
| AI Insights | Unified report combining all predictions with health score |
| CSV Upload | Bulk import customers with auto data cleaning |

---

## Technology Stack

| Layer | Technology |
|---|---|
| Language | Python 3.x |
| Web Framework | Flask |
| Database | MySQL (via SQLAlchemy ORM) |
| ML Library | Scikit-learn (Random Forest) |
| Data Processing | Pandas, NumPy |
| Model Storage | Joblib (.pkl files) |
| DB Driver | PyMySQL |

---

## Project Structure

```
PROJ-VANT-260704/
│
├── app.py                        # Flask app entry point — run this to start the server
├── config.py                     # Config: reads .env → builds DB connection string
├── extensions.py                 # Shared db object (avoids circular imports)
├── requirements.txt              # Python dependencies
├── .env                          # Secret config (DB credentials) — NOT committed to git
├── .gitignore                    # Git ignore rules
├── test_all_apis.py              # Full API test suite (64 tests, 100% pass)
│
├── models/                       # SQLAlchemy database models
│   ├── __init__.py
│   ├── customer.py               # Customer table schema + to_dict()
│   └── purchase.py               # Purchase table schema + to_dict()
│
├── routes/                       # Flask API route handlers (Blueprints)
│   ├── customer_routes.py        # GET/POST/PUT/DELETE /api/customers
│   ├── dashboard_routes.py       # GET /api/dashboard
│   ├── prediction_routes.py      # Behavior, Churn, CLV, Segment, Insights
│   └── upload_routes.py          # POST /api/upload
│
├── services/                     # Business logic (separate from routes)
│   ├── analytics_service.py      # Behavior analysis: recency, frequency, spend
│   ├── churn_service.py          # Loads churn ML model, makes predictions
│   ├── clv_service.py            # Loads CLV ML model, makes predictions
│   ├── segmentation_service.py   # Rule-based customer segmentation
│   └── insights_service.py       # Unified AI report: all predictions combined
│
├── ml/                           # Machine Learning
│   ├── train_churn_model.py      # Train & save churn model (run once)
│   ├── train_clv_model.py        # Train & save CLV model (run once)
│   └── models/                   # Saved trained models (.pkl files)
│       ├── churn_model.pkl
│       ├── churn_scaler.pkl
│       ├── clv_model.pkl
│       └── clv_scaler.pkl
│
├── data/                         # Data scripts and sample files
│   ├── seed_data.py              # Seeds database with 20 customers + 39 purchases
│   └── sample_customers.csv      # Sample CSV for testing the upload API
│
└── utils/                        # Utility helpers
    └── data_cleaning.py          # CSV validation, type checking, normalization
```

---

## Setup Instructions

### Prerequisites

- Python 3.9 or higher installed
- MySQL Server running locally
- Git (optional)

### Step 1 — Clone / Open the Project

```bash
cd C:\Users\Vishnu\OneDrive\Desktop\PROJ-VANT-260704
```

### Step 2 — Virtual Environment

The virtual environment is located at `C:\Vantara-venv` (outside OneDrive to avoid sync issues).

To activate it:
```bash
C:\Vantara-venv\Scripts\activate
```

Or run Python directly:
```bash
C:\Vantara-venv\Scripts\python.exe <script.py>
```

### Step 3 — Install Dependencies

```bash
C:\Vantara-venv\Scripts\pip.exe install -r requirements.txt
```

### Step 4 — Configure Environment Variables

Create a `.env` file in the project root (already created):

```
DB_HOST=localhost
DB_PORT=3306
DB_NAME=vantara_db
DB_USER=root
DB_PASSWORD=your_mysql_password
FLASK_ENV=development
SECRET_KEY=vantara-secret-key-2024
```

> **Note:** Never commit `.env` to git. It is listed in `.gitignore`.

### Step 5 — Create MySQL Database

Open MySQL Workbench or MySQL CLI and run:

```sql
CREATE DATABASE IF NOT EXISTS vantara_db;
```

### Step 6 — Train the ML Models (run once)

```bash
C:\Vantara-venv\Scripts\python.exe ml/train_churn_model.py
C:\Vantara-venv\Scripts\python.exe ml/train_clv_model.py
```

Expected output for churn model: **~91% accuracy**

### Step 7 — Seed the Database (run once)

```bash
C:\Vantara-venv\Scripts\python.exe data/seed_data.py
```

Seeds: 20 customers + 39 purchases

### Step 8 — Start the Server

```bash
C:\Vantara-venv\Scripts\python.exe app.py
```

Server starts at: `http://localhost:5000`

### Step 9 — Run Tests

```bash
C:\Vantara-venv\Scripts\python.exe test_all_apis.py
```

Expected: **64/64 tests pass (100%)**

---

## Database Schema

### `customers` Table

| Column | Type | Description |
|---|---|---|
| customer_id | VARCHAR(20) | Primary key (e.g., C1001) |
| name | VARCHAR(100) | Full name |
| age | INT | Age |
| gender | VARCHAR(10) | Male / Female / Other |
| location | VARCHAR(100) | City |
| email | VARCHAR(150) | Unique email address |
| total_orders | INT | Total number of orders placed |
| total_spend | FLOAT | Cumulative spend in Rs. |
| average_order_value | FLOAT | Average spend per order |
| last_purchase_date | DATE | Date of most recent purchase |
| website_visits | INT | Total site visits |
| complaints | INT | Number of complaints filed |
| subscription_status | VARCHAR(20) | Active / Inactive / Premium / Cancelled |
| created_at | DATETIME | Record creation timestamp |

### `purchases` Table

| Column | Type | Description |
|---|---|---|
| purchase_id | INT | Auto-increment primary key |
| customer_id | VARCHAR(20) | Foreign key → customers.customer_id |
| product_category | VARCHAR(50) | Electronics / Clothing / Books / etc. |
| amount | FLOAT | Purchase amount in Rs. |
| purchase_date | DATE | Date of purchase |

---

## API Reference

**Base URL:** `http://localhost:5000`

---

### Health & Status

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Server health check |
| GET | `/api/db-test` | Database connection test |

---

### Customer Management

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/customers` | Get all customers (with pagination & filters) |
| GET | `/api/customers/<id>` | Get one customer + purchase history |
| POST | `/api/customers` | Add a new customer |
| PUT | `/api/customers/<id>` | Update a customer |
| DELETE | `/api/customers/<id>` | Delete a customer |

**Query Parameters for GET /api/customers:**

| Parameter | Example | Description |
|---|---|---|
| page | `?page=1` | Page number (default: 1) |
| per_page | `?per_page=10` | Results per page (default: 20) |
| location | `?location=Mumbai` | Filter by city |
| status | `?status=Premium` | Filter by subscription status |

**POST /api/customers — Example Request Body:**
```json
{
  "customer_id": "C1099",
  "name": "Riya Shah",
  "age": 25,
  "gender": "Female",
  "location": "Mumbai",
  "email": "riya.shah@email.com",
  "total_orders": 3,
  "total_spend": 7500,
  "subscription_status": "Active"
}
```

---

### Dashboard

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/dashboard` | Full business summary — customer counts, revenue, risk indicators, top locations |

---

### Analytics & Predictions

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/customers/<id>/behavior` | Behavior analysis: recency, frequency, spending, favorite category |
| GET | `/api/customers/<id>/churn` | Churn prediction with ML probability and risk level |
| GET | `/api/customers/<id>/clv` | Customer Lifetime Value prediction with tier |
| GET | `/api/customers/<id>/segment` | Segment assignment for one customer |
| GET | `/api/customers/<id>/insights` | **Full AI report** combining all predictions + health score + recommendations |
| GET | `/api/segments` | Segmentation of ALL customers with counts and percentages |
| GET | `/api/analysis/summary` | Aggregate stats across all customers |

---

### CSV Upload

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/upload` | Upload a CSV file to bulk import customers |

**How to use in Postman:**
- Method: `POST`
- URL: `http://localhost:5000/api/upload`
- Body → `form-data` → Key: `file` (type: File) → Select your CSV

**Expected CSV columns:**

| Column | Required | Notes |
|---|---|---|
| customer_id | YES | Unique ID |
| name | YES | Customer name |
| age | No | Integer |
| gender | No | Male / Female / M / F |
| location | No | City name |
| email | No | Must contain @ |
| total_orders | No | Integer, defaults to 0 |
| total_spend | No | Float, defaults to 0.0 |
| average_order_value | No | Auto-calculated if missing |
| last_purchase_date | No | Format: YYYY-MM-DD |
| website_visits | No | Integer |
| complaints | No | Integer |
| subscription_status | No | Active / Inactive / Premium / Cancelled |

---

## Machine Learning Models

### Churn Prediction Model

- **Algorithm:** Random Forest Classifier
- **Accuracy:** ~91%
- **Features:** total_orders, total_spend, days_since_last_purchase, average_order_value, website_visits, complaints, subscription_active
- **Output:** Churn probability (0.0 to 1.0) + Risk Level (Low / Medium / High)
- **Training data:** 1000 synthetic samples with realistic patterns
- **Model file:** `ml/models/churn_model.pkl`

### CLV Prediction Model

- **Algorithm:** Random Forest Regressor
- **Top feature:** avg_order_value (44% importance)
- **Output:** Predicted lifetime value in Rs. + Tier (Entry / Bronze / Silver / Gold / Platinum)
- **Model file:** `ml/models/clv_model.pkl`

---

## Sample API Responses

### GET /api/customers/C1001/insights

```json
{
  "success": true,
  "intelligence_report": {
    "name": "Ananya Sharma",
    "health_score": 80,
    "health_label": "Excellent",
    "ai_summary": "Ananya is one of Vantara's most valuable customers...",
    "predictions": {
      "churn": { "risk_level": "Low", "percentage": "14.7%" },
      "clv":   { "formatted": "Rs.23,966", "tier": "Silver" },
      "segment": { "name": "High Value" }
    },
    "recommendations": [
      {
        "priority": "OPPORTUNITY",
        "action": "Targeted Electronics promotion",
        "detail": "Send a curated Electronics product recommendation email."
      }
    ]
  }
}
```

---

## Key Design Decisions

| Decision | Why |
|---|---|
| Blueprint architecture | Keeps routes modular — customer, dashboard, prediction, upload are separate files |
| `extensions.py` for db | Avoids circular import between `app.py` and `models/` |
| `os.getcwd()` for model paths | Flask debug reloader changes `__file__` path; `getcwd()` is more reliable |
| `quote_plus` in DB URL | Safely encodes special characters in MySQL password |
| Rule-based segmentation | More explainable and adjustable than pure clustering for a first version |
| Fallback for ML models | If models not trained yet, rule-based fallback is used — app never crashes |

---

## Running the Test Suite

```bash
# Make sure Flask is running first, then:
C:\Vantara-venv\Scripts\python.exe test_all_apis.py
```

**Result: 64/64 tests — 100% pass rate**

Tests cover: Health, DB, Customer CRUD, Dashboard, Behavior, Churn (ML), CLV (ML), Segmentation, AI Insights, Analysis Summary.

---

## Important Notes

- **MySQL must be running** before starting Flask
- **Train ML models once** before first use (`ml/train_churn_model.py`, `ml/train_clv_model.py`)
- **Seed the database once** (`data/seed_data.py`)
- **Never commit `.env`** to version control
- Always run Flask from the **project root directory** so `os.getcwd()` resolves model paths correctly

---

## Author

**Vishnu**
Vantara – Customer Intelligence Platform
College Backend Project | Python · Flask · MySQL · Scikit-learn
#   V a n t a r a - i n t e l l i g e n c e - p l a t f o r m  
 