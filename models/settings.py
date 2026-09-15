"""
SQLAlchemy model for application-wide settings.

There is always exactly one row in this table (id=1). It stores the
user-editable preferences that used to be hardcoded in config.py:
currency symbol, the category/payment-method lists, the budget alert
threshold, and an optional local AI API key override.
"""

from datetime import datetime
from models import db


class Settings(db.Model):
    """Singleton row holding app-wide, user-editable preferences."""

    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True)
    currency_symbol = db.Column(db.String(5), nullable=False, default="\u20b9")
    categories = db.Column(db.Text, nullable=False, default="")  # comma-separated
    payment_methods = db.Column(db.Text, nullable=False, default="")  # comma-separated
    budget_alert_threshold = db.Column(db.Integer, nullable=False, default=80)
    ai_api_key = db.Column(db.String(255), nullable=True, default="")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def category_list(self):
        return [c.strip() for c in (self.categories or "").split(",") if c.strip()]

    def payment_method_list(self):
        return [p.strip() for p in (self.payment_methods or "").split(",") if p.strip()]

    def set_category_list(self, items):
        self.categories = ",".join(items)

    def set_payment_method_list(self, items):
        self.payment_methods = ",".join(items)

    def __repr__(self):
        return f"<Settings currency={self.currency_symbol!r}>"
