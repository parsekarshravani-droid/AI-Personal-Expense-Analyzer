"""
Models package.

Exposes the shared SQLAlchemy `db` instance and the ORM models so the rest
of the application can simply do `from models import db, Expense, Budget`.
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Import models after `db` is created to avoid circular imports.
from models.expense import Expense, Budget, TotalBudget  # noqa: E402,F401
from models.settings import Settings  # noqa: E402,F401
