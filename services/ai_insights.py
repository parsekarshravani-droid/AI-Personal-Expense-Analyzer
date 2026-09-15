"""
AI Insights service.

Generates human-readable financial insights from the user's expense data.

Design goal: the app must be fully useful with ZERO external API keys, so
the primary engine here is a deterministic, rule-based analyzer built on
Pandas/NumPy. If an AI_API_KEY is configured (see config.py), a call to an
external LLM can be layered on top to turn the same structured findings
into more natural language - but the insights themselves are always
computed locally from the real data, never invented.
"""

from datetime import date, timedelta

from config import Config
from models import Budget
from services.expense_analyzer import get_all_expenses_df, get_budget_progress


def _month_totals(df, month, year):
    if df.empty:
        return {}
    mask = (df["date"].dt.month == month) & (df["date"].dt.year == year)
    subset = df[mask]
    if subset.empty:
        return {}
    return subset.groupby("category")["amount"].sum().to_dict()


def _shift_month(month, year, delta):
    m = month + delta
    y = year
    while m <= 0:
        m += 12
        y -= 1
    while m > 12:
        m -= 12
        y += 1
    return m, y


def generate_insights(limit=6):
    """Return a list of insight dicts: {type, title, message, icon}.

    type is one of: alert, saving, budget, positive, recommendation, info
    """
    df = get_all_expenses_df()
    insights = []

    if df.empty:
        insights.append(
            {
                "type": "info",
                "title": "Get Started",
                "message": "Add a few expenses and I'll start surfacing personalized spending insights here.",
                "icon": "sparkles",
            }
        )
        return insights

    today = date.today()
    cur_month, cur_year = today.month, today.year
    prev_month, prev_year = _shift_month(cur_month, cur_year, -1)

    cur_totals = _month_totals(df, cur_month, cur_year)
    prev_totals = _month_totals(df, prev_month, prev_year)

    total_this_month = sum(cur_totals.values())

    # 1. Category month-over-month changes (alerts + positive habits)
    changes = []
    all_categories = set(cur_totals) | set(prev_totals)
    for cat in all_categories:
        cur_amt = cur_totals.get(cat, 0.0)
        prev_amt = prev_totals.get(cat, 0.0)
        if prev_amt == 0 and cur_amt == 0:
            continue
        if prev_amt == 0:
            pct = 100.0
        else:
            pct = ((cur_amt - prev_amt) / prev_amt) * 100.0
        changes.append((cat, cur_amt, prev_amt, pct))

    # Biggest increase -> spending alert
    increases = [c for c in changes if c[3] > 15 and c[1] > 0]
    if increases:
        increases.sort(key=lambda c: c[3], reverse=True)
        cat, cur_amt, prev_amt, pct = increases[0]
        insights.append(
            {
                "type": "alert",
                "title": "Spending Alert",
                "message": f"Your {cat.lower()} expenses are {abs(round(pct))}% higher than last month "
                           f"({Config.CURRENCY_SYMBOL}{cur_amt:,.0f} vs {Config.CURRENCY_SYMBOL}{prev_amt:,.0f}).",
                "icon": "trending-up",
            }
        )

    # Biggest decrease -> positive habit
    decreases = [c for c in changes if c[3] < -10 and c[2] > 0]
    if decreases:
        decreases.sort(key=lambda c: c[3])
        cat, cur_amt, prev_amt, pct = decreases[0]
        insights.append(
            {
                "type": "positive",
                "title": "Positive Habit",
                "message": f"Your {cat.lower()} expenses decreased by {abs(round(pct))}% compared with last month. Keep it up!",
                "icon": "trending-down",
            }
        )

    # 2. Highest spending category this month
    if cur_totals:
        top_cat = max(cur_totals, key=cur_totals.get)
        top_amt = cur_totals[top_cat]
        pct_of_total = (top_amt / total_this_month * 100.0) if total_this_month else 0.0
        insights.append(
            {
                "type": "info",
                "title": "Top Category",
                "message": f"{top_cat} is your highest spending category this month at "
                           f"{Config.CURRENCY_SYMBOL}{top_amt:,.0f} ({round(pct_of_total)}% of total spending).",
                "icon": "pie-chart",
            }
        )

    # 3. Budget alerts
    progress = get_budget_progress(cur_month, cur_year)
    over_budget = [p for p in progress if p["raw_percentage"] >= 80]
    if over_budget:
        p = over_budget[0]
        insights.append(
            {
                "type": "budget",
                "title": "Budget Alert",
                "message": f"You have used {round(p['raw_percentage'])}% of your {p['category']} budget "
                           f"({Config.CURRENCY_SYMBOL}{p['spent']:,.0f} of {Config.CURRENCY_SYMBOL}{p['budget']:,.0f}).",
                "icon": "alert-triangle",
            }
        )

    # 4. Saving opportunity: discretionary categories (Food/Shopping/Entertainment)
    discretionary = ["Food", "Shopping", "Entertainment"]
    discretionary_total = sum(cur_totals.get(c, 0.0) for c in discretionary)
    if discretionary_total > 0:
        potential_saving = discretionary_total * 0.2
        cats_present = [c for c in discretionary if cur_totals.get(c, 0) > 0]
        cats_label = " and ".join(cats_present[:2]).lower() if cats_present else "discretionary spending"
        insights.append(
            {
                "type": "saving",
                "title": "Saving Opportunity",
                "message": f"You could save approximately {Config.CURRENCY_SYMBOL}{potential_saving:,.0f}/month "
                           f"by reducing {cats_label} expenses by 20%.",
                "icon": "piggy-bank",
            }
        )

    # 5. Weekend vs weekday spending recommendation
    df_month_mask = (df["date"].dt.month == cur_month) & (df["date"].dt.year == cur_year)
    month_df = df[df_month_mask]
    if not month_df.empty:
        weekend_total = float(month_df[month_df["date"].dt.dayofweek >= 5]["amount"].sum())
        if total_this_month and (weekend_total / total_this_month) > 0.4:
            insights.append(
                {
                    "type": "recommendation",
                    "title": "Recommendation",
                    "message": f"Weekend spending makes up {round(weekend_total / total_this_month * 100)}% of this "
                               f"month's expenses. Try setting a weekly weekend limit of "
                               f"{Config.CURRENCY_SYMBOL}{(total_this_month * 0.25):,.0f}.",
                    "icon": "calendar",
                }
            )

    # 6. Recurring expense detection (same description appears 2+ times)
    recurring = df.groupby("description").filter(lambda g: len(g) >= 2)
    if not recurring.empty:
        recurring_desc = recurring["description"].value_counts().index[0]
        count = int(recurring["description"].value_counts().iloc[0])
        avg_amt = float(recurring[recurring["description"] == recurring_desc]["amount"].mean())
        insights.append(
            {
                "type": "info",
                "title": "Recurring Expense",
                "message": f"'{recurring_desc}' appears {count} times in your history, averaging "
                           f"{Config.CURRENCY_SYMBOL}{avg_amt:,.0f} each time. Consider if a subscription "
                           f"or bundled plan could reduce this.",
                "icon": "repeat",
            }
        )

    if not insights:
        insights.append(
            {
                "type": "positive",
                "title": "Looking Good",
                "message": "Your spending looks steady this month with no major red flags. Keep tracking to unlock deeper trends.",
                "icon": "check-circle",
            }
        )

    return insights[:limit]


def generate_recommendations():
    """A focused list of savings-oriented recommendations for the reports page."""
    df = get_all_expenses_df()
    if df.empty:
        return ["Add some expenses to receive personalized savings recommendations."]

    recs = []
    today = date.today()
    cur_totals = _month_totals(df, today.month, today.year)

    if cur_totals:
        top_cat = max(cur_totals, key=cur_totals.get)
        top_amt = cur_totals[top_cat]
        saving = top_amt * 0.2
        recs.append(
            f"Reducing {top_cat.lower()} spending by 20% could save approximately "
            f"{Config.CURRENCY_SYMBOL}{saving:,.0f} per month."
        )

    progress = get_budget_progress(today.month, today.year)
    for p in progress:
        if p["raw_percentage"] >= 90:
            recs.append(f"You have used {round(p['raw_percentage'])}% of your {p['category']} budget - consider slowing down spending in this category for the rest of the month.")

    anomalies_desc = df.groupby("category")["amount"].std(ddof=0).fillna(0)
    volatile_cats = anomalies_desc[anomalies_desc > anomalies_desc.mean()].index.tolist() if not anomalies_desc.empty else []
    if volatile_cats:
        recs.append(
            f"Your spending in {volatile_cats[0]} varies a lot month to month - setting a fixed weekly cap could help smooth this out."
        )

    if not recs:
        recs.append("Your spending is well balanced across categories. Keep maintaining your current habits.")

    return recs


def generate_notifications(limit=10):
    """Real-data alerts for the notification bell: budget breaches and
    unusual expenses. Unlike generate_insights() (which picks one headline
    item per theme for the dashboard), this returns every item that
    currently needs the user's attention.
    """
    from services.expense_analyzer import find_all_anomalies

    today = date.today()
    notifications = []

    # 1. Budget alerts - every category at/over the configured threshold.
    progress = get_budget_progress(today.month, today.year)
    for p in progress:
        if p["raw_percentage"] < Config.BUDGET_ALERT_THRESHOLD:
            continue
        over = p["raw_percentage"] >= 100
        notifications.append(
            {
                "type": "danger" if over else "warning",
                "title": "Budget exceeded" if over else "Budget alert",
                "message": f"{p['category']}: {round(p['raw_percentage'])}% of "
                           f"{Config.CURRENCY_SYMBOL}{p['budget']:,.0f} used "
                           f"({Config.CURRENCY_SYMBOL}{p['spent']:,.0f} spent).",
                "icon": "alert-triangle",
                "severity": 2 if over else 1,
            }
        )

    # 2. Unusual expenses from the current month.
    anomalies = find_all_anomalies()
    month_anomalies = [a for a in anomalies if a["date"].startswith(f"{today.year:04d}-{today.month:02d}")]
    for a in month_anomalies[:5]:
        notifications.append(
            {
                "type": "alert",
                "title": "Unusual expense detected",
                "message": f"{a['description']} ({a['category']}) was "
                           f"{Config.CURRENCY_SYMBOL}{a['amount']:,.0f}, well above the usual "
                           f"{Config.CURRENCY_SYMBOL}{a['average']:,.0f} for that category.",
                "icon": "zap",
                "severity": 1,
            }
        )

    notifications.sort(key=lambda n: n["severity"], reverse=True)
    return notifications[:limit]


def is_external_ai_configured():
    """Whether an external AI API key has been provided (fully optional)."""
    return Config.AI_API_ENABLED
