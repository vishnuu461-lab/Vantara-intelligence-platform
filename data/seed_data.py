# ============================================================
# data/seed_data.py — Add Sample Data to the Database
# ============================================================
# All dates are RELATIVE to today using timedelta so the data
# always looks fresh and realistic no matter when it's seeded.
#
# High-value Premium customers   → purchased recently (5-22 days ago)
# Regular Active customers       → purchased in last 1-4 months
# Inactive/Cancelled customers   → last purchase 380-600+ days ago
# ============================================================

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, timedelta
from app import app
from extensions import db
from models.customer import Customer
from models.purchase import Purchase

# Relative date helper — call at module load so all dates are consistent
_today = date.today()
def _ago(days):
    return _today - timedelta(days=days)


# ============================================================
# Sample Customer Data — 20 realistic Indian customers
# ============================================================

SAMPLE_CUSTOMERS = [
    {
        "customer_id": "C1001",
        "name": "Ananya Sharma",
        "age": 28,
        "gender": "Female",
        "location": "Mumbai",
        "email": "ananya.sharma@email.com",
        "total_orders": 24,
        "total_spend": 85000.0,
        "average_order_value": 3541.67,
        "last_purchase_date": _ago(15),     # Recent Premium buyer
        "website_visits": 120,
        "complaints": 0,
        "subscription_status": "Premium",
    },
    {
        "customer_id": "C1002",
        "name": "Rahul Verma",
        "age": 35,
        "gender": "Male",
        "location": "Delhi",
        "email": "rahul.verma@email.com",
        "total_orders": 5,
        "total_spend": 12000.0,
        "average_order_value": 2400.0,
        "last_purchase_date": _ago(400),    # At-risk Inactive
        "website_visits": 15,
        "complaints": 2,
        "subscription_status": "Inactive",
    },
    {
        "customer_id": "C1003",
        "name": "Priya Nair",
        "age": 22,
        "gender": "Female",
        "location": "Bangalore",
        "email": "priya.nair@email.com",
        "total_orders": 2,
        "total_spend": 3500.0,
        "average_order_value": 1750.0,
        "last_purchase_date": _ago(45),     # New active customer
        "website_visits": 8,
        "complaints": 0,
        "subscription_status": "Active",
    },
    {
        "customer_id": "C1004",
        "name": "Arjun Mehta",
        "age": 42,
        "gender": "Male",
        "location": "Hyderabad",
        "email": "arjun.mehta@email.com",
        "total_orders": 31,
        "total_spend": 145000.0,
        "average_order_value": 4677.42,
        "last_purchase_date": _ago(7),      # Very recent top spender
        "website_visits": 200,
        "complaints": 1,
        "subscription_status": "Premium",
    },
    {
        "customer_id": "C1005",
        "name": "Sneha Patil",
        "age": 30,
        "gender": "Female",
        "location": "Pune",
        "email": "sneha.patil@email.com",
        "total_orders": 12,
        "total_spend": 28000.0,
        "average_order_value": 2333.33,
        "last_purchase_date": _ago(35),     # Steady regular buyer
        "website_visits": 55,
        "complaints": 1,
        "subscription_status": "Active",
    },
    {
        "customer_id": "C1006",
        "name": "Karan Singh",
        "age": 27,
        "gender": "Male",
        "location": "Chennai",
        "email": "karan.singh@email.com",
        "total_orders": 0,
        "total_spend": 0.0,
        "average_order_value": 0.0,
        "last_purchase_date": None,         # Never purchased
        "website_visits": 3,
        "complaints": 0,
        "subscription_status": "Active",
    },
    {
        "customer_id": "C1007",
        "name": "Deepika Rao",
        "age": 38,
        "gender": "Female",
        "location": "Kolkata",
        "email": "deepika.rao@email.com",
        "total_orders": 18,
        "total_spend": 62000.0,
        "average_order_value": 3444.44,
        "last_purchase_date": _ago(22),     # Active high spender
        "website_visits": 95,
        "complaints": 0,
        "subscription_status": "Active",
    },
    {
        "customer_id": "C1008",
        "name": "Vikram Joshi",
        "age": 50,
        "gender": "Male",
        "location": "Ahmedabad",
        "email": "vikram.joshi@email.com",
        "total_orders": 3,
        "total_spend": 7500.0,
        "average_order_value": 2500.0,
        "last_purchase_date": _ago(500),    # Long inactive, many complaints
        "website_visits": 5,
        "complaints": 3,
        "subscription_status": "Inactive",
    },
    {
        "customer_id": "C1009",
        "name": "Meera Krishnan",
        "age": 25,
        "gender": "Female",
        "location": "Jaipur",
        "email": "meera.krishnan@email.com",
        "total_orders": 9,
        "total_spend": 19500.0,
        "average_order_value": 2166.67,
        "last_purchase_date": _ago(60),     # Moderately active
        "website_visits": 42,
        "complaints": 0,
        "subscription_status": "Active",
    },
    {
        "customer_id": "C1010",
        "name": "Rohit Gupta",
        "age": 33,
        "gender": "Male",
        "location": "Lucknow",
        "email": "rohit.gupta@email.com",
        "total_orders": 1,
        "total_spend": 1200.0,
        "average_order_value": 1200.0,
        "last_purchase_date": _ago(520),    # Churned, cancelled
        "website_visits": 2,
        "complaints": 1,
        "subscription_status": "Cancelled",
    },
    {
        "customer_id": "C1011",
        "name": "Aisha Khan",
        "age": 29,
        "gender": "Female",
        "location": "Mumbai",
        "email": "aisha.khan@email.com",
        "total_orders": 20,
        "total_spend": 76000.0,
        "average_order_value": 3800.0,
        "last_purchase_date": _ago(12),     # Very frequent Premium buyer
        "website_visits": 110,
        "complaints": 0,
        "subscription_status": "Premium",
    },
    {
        "customer_id": "C1012",
        "name": "Suresh Babu",
        "age": 45,
        "gender": "Male",
        "location": "Coimbatore",
        "email": "suresh.babu@email.com",
        "total_orders": 7,
        "total_spend": 15400.0,
        "average_order_value": 2200.0,
        "last_purchase_date": _ago(110),    # Fading, some complaints
        "website_visits": 28,
        "complaints": 2,
        "subscription_status": "Active",
    },
    {
        "customer_id": "C1013",
        "name": "Neha Saxena",
        "age": 31,
        "gender": "Female",
        "location": "Bhopal",
        "email": "neha.saxena@email.com",
        "total_orders": 14,
        "total_spend": 33600.0,
        "average_order_value": 2400.0,
        "last_purchase_date": _ago(28),     # Consistent active buyer
        "website_visits": 67,
        "complaints": 1,
        "subscription_status": "Active",
    },
    {
        "customer_id": "C1014",
        "name": "Amit Tiwari",
        "age": 37,
        "gender": "Male",
        "location": "Nagpur",
        "email": "amit.tiwari@email.com",
        "total_orders": 0,
        "total_spend": 0.0,
        "average_order_value": 0.0,
        "last_purchase_date": None,         # Never purchased
        "website_visits": 1,
        "complaints": 0,
        "subscription_status": "Active",
    },
    {
        "customer_id": "C1015",
        "name": "Pooja Iyer",
        "age": 26,
        "gender": "Female",
        "location": "Bangalore",
        "email": "pooja.iyer@email.com",
        "total_orders": 28,
        "total_spend": 98000.0,
        "average_order_value": 3500.0,
        "last_purchase_date": _ago(5),      # Top spender, just bought
        "website_visits": 175,
        "complaints": 0,
        "subscription_status": "Premium",
    },
    {
        "customer_id": "C1016",
        "name": "Nikhil Desai",
        "age": 40,
        "gender": "Male",
        "location": "Surat",
        "email": "nikhil.desai@email.com",
        "total_orders": 4,
        "total_spend": 8800.0,
        "average_order_value": 2200.0,
        "last_purchase_date": _ago(385),    # Long inactive
        "website_visits": 12,
        "complaints": 2,
        "subscription_status": "Inactive",
    },
    {
        "customer_id": "C1017",
        "name": "Shruti Agarwal",
        "age": 23,
        "gender": "Female",
        "location": "Indore",
        "email": "shruti.agarwal@email.com",
        "total_orders": 6,
        "total_spend": 11400.0,
        "average_order_value": 1900.0,
        "last_purchase_date": _ago(42),     # Young active customer
        "website_visits": 30,
        "complaints": 0,
        "subscription_status": "Active",
    },
    {
        "customer_id": "C1018",
        "name": "Rajesh Kumar",
        "age": 48,
        "gender": "Male",
        "location": "Patna",
        "email": "rajesh.kumar@email.com",
        "total_orders": 2,
        "total_spend": 3000.0,
        "average_order_value": 1500.0,
        "last_purchase_date": _ago(600),    # Churned long ago
        "website_visits": 4,
        "complaints": 4,
        "subscription_status": "Cancelled",
    },
    {
        "customer_id": "C1019",
        "name": "Kavita Menon",
        "age": 34,
        "gender": "Female",
        "location": "Kochi",
        "email": "kavita.menon@email.com",
        "total_orders": 16,
        "total_spend": 44000.0,
        "average_order_value": 2750.0,
        "last_purchase_date": _ago(25),     # Solid active customer
        "website_visits": 82,
        "complaints": 1,
        "subscription_status": "Active",
    },
    {
        "customer_id": "C1020",
        "name": "Siddharth Patel",
        "age": 31,
        "gender": "Male",
        "location": "Vadodara",
        "email": "siddharth.patel@email.com",
        "total_orders": 10,
        "total_spend": 22000.0,
        "average_order_value": 2200.0,
        "last_purchase_date": _ago(55),     # Regular mid-tier
        "website_visits": 45,
        "complaints": 0,
        "subscription_status": "Active",
    },
]


# ============================================================
# Sample Purchase Data — relative dates matching customers
# ============================================================

SAMPLE_PURCHASES = [
    # Ananya Sharma (C1001) — High spender, Premium
    {"customer_id": "C1001", "product_name": "iPhone 15 Pro",  "product_category": "Electronics", "amount": 134900.0, "purchase_date": _ago(15)},
    {"customer_id": "C1001", "product_name": "AirPods Pro",    "product_category": "Electronics", "amount": 24900.0,  "purchase_date": _ago(45)},
    {"customer_id": "C1001", "product_name": "Silk Saree",     "product_category": "Clothing",    "amount": 8500.0,   "purchase_date": _ago(90)},

    # Rahul Verma (C1002) — Low activity, complaints
    {"customer_id": "C1002", "product_name": "Running Shoes",  "product_category": "Sports",  "amount": 4500.0, "purchase_date": _ago(400)},
    {"customer_id": "C1002", "product_name": "Protein Powder", "product_category": "Health",  "amount": 2800.0, "purchase_date": _ago(430)},

    # Priya Nair (C1003) — New customer
    {"customer_id": "C1003", "product_name": "Python Book", "product_category": "Books", "amount": 699.0,  "purchase_date": _ago(45)},
    {"customer_id": "C1003", "product_name": "Desk Lamp",   "product_category": "Home",  "amount": 1200.0, "purchase_date": _ago(75)},

    # Arjun Mehta (C1004) — Highest spender, Premium
    {"customer_id": "C1004", "product_name": "MacBook Pro M3", "product_category": "Electronics", "amount": 199900.0, "purchase_date": _ago(7)},
    {"customer_id": "C1004", "product_name": "iPad Pro",       "product_category": "Electronics", "amount": 109900.0, "purchase_date": _ago(50)},
    {"customer_id": "C1004", "product_name": "Office Chair",   "product_category": "Furniture",   "amount": 25000.0,  "purchase_date": _ago(100)},
    {"customer_id": "C1004", "product_name": "Smart Watch",    "product_category": "Electronics", "amount": 35000.0,  "purchase_date": _ago(150)},

    # Sneha Patil (C1005) — Regular customer
    {"customer_id": "C1005", "product_name": "Kurta Set",      "product_category": "Clothing",    "amount": 2800.0, "purchase_date": _ago(35)},
    {"customer_id": "C1005", "product_name": "Mixer Grinder",  "product_category": "Appliances",  "amount": 5500.0, "purchase_date": _ago(90)},
    {"customer_id": "C1005", "product_name": "Face Cream",     "product_category": "Beauty",      "amount": 1200.0, "purchase_date": _ago(130)},

    # Vikram Joshi (C1008) — Long inactive, complaints
    {"customer_id": "C1008", "product_name": "Garden Tools Set", "product_category": "Home",   "amount": 3500.0, "purchase_date": _ago(500)},
    {"customer_id": "C1008", "product_name": "Yoga Mat",         "product_category": "Sports", "amount": 800.0,  "purchase_date": _ago(550)},

    # Meera Krishnan (C1009) — Active mid-tier
    {"customer_id": "C1009", "product_name": "Bluetooth Speaker", "product_category": "Electronics", "amount": 3999.0, "purchase_date": _ago(60)},
    {"customer_id": "C1009", "product_name": "Cookware Set",      "product_category": "Kitchen",     "amount": 4500.0, "purchase_date": _ago(90)},
    {"customer_id": "C1009", "product_name": "Novel - Fiction",   "product_category": "Books",       "amount": 450.0,  "purchase_date": _ago(130)},

    # Aisha Khan (C1011) — High value, Premium
    {"customer_id": "C1011", "product_name": "Samsung Galaxy S24", "product_category": "Electronics", "amount": 79999.0, "purchase_date": _ago(12)},
    {"customer_id": "C1011", "product_name": "Designer Handbag",   "product_category": "Fashion",     "amount": 15000.0, "purchase_date": _ago(45)},
    {"customer_id": "C1011", "product_name": "Perfume Set",        "product_category": "Beauty",      "amount": 4500.0,  "purchase_date": _ago(90)},

    # Suresh Babu (C1012) — Mid-tier, some complaints
    {"customer_id": "C1012", "product_name": "Ceiling Fan",    "product_category": "Appliances", "amount": 3200.0,  "purchase_date": _ago(110)},
    {"customer_id": "C1012", "product_name": "Water Purifier", "product_category": "Appliances", "amount": 12000.0, "purchase_date": _ago(170)},

    # Neha Saxena (C1013) — Active regular
    {"customer_id": "C1013", "product_name": "Treadmill",     "product_category": "Sports", "amount": 25000.0, "purchase_date": _ago(28)},
    {"customer_id": "C1013", "product_name": "Dumbbells Set", "product_category": "Sports", "amount": 3500.0,  "purchase_date": _ago(58)},

    # Pooja Iyer (C1015) — Top spender, Premium
    {"customer_id": "C1015", "product_name": "Sony 55 inch TV",           "product_category": "Electronics", "amount": 75000.0, "purchase_date": _ago(5)},
    {"customer_id": "C1015", "product_name": "PlayStation 5",             "product_category": "Electronics", "amount": 49990.0, "purchase_date": _ago(40)},
    {"customer_id": "C1015", "product_name": "Gaming Chair",              "product_category": "Furniture",   "amount": 18000.0, "purchase_date": _ago(80)},
    {"customer_id": "C1015", "product_name": "Noise Cancelling Headphones","product_category": "Electronics","amount": 22000.0, "purchase_date": _ago(130)},

    # Kavita Menon (C1019) — Steady active customer
    {"customer_id": "C1019", "product_name": "Dining Table Set", "product_category": "Furniture", "amount": 35000.0, "purchase_date": _ago(25)},
    {"customer_id": "C1019", "product_name": "Pressure Cooker",  "product_category": "Kitchen",   "amount": 2800.0,  "purchase_date": _ago(70)},
    {"customer_id": "C1019", "product_name": "Ethnic Saree",     "product_category": "Clothing",  "amount": 5500.0,  "purchase_date": _ago(120)},

    # Deepika Rao (C1007) — Active, good customer
    {"customer_id": "C1007", "product_name": "Air Purifier",        "product_category": "Appliances", "amount": 12000.0, "purchase_date": _ago(22)},
    {"customer_id": "C1007", "product_name": "Vitamin Supplements", "product_category": "Health",     "amount": 1800.0,  "purchase_date": _ago(75)},

    # Shruti Agarwal (C1017) — Young active customer
    {"customer_id": "C1017", "product_name": "Wireless Earbuds", "product_category": "Electronics", "amount": 3500.0, "purchase_date": _ago(42)},
    {"customer_id": "C1017", "product_name": "Casual Dress",     "product_category": "Clothing",    "amount": 1800.0, "purchase_date": _ago(75)},

    # Siddharth Patel (C1020) — Mid-tier regular
    {"customer_id": "C1020", "product_name": "Laptop Bag",          "product_category": "Accessories", "amount": 2500.0, "purchase_date": _ago(55)},
    {"customer_id": "C1020", "product_name": "Mechanical Keyboard", "product_category": "Electronics", "amount": 5500.0, "purchase_date": _ago(110)},
]


# ============================================================
# Main Seeding Function
# ============================================================

def seed_database():
    """
    Adds all sample customers and purchases to the database.
    Checks if data already exists to avoid duplicates.
    """
    with app.app_context():

        existing = Customer.query.count()
        if existing > 0:
            print(f"Database already has {existing} customers.")
            print("Skipping seed to avoid duplicates.")
            return

        print("Seeding database with sample data...")
        print("-" * 45)

        customer_count = 0
        for data in SAMPLE_CUSTOMERS:
            customer = Customer(**data)
            db.session.add(customer)
            customer_count += 1

        db.session.commit()
        print(f"  Added {customer_count} customers.")

        purchase_count = 0
        for data in SAMPLE_PURCHASES:
            purchase = Purchase(**data)
            db.session.add(purchase)
            purchase_count += 1

        db.session.commit()
        print(f"  Added {purchase_count} purchases.")

        print("-" * 45)
        print("Database seeded successfully!")
        print(f"Total: {customer_count} customers, {purchase_count} purchases")


if __name__ == "__main__":
    seed_database()
