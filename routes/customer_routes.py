# ============================================================
# routes/customer_routes.py — Customer API Endpoints
# ============================================================
# This file contains all REST API routes for customers.
#
# WHAT IS A BLUEPRINT?
#   A Blueprint is Flask's way of grouping related routes.
#   Instead of putting ALL routes in app.py (messy!), we
#   group customer routes here, dashboard routes elsewhere, etc.
#   Then we "register" this blueprint in app.py.
#
# API ENDPOINTS IN THIS FILE:
#   GET    /api/customers              → Get all customers
#   GET    /api/customers/<id>         → Get one customer
#   POST   /api/customers              → Add new customer
#   PUT    /api/customers/<id>         → Update customer
#   DELETE /api/customers/<id>         → Delete customer
# ============================================================

from flask import Blueprint, jsonify, request
from extensions import db
from models.customer import Customer
from models.purchase import Purchase
from datetime import datetime

# ============================================================
# Create Blueprint
# ============================================================
# Blueprint("customer_bp", __name__) creates a group called
# "customer_bp". We'll register this in app.py later.
customer_bp = Blueprint("customer_bp", __name__)


# ============================================================
# ROUTE 1: GET /api/customers
# ============================================================
# PURPOSE   : Returns a list of ALL customers
# METHOD    : GET (just fetching data, not changing anything)
# URL       : http://localhost:5000/api/customers
# PARAMS    : Optional query params:
#               ?page=1&per_page=10   → pagination
#               ?location=Mumbai      → filter by city
#               ?status=Active        → filter by subscription
# ============================================================

@customer_bp.route("/api/customers", methods=["GET"])
def get_all_customers():
    """Get all customers with optional filtering and pagination."""
    try:
        # --- Read optional query parameters from the URL ---
        # Example: /api/customers?location=Mumbai&status=Active
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        location = request.args.get("location", None)
        status = request.args.get("status", None)

        # --- Build the database query ---
        # Customer.query starts a SELECT query on the customers table
        query = Customer.query

        # Apply filters if provided
        if location:
            query = query.filter(Customer.location.ilike(f"%{location}%"))
            # ilike = case-insensitive LIKE search
            # "Mumbai" and "mumbai" both match

        if status:
            query = query.filter(Customer.subscription_status == status)

        # --- Paginate the results ---
        # Instead of returning ALL 10,000 customers at once (slow!),
        # we return them in pages of 20 (or whatever per_page says)
        paginated = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        # Convert each Customer object to a dictionary
        customers_list = [c.to_dict() for c in paginated.items]

        return jsonify({
            "success": True,
            "customers": customers_list,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_customers": paginated.total,
                "total_pages": paginated.pages,
                "has_next": paginated.has_next,
                "has_prev": paginated.has_prev,
            }
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Failed to fetch customers",
            "message": str(e)
        }), 500


# ============================================================
# ROUTE 2: GET /api/customers/<customer_id>
# ============================================================
# PURPOSE   : Returns details of ONE specific customer
# METHOD    : GET
# URL       : http://localhost:5000/api/customers/C1001
# URL PARAM : customer_id — the ID of the customer you want
# ============================================================

@customer_bp.route("/api/customers/<string:customer_id>", methods=["GET"])
def get_customer(customer_id):
    """Get a single customer by their customer_id."""
    try:
        # db.session.get() fetches a record by its primary key
        # Returns None if not found (instead of crashing)
        customer = db.session.get(Customer, customer_id)

        if not customer:
            # 404 = "Not Found"
            return jsonify({
                "success": False,
                "error": f"Customer '{customer_id}' not found"
            }), 404

        # Also fetch their purchase history
        purchases = Purchase.query.filter_by(customer_id=customer_id).all()
        purchase_list = [p.to_dict() for p in purchases]

        return jsonify({
            "success": True,
            "customer": customer.to_dict(),
            "purchase_history": purchase_list,
            "total_purchases_found": len(purchase_list)
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Failed to fetch customer",
            "message": str(e)
        }), 500


# ============================================================
# ROUTE 3: POST /api/customers
# ============================================================
# PURPOSE   : Add a NEW customer to the database
# METHOD    : POST (sending data to create something new)
# URL       : http://localhost:5000/api/customers
# BODY      : JSON object with customer details
#
# EXAMPLE REQUEST BODY:
# {
#   "customer_id": "C1021",
#   "name": "Riya Shah",
#   "age": 25,
#   "gender": "Female",
#   "location": "Mumbai",
#   "email": "riya.shah@email.com",
#   "subscription_status": "Active"
# }
# ============================================================

@customer_bp.route("/api/customers", methods=["POST"])
def add_customer():
    """Add a new customer to the database."""
    try:
        # request.get_json() reads the JSON body sent by the client
        data = request.get_json()

        # --- Validate required fields ---
        # We check that the most important fields are present
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided. Please send a JSON body."
            }), 400
            # 400 = "Bad Request" — client sent wrong/missing data

        required_fields = ["customer_id", "name"]
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    "success": False,
                    "error": f"'{field}' is required and cannot be empty."
                }), 400

        # --- Check if customer_id already exists ---
        existing = db.session.get(Customer, data["customer_id"])
        if existing:
            return jsonify({
                "success": False,
                "error": f"Customer ID '{data['customer_id']}' already exists."
            }), 409
            # 409 = "Conflict" — resource already exists

        # --- Check if email already exists ---
        if data.get("email"):
            email_exists = Customer.query.filter_by(email=data["email"]).first()
            if email_exists:
                return jsonify({
                    "success": False,
                    "error": f"Email '{data['email']}' is already registered."
                }), 409

        # --- Parse last_purchase_date if provided ---
        last_purchase_date = None
        if data.get("last_purchase_date"):
            try:
                last_purchase_date = datetime.strptime(
                    data["last_purchase_date"], "%Y-%m-%d"
                ).date()
            except ValueError:
                return jsonify({
                    "success": False,
                    "error": "Invalid date format. Use YYYY-MM-DD (e.g. 2024-12-15)"
                }), 400

        # --- Create new Customer object ---
        new_customer = Customer(
            customer_id=data["customer_id"],
            name=data["name"],
            age=data.get("age"),                          # .get() returns None if not provided
            gender=data.get("gender"),
            location=data.get("location"),
            email=data.get("email"),
            total_orders=data.get("total_orders", 0),
            total_spend=data.get("total_spend", 0.0),
            average_order_value=data.get("average_order_value", 0.0),
            last_purchase_date=last_purchase_date,
            website_visits=data.get("website_visits", 0),
            complaints=data.get("complaints", 0),
            subscription_status=data.get("subscription_status", "Active"),
        )

        # Save to database
        db.session.add(new_customer)
        db.session.commit()  # commit() = actually save to MySQL

        return jsonify({
            "success": True,
            "message": f"Customer '{data['name']}' added successfully!",
            "customer": new_customer.to_dict()
        }), 201
        # 201 = "Created" — new resource was successfully created

    except Exception as e:
        db.session.rollback()  # If anything failed, undo any partial changes
        return jsonify({
            "success": False,
            "error": "Failed to add customer",
            "message": str(e)
        }), 500


# ============================================================
# ROUTE 4: PUT /api/customers/<customer_id>
# ============================================================
# PURPOSE   : Update an existing customer's information
# METHOD    : PUT (updating an existing resource)
# URL       : http://localhost:5000/api/customers/C1001
#
# EXAMPLE REQUEST BODY:
# {
#   "total_spend": 90000,
#   "subscription_status": "Premium"
# }
# (You only need to send the fields you want to change)
# ============================================================

@customer_bp.route("/api/customers/<string:customer_id>", methods=["PUT"])
def update_customer(customer_id):
    """Update an existing customer's information."""
    try:
        customer = db.session.get(Customer, customer_id)

        if not customer:
            return jsonify({
                "success": False,
                "error": f"Customer '{customer_id}' not found"
            }), 404

        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided to update."
            }), 400

        # --- Update only the fields that were sent ---
        # We use getattr/setattr so we don't have to write
        # an if-statement for every single field
        updatable_fields = [
            "name", "age", "gender", "location", "email",
            "total_orders", "total_spend", "average_order_value",
            "website_visits", "complaints", "subscription_status"
        ]

        for field in updatable_fields:
            if field in data:
                setattr(customer, field, data[field])
                # setattr(obj, 'name', value) is same as obj.name = value

        # Handle date separately (needs parsing)
        if "last_purchase_date" in data:
            if data["last_purchase_date"]:
                try:
                    customer.last_purchase_date = datetime.strptime(
                        data["last_purchase_date"], "%Y-%m-%d"
                    ).date()
                except ValueError:
                    return jsonify({
                        "success": False,
                        "error": "Invalid date format. Use YYYY-MM-DD"
                    }), 400
            else:
                customer.last_purchase_date = None

        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Customer '{customer_id}' updated successfully!",
            "customer": customer.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": "Failed to update customer",
            "message": str(e)
        }), 500


# ============================================================
# ROUTE 5: DELETE /api/customers/<customer_id>
# ============================================================
# PURPOSE   : Delete a customer and all their purchases
# METHOD    : DELETE
# URL       : http://localhost:5000/api/customers/C1001
#
# NOTE: Because we set cascade="all, delete-orphan" in the
# Customer model, deleting a customer automatically deletes
# all their purchases too. No orphan records left behind!
# ============================================================

@customer_bp.route("/api/customers/<string:customer_id>", methods=["DELETE"])
def delete_customer(customer_id):
    """Delete a customer and all their associated purchases."""
    try:
        customer = db.session.get(Customer, customer_id)

        if not customer:
            return jsonify({
                "success": False,
                "error": f"Customer '{customer_id}' not found"
            }), 404

        name = customer.name  # Save name before deleting
        db.session.delete(customer)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Customer '{name}' (ID: {customer_id}) deleted successfully.",
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": "Failed to delete customer",
            "message": str(e)
        }), 500
