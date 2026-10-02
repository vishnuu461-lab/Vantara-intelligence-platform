# ============================================================
# app.py — Vantara Main Application Entry Point
# ============================================================
from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from extensions import db   # db now lives in extensions.py
import os


# ============================================================
# Step 1: Create the Flask Application
# ============================================================
app = Flask(__name__)

# ============================================================
# Step 2: Load Configuration
# ============================================================
app.config.from_object(Config)

# ============================================================
# Step 3: Initialize Extensions
# ============================================================
# db.init_app(app) attaches the db object to our Flask app.
# This is the correct pattern when db is in a separate file.
db.init_app(app)

# CORS — allow local dev + all Vercel deployments
# Using regex to match any *.vercel.app subdomain automatically
# so no manual FRONTEND_URL env var update is needed on Render.
CORS(app,
     origins=[
         r"http://localhost:\d+",                          # any local port
         r"https://vantara-intelligence-platform\.vercel\.app",  # production
         r"https://vantara-.*\.vercel\.app",               # preview deployments
         os.environ.get("FRONTEND_URL", ""),               # custom domain (optional)
     ],
     supports_credentials=True)


# ============================================================
# Step 4: Basic Routes
# ============================================================

@app.route("/")
def home():
    return jsonify({
        "message": "Welcome to Vantara – Customer Intelligence Platform API",
        "status": "running",
        "version": "1.0.0",
        "available_endpoints": [
            "GET  /api/health",
            "GET  /api/db-test",
            "GET  /api/customers",
            "POST /api/customers",
            "GET  /api/dashboard",
            "GET  /api/segments",
        ]
    })


@app.route("/api/health")
def health_check():
    """Simple health check — confirms server is alive."""
    return jsonify({
        "status": "healthy",
        "message": "Vantara backend is running successfully"
    }), 200


@app.route("/api/seed-db")
def seed_db():
    """
    One-time database seeding endpoint.
    Safe to call multiple times — skips if data already exists.
    Trigger via: GET /api/seed-db
    """
    try:
        from models.customer import Customer
        from models.purchase import Purchase
        from data.seed_data import SAMPLE_CUSTOMERS, SAMPLE_PURCHASES
        from datetime import date

        existing = Customer.query.count()
        if existing > 0:
            return jsonify({
                "status": "skipped",
                "message": f"Database already has {existing} customers. No action taken.",
                "customers": existing
            }), 200

        # Seed customers
        for data in SAMPLE_CUSTOMERS:
            db.session.add(Customer(**data))
        db.session.commit()

        # Seed purchases
        for data in SAMPLE_PURCHASES:
            db.session.add(Purchase(**data))
        db.session.commit()

        total_customers = Customer.query.count()
        total_purchases = Purchase.query.count()

        return jsonify({
            "status": "success",
            "message": "Database seeded successfully!",
            "customers_added": total_customers,
            "purchases_added": total_purchases
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500



@app.route("/api/db-test")
def db_test():
    """Tests the MySQL database connection."""
    try:
        from sqlalchemy import text
        db.session.execute(text("SELECT 1"))
        return jsonify({
            "status": "success",
            "message": "Database connection successful!",
            "database": Config.DB_NAME,
            "host": Config.DB_HOST
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "Database connection failed!",
            "error": str(e),
            "hint": "Check your .env file — is DB_PASSWORD correct?"
        }), 500


# ============================================================
# Step 5: Error Handlers
# ============================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Not Found",
        "message": "The endpoint you requested does not exist.",
        "status_code": 404
    }), 404


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        "error": "Method Not Allowed",
        "message": "This HTTP method is not allowed for this endpoint.",
        "status_code": 405
    }), 405


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Internal Server Error",
        "message": "Something went wrong on the server. Please try again.",
        "status_code": 500
    }), 500


# ============================================================
# Step 6: Import Models & Create Database Tables
# ============================================================
# Models are imported AFTER db.init_app(app) to avoid circular imports.
# db.create_all() creates tables in MySQL if they don't exist yet.
from models.customer import Customer   # noqa: F401
from models.purchase import Purchase   # noqa: F401

# --- Register Blueprints (Route Groups) ---
# A Blueprint is a group of routes. We register them here
# so Flask knows about all our API endpoints.
from routes.customer_routes import customer_bp
from routes.dashboard_routes import dashboard_bp
from routes.prediction_routes import prediction_bp
from routes.upload_routes import upload_bp
app.register_blueprint(customer_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(prediction_bp)
app.register_blueprint(upload_bp)

with app.app_context():
    db.create_all()
    print("  Tables: 'customers' and 'purchases' are ready.")


# ============================================================
# Step 7: Run the Application
# ============================================================
if __name__ == "__main__":
    print("=" * 55)
    print("  Vantara – Customer Intelligence Platform")
    print("  Backend Server Starting...")
    print("=" * 55)
    print(f"  Server:      http://localhost:{Config.APP_PORT}")
    print(f"  Health:      http://localhost:{Config.APP_PORT}/api/health")
    print(f"  DB Test:     http://localhost:{Config.APP_PORT}/api/db-test")
    print(f"  Debug mode:  {Config.DEBUG}")
    print("=" * 55)
    print("  Press CTRL+C to stop the server")
    print("=" * 55)

    app.run(
        host="0.0.0.0",
        port=Config.APP_PORT,
        debug=Config.DEBUG
    )
