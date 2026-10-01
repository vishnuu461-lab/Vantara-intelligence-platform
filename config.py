# ============================================================
# config.py — Vantara Configuration
# ============================================================
# This file reads settings from the .env file and makes them
# available to the rest of the application.
#
# WHY SEPARATE FILE?
# Keeping config in its own file means app.py stays clean.
# If you ever need to change a setting, you know exactly
# where to look.
# ============================================================

import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

# --- Load the .env file ---
# This reads all KEY=VALUE pairs from .env into the environment.
# After this line, os.environ["DB_PASSWORD"] etc. will work.
load_dotenv()


class Config:
    """
    Central configuration class for Vantara.
    All settings are read from environment variables (.env file).
    """

    # --- Flask Settings ---
    # SECRET_KEY is used by Flask for security (sessions, etc.)
    SECRET_KEY = os.environ.get("SECRET_KEY", "vantara-default-secret-key")

    # DEBUG mode shows detailed error messages during development
    DEBUG = os.environ.get("FLASK_DEBUG", "True") == "True"

    # --- Database Settings ---
    # We read individual pieces from .env and combine them
    # into a single "connection string" that SQLAlchemy needs.
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = os.environ.get("DB_PORT", "3306")
    DB_NAME = os.environ.get("DB_NAME", "vantara_db")
    DB_USER = os.environ.get("DB_USER", "root")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "")

    # --- SQLAlchemy Database URI ---
    # Format: mysql+pymysql://username:password@host:port/database_name
    # quote_plus() is used to safely encode special characters in the password
    # For example, if your password is "Hello@123", the @ would confuse the URL
    # parser. quote_plus converts it to "Hello%40123" so the URL is read correctly.
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    # --- SQLAlchemy Settings ---
    # This disables a feature we don't need (saves memory)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Application Port ---
    APP_PORT = int(os.environ.get("APP_PORT", 5000))
