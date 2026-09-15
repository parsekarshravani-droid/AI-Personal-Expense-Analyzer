"""
CSV import/export service.

Handles validating and parsing uploaded CSV files, and building CSV exports
of the user's expenses.
"""

import io
import csv
from datetime import datetime

import pandas as pd

from config import Config

REQUIRED_COLUMNS = ["date", "amount", "category", "description", "payment_method"]


def validate_and_parse_csv(file_stream):
    """Parse an uploaded CSV file, validating rows.

    Returns a dict with:
        valid_rows: list[dict] ready to insert as Expense records
        invalid_rows: list[dict] with an "error" key explaining the problem
        total_amount: sum of valid rows' amounts
    """
    try:
        df = pd.read_csv(file_stream)
    except Exception as exc:  # noqa: BLE001 - surface a friendly error to the UI
        return {"error": f"Could not read CSV file: {exc}"}

    df.columns = [str(c).strip().lower() for c in df.columns]

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        return {"error": f"CSV is missing required column(s): {', '.join(missing)}"}

    valid_rows = []
    invalid_rows = []

    for idx, row in df.iterrows():
        errors = []

        # Date
        parsed_date = None
        raw_date = row.get("date")
        if pd.isna(raw_date):
            errors.append("missing date")
        else:
            parsed_date = _parse_date(str(raw_date))
            if parsed_date is None:
                errors.append("invalid date format")

        # Amount
        amount = None
        raw_amount = row.get("amount")
        try:
            amount = float(raw_amount)
            if amount <= 0:
                errors.append("amount must be positive")
        except (TypeError, ValueError):
            errors.append("invalid amount")

        # Category
        category = str(row.get("category", "")).strip().title()
        if not category or category == "Nan":
            errors.append("missing category")
        elif category not in Config.CATEGORIES:
            category = "Other"  # gracefully default rather than reject

        # Description
        description = str(row.get("description", "")).strip()
        if not description or description.lower() == "nan":
            description = category

        # Payment method
        payment_method = str(row.get("payment_method", "")).strip().title()
        if not payment_method or payment_method == "Nan" or payment_method not in Config.PAYMENT_METHODS:
            payment_method = "Other"

        if errors:
            invalid_rows.append({"row": idx + 2, "data": row.to_dict(), "error": "; ".join(errors)})
            continue

        valid_rows.append(
            {
                "date": parsed_date,
                "amount": amount,
                "category": category,
                "description": description,
                "payment_method": payment_method,
                "notes": str(row.get("notes", "")).strip() if "notes" in df.columns else "",
            }
        )

    total_amount = sum(r["amount"] for r in valid_rows)

    return {
        "valid_rows": valid_rows,
        "invalid_rows": invalid_rows,
        "total_amount": round(total_amount, 2),
        "valid_count": len(valid_rows),
        "invalid_count": len(invalid_rows),
    }


def _parse_date(raw):
    formats = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"]
    for fmt in formats:
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    # Fall back to pandas' flexible parser
    try:
        return pd.to_datetime(raw).date()
    except Exception:  # noqa: BLE001
        return None


def export_expenses_to_csv(expenses):
    """Build a CSV string (in-memory) from a list of Expense ORM objects."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "amount", "category", "description", "payment_method", "notes"])

    for e in expenses:
        writer.writerow(
            [
                e.date.isoformat() if e.date else "",
                e.amount,
                e.category,
                e.description,
                e.payment_method,
                e.notes or "",
            ]
        )

    output.seek(0)
    return output.getvalue()
