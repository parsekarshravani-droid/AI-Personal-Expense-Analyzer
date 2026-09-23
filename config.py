"""
Application configuration.

Loads settings from environment variables (via a .env file if present) and
exposes a single Config object used by app.py.
"""

import os
from dotenv import load_dotenv

# Load variables from a .env file into the process environment, if one exists.
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Central configuration for the Flask application."""

    # Flask
    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "dev-secret-key-change-in-production"
    )
    DEBUG = os.environ.get("FLASK_DEBUG", "True") == "True"

    # Database
    # Render Persistent Disk:
    # DATABASE_PATH=/var/data/expense.db
    #
    # Local development:
    # database/expense.db
    DATABASE_PATH = os.environ.get(
        "DATABASE_PATH",
        os.path.join(BASE_DIR, "database", "expense.db")
    )

    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Uploads
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    ALLOWED_EXTENSIONS = {"csv"}
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB max upload size

    # AI / external API (optional - app works fully without this)
    AI_API_KEY = os.environ.get("AI_API_KEY", "")
    AI_API_ENABLED = bool(AI_API_KEY)

    # Currency
    CURRENCY_SYMBOL = "\u20b9"  # Indian Rupee sign

    # Budgets - default category list used across the app
    CATEGORIES = [
        "Food",
        "Shopping",
        "Transport",
        "Bills",
        "Entertainment",
        "Health",
        "Education",
        "Travel",
        "Groceries",
        "Other",
    ]

    PAYMENT_METHODS = [
        "Cash",
        "Credit Card",
        "Debit Card",
        "UPI",
        "Bank Transfer",
        "Other",
    ]

    # Percentage of a category budget used at which alerts/notifications
    # start firing. Overridden at runtime from Settings (see app.py).
    BUDGET_ALERT_THRESHOLD = 80
