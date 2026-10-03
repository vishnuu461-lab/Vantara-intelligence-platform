# ============================================================
# config.py — Vantara Configuration
# ============================================================
# Reads settings from environment variables (.env locally,
# Render dashboard in production).
# ============================================================

import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()


class Config:
    """
    Central configuration class for Vantara.
    All settings are read from environment variables.

    Local development: values come from .env file
    Production (Render): values come from Render environment variables
    """

    # --- Flask Settings ---
    SECRET_KEY = os.environ.get("SECRET_KEY", "vantara-default-secret-key-change-in-prod")
    DEBUG = os.environ.get("FLASK_DEBUG", "False") == "True"

    # --- Database Settings ---
    # Supports two modes:
    #   1. DATABASE_URL  = full connection string (provided by Render, PlanetScale, etc.)
    #   2. Individual DB_* vars = used locally or when you set them manually
    _db_url = os.environ.get("DATABASE_URL", "")

    if _db_url:
        # Cloud databases (Render, PlanetScale, Railway, etc.) provide a full URL.
        # Some providers give postgres:// — we keep mysql+pymysql:// format.
        if _db_url.startswith("mysql://"):
            _db_url = _db_url.replace("mysql://", "mysql+pymysql://", 1)
        SQLALCHEMY_DATABASE_URI = _db_url
    else:
        # Local / manual config via individual env vars
        DB_HOST     = os.environ.get("DB_HOST", "localhost")
        DB_PORT     = os.environ.get("DB_PORT", "3306")
        DB_NAME     = os.environ.get("DB_NAME", "vantara_db")
        DB_USER     = os.environ.get("DB_USER", "root")
        DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{DB_USER}:{quote_plus(DB_PASSWORD)}"
            f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        )

    # Keep these as class attributes for use in routes (e.g. /api/db-test)
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = os.environ.get("DB_PORT", "3306")
    DB_NAME = os.environ.get("DB_NAME", "vantara_db")
    DB_USER = os.environ.get("DB_USER", "root")

    # --- SQLAlchemy Settings ---
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Pool settings for production stability
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 280,       # Reconnect before MySQL's 5-min timeout
        "pool_pre_ping": True,     # Test connection before using it
        "pool_size": 10,           # Allow more simultaneous DB connections
        "max_overflow": 5,         # Extra connections under peak load
    }

    # --- Application Port ---
    APP_PORT = int(os.environ.get("APP_PORT", 5000))
