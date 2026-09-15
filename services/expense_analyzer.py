"""
Expense Analyzer service.

Pure data-crunching logic built on Pandas/NumPy: dashboard summaries,
analytics breakdowns, smart category suggestion, and anomaly detection.
No Flask imports here - this module only knows about data.
"""

from datetime import date, timedelta
from calendar import monthrange

import numpy as np
import pandas as pd

from models import Expense, Budget, TotalBudget


# ----------------------------------------------------------------------
# Data loading helpers
# ----------------------------------------------------------------------

def expenses_to_dataframe(expenses):
    """Convert a list of Expense ORM objects into a tidy DataFrame."""
    if not expenses:
        return pd.DataFrame(
            columns=["id", "amount", "category", "description", "date", "payment_method", "notes"]
        )

    rows = [
        {
            "id": e.id,
            "amount": float(e.amount),
            "category": e.category,
            "description": e.description,
            "date": pd.to_datetime(e.date),
            "payment_method": e.payment_method,
            "notes": e.notes or "",
        }
        for e in expenses
    ]
    df = pd.DataFrame(rows)
    return df


def get_all_expenses_df():
    """Fetch every expense from the database as a DataFrame."""
    expenses = Expense.query.all()
    return expenses_to_dataframe(expenses)


# ----------------------------------------------------------------------
# Dashboard summary
# ----------------------------------------------------------------------

def get_dashboard_summary():
    """Build the numbers shown on the dashboard summary cards."""
    df = get_all_expenses_df()
    today = date.today()

    if df.empty:
        return {
            "total_expenses": 0.0,
            "month_expenses": 0.0,
            "today_expenses": 0.0,
            "avg_daily_spending": 0.0,
            "highest_category": "N/A",
            "highest_category_amount": 0.0,
            "total_budget": 0.0,
            "total_spent_this_month": 0.0,
            "remaining_budget": 0.0,
            "transaction_count": 0,
            "month_change_pct": 0.0,
            "today_change_pct": 0.0,
        }

    df["date_only"] = df["date"].dt.date

    total_expenses = float(df["amount"].sum())
    transaction_count = int(len(df))

    # Current month
    month_mask = (df["date"].dt.month == today.month) & (df["date"].dt.year == today.year)
    month_df = df[month_mask]
    month_expenses = float(month_df["amount"].sum())

    # Previous month for comparison
    prev_month_date = (today.replace(day=1) - timedelta(days=1))
    prev_mask = (df["date"].dt.month == prev_month_date.month) & (df["date"].dt.year == prev_month_date.year)
    prev_month_total = float(df[prev_mask]["amount"].sum())
    month_change_pct = _pct_change(prev_month_total, month_expenses)

    # Today
    today_df = df[df["date_only"] == today]
    today_expenses = float(today_df["amount"].sum())
    yesterday = today - timedelta(days=1)
    yesterday_total = float(df[df["date_only"] == yesterday]["amount"].sum())
    today_change_pct = _pct_change(yesterday_total, today_expenses)

    # Average daily spending (across days that actually have data)
    days_span = max((df["date_only"].max() - df["date_only"].min()).days + 1, 1)
    avg_daily_spending = float(total_expenses / days_span)

    # Highest spending category (current month, fallback to all-time)
    basis_df = month_df if not month_df.empty else df
    cat_totals = basis_df.groupby("category")["amount"].sum().sort_values(ascending=False)
    highest_category = cat_totals.index[0] if not cat_totals.empty else "N/A"
    highest_category_amount = float(cat_totals.iloc[0]) if not cat_totals.empty else 0.0

    # Budget for the current month - uses the user's own total budget if
    # they've set one, otherwise falls back to the sum of category budgets.
    total_budget = get_total_budget(today.month, today.year)
    remaining_budget = float(total_budget - month_expenses)

    return {
        "total_expenses": round(total_expenses, 2),
        "month_expenses": round(month_expenses, 2),
        "today_expenses": round(today_expenses, 2),
        "avg_daily_spending": round(avg_daily_spending, 2),
        "highest_category": highest_category,
        "highest_category_amount": round(highest_category_amount, 2),
        "total_budget": round(total_budget, 2),
        "total_spent_this_month": round(month_expenses, 2),
        "remaining_budget": round(remaining_budget, 2),
        "transaction_count": transaction_count,
        "month_change_pct": round(month_change_pct, 1),
        "today_change_pct": round(today_change_pct, 1),
    }


def _pct_change(old, new):
    """Percentage change from old to new, guarding against divide-by-zero."""
    if old == 0:
        return 100.0 if new > 0 else 0.0
    return ((new - old) / old) * 100.0


# ----------------------------------------------------------------------
# Chart data for the dashboard
# ----------------------------------------------------------------------

def get_monthly_trend(months=6):
    """Total spend for each of the last N months, oldest first."""
    df = get_all_expenses_df()
    today = date.today()

    labels, values = [], []
    for i in range(months - 1, -1, -1):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        label = date(year, month, 1).strftime("%b %Y")
        if df.empty:
            total = 0.0
        else:
            mask = (df["date"].dt.month == month) & (df["date"].dt.year == year)
            total = float(df[mask]["amount"].sum())
        labels.append(label)
        values.append(round(total, 2))

    return {"labels": labels, "values": values}


def get_category_distribution(month_only=False):
    """Category-wise totals for the doughnut chart."""
    df = get_all_expenses_df()
    if df.empty:
        return {"labels": [], "values": []}

    if month_only:
        today = date.today()
        df = df[(df["date"].dt.month == today.month) & (df["date"].dt.year == today.year)]

    if df.empty:
        return {"labels": [], "values": []}

    totals = df.groupby("category")["amount"].sum().sort_values(ascending=False)
    return {"labels": totals.index.tolist(), "values": [round(v, 2) for v in totals.values]}


def get_daily_spending(days=30):
    """Daily totals for the last N days for the line chart."""
    df = get_all_expenses_df()
    today = date.today()
    start = today - timedelta(days=days - 1)

    labels, values = [], []
    if not df.empty:
        df["date_only"] = df["date"].dt.date

    for i in range(days):
        d = start + timedelta(days=i)
        if df.empty:
            total = 0.0
        else:
            total = float(df[df["date_only"] == d]["amount"].sum())
        labels.append(d.strftime("%d %b"))
        values.append(round(total, 2))

    return {"labels": labels, "values": values}


def get_payment_method_distribution():
    df = get_all_expenses_df()
    if df.empty:
        return {"labels": [], "values": []}
    totals = df.groupby("payment_method")["amount"].sum().sort_values(ascending=False)
    return {"labels": totals.index.tolist(), "values": [round(v, 2) for v in totals.values]}


def get_weekday_distribution():
    """Average and total spending grouped by day of week (Mon-Sun)."""
    df = get_all_expenses_df()
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    if df.empty:
        return {"labels": order, "values": [0] * 7}

    df["weekday"] = df["date"].dt.day_name()
    totals = df.groupby("weekday")["amount"].sum()
    values = [round(float(totals.get(day, 0.0)), 2) for day in order]
    return {"labels": order, "values": values}


def get_weekly_spending(weeks=8):
    """Total spend per ISO week for the last N weeks."""
    df = get_all_expenses_df()
    today = date.today()
    labels, values = [], []

    for i in range(weeks - 1, -1, -1):
        week_start = today - timedelta(days=today.weekday() + i * 7)
        week_end = week_start + timedelta(days=6)
        label = f"{week_start.strftime('%d %b')}"
        if df.empty:
            total = 0.0
        else:
            df["date_only"] = df["date"].dt.date
            mask = (df["date_only"] >= week_start) & (df["date_only"] <= week_end)
            total = float(df[mask]["amount"].sum())
        labels.append(label)
        values.append(round(total, 2))

    return {"labels": labels, "values": values}


def get_analytics_summary():
    """A bundle of stats used by the analytics page beyond the charts."""
    df = get_all_expenses_df()
    if df.empty:
        return {
            "highest_expense": 0.0,
            "highest_expense_category": "N/A",
            "average_transaction": 0.0,
            "weekend_total": 0.0,
            "weekday_total": 0.0,
            "weekend_avg": 0.0,
            "weekday_avg": 0.0,
            "total_transactions": 0,
        }

    df["weekday_num"] = df["date"].dt.dayofweek  # 5,6 = Sat,Sun
    weekend_df = df[df["weekday_num"] >= 5]
    weekday_df = df[df["weekday_num"] < 5]

    highest_idx = df["amount"].idxmax()
    highest_row = df.loc[highest_idx]

    return {
        "highest_expense": round(float(df["amount"].max()), 2),
        "highest_expense_category": highest_row["category"],
        "average_transaction": round(float(df["amount"].mean()), 2),
        "weekend_total": round(float(weekend_df["amount"].sum()), 2),
        "weekday_total": round(float(weekday_df["amount"].sum()), 2),
        "weekend_avg": round(float(weekend_df["amount"].mean()) if not weekend_df.empty else 0.0, 2),
        "weekday_avg": round(float(weekday_df["amount"].mean()) if not weekday_df.empty else 0.0, 2),
        "total_transactions": int(len(df)),
    }


# ----------------------------------------------------------------------
# Budget progress
# ----------------------------------------------------------------------

def get_total_budget(month=None, year=None):
    """Return the overall monthly spending limit as a single number.

    The user's own total budget (set on the Budgets page) always wins
    when it exists for that month. If they haven't set one yet, this
    falls back to the sum of whatever per-category budgets exist, so
    the dashboard still shows something sensible before they do.
    """
    today = date.today()
    month = month or today.month
    year = year or today.year

    total_row = TotalBudget.query.filter_by(month=month, year=year).first()
    if total_row is not None:
        return float(total_row.amount)

    budgets = Budget.query.filter_by(month=month, year=year).all()
    return float(sum(b.amount for b in budgets))


def has_custom_total_budget(month=None, year=None):
    """Whether the user has explicitly set their own total budget (as
    opposed to it being derived from the sum of category budgets)."""
    today = date.today()
    month = month or today.month
    year = year or today.year
    return TotalBudget.query.filter_by(month=month, year=year).first() is not None


def get_total_budget_progress(month=None, year=None):
    """Spend-vs-limit progress for the overall monthly budget (not tied
    to any single category)."""
    today = date.today()
    month = month or today.month
    year = year or today.year

    df = get_all_expenses_df()
    if not df.empty:
        month_mask = (df["date"].dt.month == month) & (df["date"].dt.year == year)
        spent = float(df[month_mask]["amount"].sum())
    else:
        spent = 0.0

    budget = get_total_budget(month, year)
    pct = (spent / budget * 100.0) if budget > 0 else 0.0

    if pct >= 90:
        status = "danger"
    elif pct >= 70:
        status = "warning"
    else:
        status = "normal"

    return {
        "budget": round(budget, 2),
        "spent": round(spent, 2),
        "remaining": round(budget - spent, 2),
        "percentage": round(min(pct, 100.0), 1),
        "raw_percentage": round(pct, 1),
        "status": status,
        "is_custom": has_custom_total_budget(month, year),
    }


def get_budget_progress(month=None, year=None):
    """Compute spend-vs-budget progress for every budgeted category."""
    today = date.today()
    month = month or today.month
    year = year or today.year

    df = get_all_expenses_df()
    if not df.empty:
        month_mask = (df["date"].dt.month == month) & (df["date"].dt.year == year)
        month_df = df[month_mask]
    else:
        month_df = df

    budgets = Budget.query.filter_by(month=month, year=year).all()
    progress = []

    for b in budgets:
        spent = float(month_df[month_df["category"] == b.category]["amount"].sum()) if not month_df.empty else 0.0
        pct = (spent / b.amount * 100.0) if b.amount > 0 else 0.0
        if pct >= 90:
            status = "danger"
        elif pct >= 70:
            status = "warning"
        else:
            status = "normal"

        progress.append(
            {
                "id": b.id,
                "category": b.category,
                "budget": round(b.amount, 2),
                "spent": round(spent, 2),
                "remaining": round(b.amount - spent, 2),
                "percentage": round(min(pct, 100.0), 1),
                "raw_percentage": round(pct, 1),
                "status": status,
            }
        )

    return sorted(progress, key=lambda p: p["raw_percentage"], reverse=True)


# ----------------------------------------------------------------------
# Smart category classification
# ----------------------------------------------------------------------

CATEGORY_KEYWORDS = {
    "Food": [
        "pizza", "burger", "restaurant", "cafe", "coffee", "dinner", "lunch",
        "breakfast", "swiggy", "zomato", "dominos", "domino", "food", "snack",
        "kfc", "mcdonald", "starbucks", "biryani", "meal", "dine",
    ],
    "Transport": [
        "uber", "ola", "taxi", "cab", "fuel", "petrol", "diesel", "auto",
        "bus", "train", "metro", "rickshaw", "ride", "parking", "toll",
    ],
    "Entertainment": [
        "netflix", "movie", "cinema", "spotify", "prime video", "hotstar",
        "concert", "game", "gaming", "youtube premium", "amusement", "party",
    ],
    "Shopping": [
        "shoes", "clothes", "amazon", "flipkart", "myntra", "mall", "shopping",
        "dress", "shirt", "bag", "watch", "jeans", "sale",
    ],
    "Bills": [
        "electricity", "bill", "water bill", "recharge", "wifi", "internet",
        "broadband", "gas bill", "mobile bill", "dth", "rent",
    ],
    "Education": [
        "books", "college", "school", "tuition", "course", "udemy", "fees",
        "exam", "stationery", "coaching",
    ],
    "Health": [
        "medicine", "doctor", "hospital", "pharmacy", "clinic", "gym",
        "medical", "health", "dentist",
    ],
    "Travel": [
        "flight", "hotel", "trip", "vacation", "travel", "airbnb", "booking",
        "holiday", "tour",
    ],
    "Groceries": [
        "grocery", "groceries", "supermarket", "vegetables", "bigbasket",
        "dmart", "milk", "kirana",
    ],
}


def suggest_category(description):
    """Suggest a category for a free-text expense description.

    Simple, transparent keyword matching - deliberately rule-based so it
    works with zero external dependencies and is easy to reason about.
    """
    if not description:
        return "Other"

    text = description.lower()
    scores = {category: 0 for category in CATEGORY_KEYWORDS}

    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[category] += 1

    best_category = max(scores, key=scores.get)
    if scores[best_category] == 0:
        return "Other"
    return best_category


# ----------------------------------------------------------------------
# Anomaly detection
# ----------------------------------------------------------------------

def detect_anomaly(amount, category):
    """Flag an expense as unusual if it's a statistical outlier for its category.

    Uses mean + 2*std as a threshold (classic simple outlier rule), and
    requires at least 3 historical points in that category to be meaningful.
    """
    df = get_all_expenses_df()
    if df.empty:
        return {"is_unusual": False, "message": ""}

    cat_df = df[df["category"] == category]
    if len(cat_df) < 3:
        return {"is_unusual": False, "message": ""}

    mean = float(cat_df["amount"].mean())
    std = float(cat_df["amount"].std(ddof=0)) or 0.0
    threshold = mean + 2 * std

    if amount > threshold and amount > mean * 1.5:
        return {
            "is_unusual": True,
            "message": (
                f"This expense is significantly higher than your normal {category} "
                f"spending (avg is roughly {round(mean, 0):,.0f})."
            ),
            "average": round(mean, 2),
        }

    return {"is_unusual": False, "message": ""}


def find_all_anomalies():
    """Scan the whole dataset and return expenses that look like outliers."""
    df = get_all_expenses_df()
    if df.empty:
        return []

    anomalies = []
    for category in df["category"].unique():
        cat_df = df[df["category"] == category]
        if len(cat_df) < 3:
            continue
        mean = cat_df["amount"].mean()
        std = cat_df["amount"].std(ddof=0) or 0
        threshold = mean + 2 * std
        outliers = cat_df[(cat_df["amount"] > threshold) & (cat_df["amount"] > mean * 1.5)]
        for _, row in outliers.iterrows():
            anomalies.append(
                {
                    "id": int(row["id"]),
                    "category": category,
                    "amount": round(float(row["amount"]), 2),
                    "average": round(float(mean), 2),
                    "date": row["date"].strftime("%Y-%m-%d"),
                    "description": row["description"],
                }
            )
    return anomalies


# ----------------------------------------------------------------------
# Report generation support
# ----------------------------------------------------------------------

def get_monthly_report_data(month=None, year=None):
    """All figures needed to render/export the monthly report."""
    today = date.today()
    month = month or today.month
    year = year or today.year

    df = get_all_expenses_df()
    if not df.empty:
        mask = (df["date"].dt.month == month) & (df["date"].dt.year == year)
        month_df = df[mask]
    else:
        month_df = df

    total_spending = float(month_df["amount"].sum()) if not month_df.empty else 0.0
    days_in_month = monthrange(year, month)[1]
    avg_daily = total_spending / days_in_month if days_in_month else 0.0

    category_breakdown = []
    if not month_df.empty:
        cat_totals = month_df.groupby("category")["amount"].sum().sort_values(ascending=False)
        for cat, amt in cat_totals.items():
            pct = (amt / total_spending * 100.0) if total_spending else 0.0
            category_breakdown.append({"category": cat, "amount": round(float(amt), 2), "percentage": round(pct, 1)})

    highest_expense = None
    if not month_df.empty:
        row = month_df.loc[month_df["amount"].idxmax()]
        highest_expense = {
            "amount": round(float(row["amount"]), 2),
            "category": row["category"],
            "description": row["description"],
            "date": row["date"].strftime("%Y-%m-%d"),
        }

    budget_status = get_budget_progress(month, year)
    total_budget_progress = get_total_budget_progress(month, year)

    return {
        "month": month,
        "year": year,
        "month_name": date(year, month, 1).strftime("%B %Y"),
        "total_spending": round(total_spending, 2),
        "average_daily_spending": round(avg_daily, 2),
        "category_breakdown": category_breakdown,
        "highest_expense": highest_expense,
        "budget_status": budget_status,
        "total_budget": total_budget_progress["budget"],
        "total_budget_progress": total_budget_progress,
        "transaction_count": int(len(month_df)) if not month_df.empty else 0,
    }
