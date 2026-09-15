"""
SQLAlchemy ORM models for expenses and budgets.
"""

from datetime import datetime, date
from models import db


class Expense(db.Model):
    """A single recorded expense transaction."""

    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True)
    description = db.Column(db.String(255), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    payment_method = db.Column(db.String(50), nullable=False, default="Cash")
    notes = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Serialize the expense to a plain dict (used by JSON APIs)."""
        return {
            "id": self.id,
            "amount": self.amount,
            "category": self.category,
            "description": self.description,
            "date": self.date.isoformat() if self.date else None,
            "payment_method": self.payment_method,
            "notes": self.notes or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Expense {self.id} {self.category} {self.amount}>"


class Budget(db.Model):
    """A monthly budget limit set for a specific category."""

    __tablename__ = "budgets"

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False, index=True)
    month = db.Column(db.Integer, nullable=False)  # 1-12
    year = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("category", "month", "year", name="uq_budget_category_month_year"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "month": self.month,
            "year": self.year,
            "amount": self.amount,
        }

    def __repr__(self):
        return f"<Budget {self.category} {self.month}/{self.year} {self.amount}>"


class TotalBudget(db.Model):
    """The user's own overall monthly spending limit.

    This is independent of (and not derived from) the per-category
    Budget rows above - it is a single number the user sets for the
    whole month, e.g. "I don't want to spend more than 25,000 total
    this month" regardless of how that breaks down by category.
    """

    __tablename__ = "total_budgets"

    id = db.Column(db.Integer, primary_key=True)
    month = db.Column(db.Integer, nullable=False)  # 1-12
    year = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("month", "year", name="uq_total_budget_month_year"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "month": self.month,
            "year": self.year,
            "amount": self.amount,
        }

    def __repr__(self):
        return f"<TotalBudget {self.month}/{self.year} {self.amount}>"
