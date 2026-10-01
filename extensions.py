# ============================================================
# extensions.py — Shared Flask Extensions
# ============================================================
# WHY THIS FILE EXISTS:
#   We had a circular import problem:
#     app.py imports Customer (from models/customer.py)
#     models/customer.py imports db (from app.py)
#     → Python gets confused: "Which one do I load first?"
#
# THE FIX:
#   Put db in a separate file (extensions.py).
#   Both app.py and models/ import db from HERE instead.
#   Now there's no circle — everyone points to one place.
# ============================================================

from flask_sqlalchemy import SQLAlchemy

# Create the db object here — it starts unattached to any app.
# We attach it to the Flask app inside app.py using db.init_app(app)
db = SQLAlchemy()
