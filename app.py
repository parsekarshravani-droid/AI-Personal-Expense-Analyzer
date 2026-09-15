"""
AI Personal Expense Analyzer
=============================
Main Flask application entry point.

Run with:
    python app.py

Then open http://127.0.0.1:5000 in your browser.
"""

import io
import os
from datetime import datetime, date, timedelta

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
    flash,
    send_file,
    abort,
)
from werkzeug.utils import secure_filename

from config import Config
from models import db, Expense, Budget, TotalBudget, Settings
from services import expense_analyzer as analyzer
from services import ai_insights
from services import csv_service


def create_app():
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    with app.app_context():
        os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        db.create_all()
        _seed_sample_data_if_empty()
        _apply_settings_to_config(_get_or_create_settings())

    register_routes(app)
    register_template_filters(app)
    return app


# ----------------------------------------------------------------------
# Settings
# ----------------------------------------------------------------------

def _get_or_create_settings():
    """Return the single Settings row, creating it from config.py defaults
    on first run."""
    settings = Settings.query.get(1)
    if settings is None:
        settings = Settings(
            id=1,
            currency_symbol=Config.CURRENCY_SYMBOL,
            budget_alert_threshold=80,
            ai_api_key=Config.AI_API_KEY,
        )
        settings.set_category_list(Config.CATEGORIES)
        settings.set_payment_method_list(Config.PAYMENT_METHODS)
        db.session.add(settings)
        db.session.commit()
    return settings


def _apply_settings_to_config(settings):
    """Push the persisted settings onto the Config class so every part of
    the app (which reads Config.* at call time) picks up the change."""
    Config.CURRENCY_SYMBOL = settings.currency_symbol
    Config.CATEGORIES = settings.category_list()
    Config.PAYMENT_METHODS = settings.payment_method_list()
    # An explicit key saved in Settings takes priority over the .env value,
    # but the app keeps working with neither set (rule-based insights only).
    Config.AI_API_KEY = settings.ai_api_key or os.environ.get("AI_API_KEY", "")
    Config.AI_API_ENABLED = bool(Config.AI_API_KEY)
    Config.BUDGET_ALERT_THRESHOLD = settings.budget_alert_threshold


# ----------------------------------------------------------------------
# Sample / demo data
# ----------------------------------------------------------------------

def _seed_sample_data_if_empty():
    """Populate the database with realistic demo data on first run."""
    if Expense.query.first() is not None:
        return

    today = date.today()

    sample_expenses = [
        # (days_ago, category, description, amount, payment_method)
        (0, "Food", "Lunch at cafe", 350, "UPI"),
        (0, "Transport", "Auto ride to office", 150, "Cash"),
        (1, "Groceries", "Weekly groceries - BigBasket", 1450, "Credit Card"),
        (1, "Food", "Dinner - Domino's Pizza", 620, "UPI"),
        (2, "Entertainment", "Netflix subscription", 499, "Credit Card"),
        (2, "Transport", "Uber ride", 240, "UPI"),
        (3, "Bills", "Electricity bill", 1800, "Bank Transfer"),
        (4, "Shopping", "Bought shoes", 2450, "Debit Card"),
        (5, "Food", "Breakfast", 280, "Cash"),
        (6, "Health", "Pharmacy - medicines", 540, "UPI"),
        (7, "Food", "Groceries top-up", 320, "Cash"),
        (8, "Transport", "Petrol refill", 1200, "Debit Card"),
        (9, "Shopping", "Amazon - electronics accessory", 1299, "Credit Card"),
        (10, "Entertainment", "Movie tickets", 799, "UPI"),
        (12, "Bills", "Mobile recharge", 599, "UPI"),
        (14, "Education", "Online course - Udemy", 1200, "Credit Card"),
        (15, "Food", "Swiggy order", 430, "UPI"),
        (16, "Groceries", "DMart shopping", 980, "Debit Card"),
        (18, "Transport", "Ola cab", 420, "UPI"),
        (20, "Food", "Team lunch", 850, "Cash"),
        (21, "Health", "Gym membership", 1500, "Bank Transfer"),
        (23, "Shopping", "Myntra - clothes", 1899, "Credit Card"),
        (25, "Bills", "Internet bill", 999, "Bank Transfer"),
        (27, "Food", "Weekend dinner", 1250, "UPI"),
        (29, "Travel", "Weekend trip - hotel booking", 3500, "Credit Card"),
        (32, "Food", "Coffee runs (weekly)", 450, "Cash"),
        (35, "Entertainment", "Concert tickets", 2200, "UPI"),
        (38, "Transport", "Monthly metro pass", 1200, "Debit Card"),
        (40, "Groceries", "Groceries - Kirana store", 620, "Cash"),
        (42, "Shopping", "Bought a jacket", 2999, "Credit Card"),
        (45, "Food", "Domino's Pizza order", 1850, "UPI"),  # anomaly vs typical food spend
        (48, "Bills", "Water bill", 450, "Bank Transfer"),
        (50, "Health", "Doctor visit", 800, "UPI"),
        (55, "Education", "College books", 1600, "Debit Card"),
        (58, "Food", "Groceries", 390, "Cash"),
        (60, "Transport", "Fuel", 1350, "Debit Card"),
        (65, "Entertainment", "Spotify + Netflix bundle", 649, "Credit Card"),
        (70, "Shopping", "Festive shopping", 3200, "Credit Card"),
        (75, "Food", "Family dinner out", 1450, "UPI"),
        (80, "Bills", "Electricity bill", 1650, "Bank Transfer"),
        (85, "Groceries", "Monthly groceries", 2100, "Debit Card"),
        (90, "Travel", "Flight tickets", 5400, "Credit Card"),
    ]

    for days_ago, category, desc, amount, method in sample_expenses:
        exp_date = today - timedelta(days=days_ago)
        db.session.add(
            Expense(
                amount=amount,
                category=category,
                description=desc,
                date=exp_date,
                payment_method=method,
                notes="",
            )
        )

    # Sample budgets for the current month
    sample_budgets = [
        ("Food", 8000),
        ("Shopping", 5000),
        ("Transport", 3000),
        ("Entertainment", 2000),
        ("Bills", 5000),
        ("Groceries", 4000),
    ]
    for category, amount in sample_budgets:
        db.session.add(Budget(category=category, month=today.month, year=today.year, amount=amount))

    # A sample overall monthly budget, set by the user independently of
    # the category budgets above.
    if TotalBudget.query.filter_by(month=today.month, year=today.year).first() is None:
        db.session.add(TotalBudget(month=today.month, year=today.year, amount=30000))

    db.session.commit()


# ----------------------------------------------------------------------
# Template filters / globals
# ----------------------------------------------------------------------

def register_template_filters(app):
    @app.template_filter("inr")
    def format_inr(value):
        """Format a number using Indian digit grouping, e.g. 1,24,580."""
        try:
            value = float(value)
        except (TypeError, ValueError):
            return value
        is_negative = value < 0
        value = abs(value)
        whole = int(value)
        fraction = round(value - whole, 2)

        s = str(whole)
        if len(s) <= 3:
            grouped = s
        else:
            last3 = s[-3:]
            rest = s[:-3]
            parts = []
            while len(rest) > 2:
                parts.insert(0, rest[-2:])
                rest = rest[:-2]
            if rest:
                parts.insert(0, rest)
            grouped = ",".join(parts) + "," + last3

        result = f"{Config.CURRENCY_SYMBOL}{grouped}"
        if fraction:
            result += f".{int(round(fraction * 100)):02d}"
        if is_negative:
            result = "-" + result
        return result

    @app.context_processor
    def inject_globals():
        return {
            "categories": Config.CATEGORIES,
            "payment_methods": Config.PAYMENT_METHODS,
            "currency_symbol": Config.CURRENCY_SYMBOL,
            "current_year": datetime.now().year,
        }


# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------

def register_routes(app):

    # ---------------- Pages ----------------

    @app.route("/")
    def index():
        return redirect(url_for("dashboard"))

    @app.route("/dashboard")
    def dashboard():
        summary = analyzer.get_dashboard_summary()
        recent_expenses = Expense.query.order_by(Expense.date.desc(), Expense.id.desc()).limit(6).all()
        insights = ai_insights.generate_insights(limit=4)
        budget_progress = analyzer.get_budget_progress()
        return render_template(
            "dashboard.html",
            summary=summary,
            recent_expenses=recent_expenses,
            insights=insights,
            budget_progress=budget_progress[:4],
            active_page="dashboard",
        )

    @app.route("/expenses")
    def expenses():
        query = Expense.query

        search = request.args.get("search", "").strip()
        category = request.args.get("category", "")
        payment_method = request.args.get("payment_method", "")
        date_from = request.args.get("date_from", "")
        date_to = request.args.get("date_to", "")
        sort_by = request.args.get("sort_by", "date_desc")
        page = request.args.get("page", 1, type=int)

        if search:
            like = f"%{search}%"
            query = query.filter(Expense.description.ilike(like))
        if category:
            query = query.filter(Expense.category == category)
        if payment_method:
            query = query.filter(Expense.payment_method == payment_method)
        if date_from:
            query = query.filter(Expense.date >= datetime.strptime(date_from, "%Y-%m-%d").date())
        if date_to:
            query = query.filter(Expense.date <= datetime.strptime(date_to, "%Y-%m-%d").date())

        sort_map = {
            "date_desc": Expense.date.desc(),
            "date_asc": Expense.date.asc(),
            "amount_desc": Expense.amount.desc(),
            "amount_asc": Expense.amount.asc(),
        }
        query = query.order_by(sort_map.get(sort_by, Expense.date.desc()), Expense.id.desc())

        pagination = query.paginate(page=page, per_page=10, error_out=False)

        return render_template(
            "expenses.html",
            expenses=pagination.items,
            pagination=pagination,
            filters={
                "search": search,
                "category": category,
                "payment_method": payment_method,
                "date_from": date_from,
                "date_to": date_to,
                "sort_by": sort_by,
            },
            active_page="expenses",
        )

    @app.route("/add-expense", methods=["GET", "POST"])
    def add_expense():
        if request.method == "POST":
            error = _validate_expense_form(request.form)
            if error:
                flash(error, "error")
                return redirect(url_for("add_expense"))

            exp_date = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
            amount = float(request.form["amount"])
            category = request.form["category"]

            anomaly = analyzer.detect_anomaly(amount, category)

            new_expense = Expense(
                amount=amount,
                category=category,
                description=request.form["description"].strip(),
                date=exp_date,
                payment_method=request.form["payment_method"],
                notes=request.form.get("notes", "").strip(),
            )
            db.session.add(new_expense)
            db.session.commit()

            if anomaly["is_unusual"]:
                flash(f"Expense added. Heads up: {anomaly['message']}", "warning")
            else:
                flash("Expense added successfully.", "success")
            return redirect(url_for("expenses"))

        return render_template("add_expense.html", active_page="add_expense", expense=None, edit_mode=False)

    @app.route("/edit-expense/<int:expense_id>", methods=["GET", "POST"])
    def edit_expense(expense_id):
        expense = Expense.query.get_or_404(expense_id)

        if request.method == "POST":
            error = _validate_expense_form(request.form)
            if error:
                flash(error, "error")
                return redirect(url_for("edit_expense", expense_id=expense_id))

            expense.amount = float(request.form["amount"])
            expense.category = request.form["category"]
            expense.description = request.form["description"].strip()
            expense.date = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
            expense.payment_method = request.form["payment_method"]
            expense.notes = request.form.get("notes", "").strip()
            db.session.commit()
            flash("Expense updated successfully.", "success")
            return redirect(url_for("expenses"))

        return render_template("add_expense.html", active_page="expenses", expense=expense, edit_mode=True)

    @app.route("/delete-expense/<int:expense_id>", methods=["POST"])
    def delete_expense(expense_id):
        expense = Expense.query.get_or_404(expense_id)
        db.session.delete(expense)
        db.session.commit()
        flash("Expense deleted.", "success")
        return redirect(request.referrer or url_for("expenses"))

    @app.route("/analytics")
    def analytics():
        summary = analyzer.get_analytics_summary()
        anomalies = analyzer.find_all_anomalies()
        return render_template(
            "analytics.html",
            summary=summary,
            anomalies=anomalies,
            active_page="analytics",
        )

    @app.route("/budgets", methods=["GET", "POST"])
    def budgets():
        today = date.today()

        if request.method == "POST":
            form_type = request.form.get("form_type", "category")

            if form_type == "total":
                # User setting/updating their own overall monthly budget.
                amount = request.form.get("total_amount")
                try:
                    amount_val = float(amount)
                    if amount_val <= 0:
                        raise ValueError
                except (TypeError, ValueError):
                    flash("Please enter a valid positive total budget amount.", "error")
                    return redirect(url_for("budgets"))

                existing_total = TotalBudget.query.filter_by(month=today.month, year=today.year).first()
                if existing_total:
                    existing_total.amount = amount_val
                    flash("Updated your total monthly budget.", "success")
                else:
                    db.session.add(TotalBudget(month=today.month, year=today.year, amount=amount_val))
                    flash("Total monthly budget set.", "success")
                db.session.commit()
                return redirect(url_for("budgets"))

            # Otherwise: setting/updating a per-category budget.
            category = request.form.get("category")
            amount = request.form.get("amount")
            try:
                amount_val = float(amount)
                if amount_val <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                flash("Please enter a valid positive budget amount.", "error")
                return redirect(url_for("budgets"))

            existing = Budget.query.filter_by(category=category, month=today.month, year=today.year).first()
            if existing:
                existing.amount = amount_val
                flash(f"Updated budget for {category}.", "success")
            else:
                db.session.add(Budget(category=category, month=today.month, year=today.year, amount=amount_val))
                flash(f"Budget set for {category}.", "success")
            db.session.commit()
            return redirect(url_for("budgets"))

        progress = analyzer.get_budget_progress(today.month, today.year)
        budgeted_categories = {p["category"] for p in progress}
        available_categories = [c for c in Config.CATEGORIES if c not in budgeted_categories]
        total_budget_progress = analyzer.get_total_budget_progress(today.month, today.year)

        return render_template(
            "budgets.html",
            progress=progress,
            available_categories=available_categories,
            total_budget_progress=total_budget_progress,
            active_page="budgets",
        )

    @app.route("/budgets/delete/<int:budget_id>", methods=["POST"])
    def delete_budget(budget_id):
        budget = Budget.query.get_or_404(budget_id)
        db.session.delete(budget)
        db.session.commit()
        flash("Budget removed.", "success")
        return redirect(url_for("budgets"))

    @app.route("/budgets/delete-total", methods=["POST"])
    def delete_total_budget():
        today = date.today()
        total = TotalBudget.query.filter_by(month=today.month, year=today.year).first()
        if total:
            db.session.delete(total)
            db.session.commit()
            flash("Total monthly budget removed. Falling back to the sum of category budgets.", "success")
        return redirect(url_for("budgets"))

    @app.route("/reports")
    def reports():
        month = request.args.get("month", date.today().month, type=int)
        year = request.args.get("year", date.today().year, type=int)
        report = analyzer.get_monthly_report_data(month, year)
        recommendations = ai_insights.generate_recommendations()
        return render_template(
            "reports.html",
            report=report,
            recommendations=recommendations,
            active_page="reports",
        )

    @app.route("/settings", methods=["GET", "POST"])
    def settings():
        settings_row = _get_or_create_settings()

        if request.method == "POST":
            action = request.form.get("action")

            if action == "update_general":
                symbol = request.form.get("currency_symbol", "").strip()
                threshold = request.form.get("budget_alert_threshold", "")
                try:
                    threshold_val = int(threshold)
                except (TypeError, ValueError):
                    threshold_val = settings_row.budget_alert_threshold

                if not symbol:
                    flash("Please choose a currency symbol.", "error")
                elif not (1 <= threshold_val <= 100):
                    flash("Budget alert threshold must be between 1 and 100.", "error")
                else:
                    settings_row.currency_symbol = symbol
                    settings_row.budget_alert_threshold = threshold_val
                    db.session.commit()
                    _apply_settings_to_config(settings_row)
                    flash("General settings updated.", "success")

            elif action == "add_category":
                new_cat = request.form.get("new_category", "").strip()
                categories = settings_row.category_list()
                if not new_cat:
                    flash("Please enter a category name.", "error")
                elif new_cat in categories:
                    flash(f"'{new_cat}' already exists.", "error")
                else:
                    categories.append(new_cat)
                    settings_row.set_category_list(categories)
                    db.session.commit()
                    _apply_settings_to_config(settings_row)
                    flash(f"Added category '{new_cat}'.", "success")

            elif action == "delete_category":
                cat = request.form.get("category", "")
                in_use = Expense.query.filter_by(category=cat).first() is not None or \
                    Budget.query.filter_by(category=cat).first() is not None
                if in_use:
                    flash(f"Can't remove '{cat}' - it's used by existing expenses or budgets.", "error")
                else:
                    categories = [c for c in settings_row.category_list() if c != cat]
                    settings_row.set_category_list(categories)
                    db.session.commit()
                    _apply_settings_to_config(settings_row)
                    flash(f"Removed category '{cat}'.", "success")

            elif action == "add_payment_method":
                new_pm = request.form.get("new_payment_method", "").strip()
                methods = settings_row.payment_method_list()
                if not new_pm:
                    flash("Please enter a payment method name.", "error")
                elif new_pm in methods:
                    flash(f"'{new_pm}' already exists.", "error")
                else:
                    methods.append(new_pm)
                    settings_row.set_payment_method_list(methods)
                    db.session.commit()
                    _apply_settings_to_config(settings_row)
                    flash(f"Added payment method '{new_pm}'.", "success")

            elif action == "delete_payment_method":
                pm = request.form.get("payment_method", "")
                in_use = Expense.query.filter_by(payment_method=pm).first() is not None
                if in_use:
                    flash(f"Can't remove '{pm}' - it's used by existing expenses.", "error")
                else:
                    methods = [p for p in settings_row.payment_method_list() if p != pm]
                    settings_row.set_payment_method_list(methods)
                    db.session.commit()
                    _apply_settings_to_config(settings_row)
                    flash(f"Removed payment method '{pm}'.", "success")

            elif action == "update_ai_key":
                key = request.form.get("ai_api_key", "").strip()
                settings_row.ai_api_key = key
                db.session.commit()
                _apply_settings_to_config(settings_row)
                flash("AI API key updated." if key else "AI API key cleared - using built-in rule-based insights.", "success")

            elif action == "reset_data":
                Expense.query.delete()
                Budget.query.delete()
                TotalBudget.query.delete()
                db.session.commit()
                _seed_sample_data_if_empty()
                flash("All data cleared and demo data restored.", "success")

            return redirect(url_for("settings"))

        return render_template(
            "settings.html",
            settings=settings_row,
            categories=settings_row.category_list(),
            payment_methods=settings_row.payment_method_list(),
            ai_configured=bool(Config.AI_API_KEY),
            active_page="settings",
        )

    @app.route("/reports/download")
    def download_report():
        month = request.args.get("month", date.today().month, type=int)
        year = request.args.get("year", date.today().year, type=int)
        report = analyzer.get_monthly_report_data(month, year)
        recommendations = ai_insights.generate_recommendations()

        content = _build_text_report(report, recommendations)
        buffer = io.BytesIO(content.encode("utf-8"))
        filename = f"expense_report_{report['month_name'].replace(' ', '_')}.txt"
        return send_file(buffer, as_attachment=True, download_name=filename, mimetype="text/plain")

    # ---------------- CSV import/export ----------------

    @app.route("/import-csv", methods=["GET", "POST"])
    def import_csv():
        preview = None
        empty_filters = {"search": "", "category": "", "payment_method": "", "date_from": "", "date_to": "", "sort_by": "date_desc"}

        if request.method == "POST":
            # Step 2: user confirmed the preview - insert the already-validated rows.
            if request.form.get("confirm") == "1":
                import json as _json

                raw = request.form.get("valid_rows_json", "[]")
                try:
                    rows = _json.loads(raw)
                except ValueError:
                    rows = []

                total_amount = 0.0
                for row in rows:
                    row["date"] = datetime.strptime(row["date"], "%Y-%m-%d").date()
                    db.session.add(Expense(**row))
                    total_amount += row["amount"]
                db.session.commit()

                flash(
                    f"Imported {len(rows)} expense(s) totaling "
                    f"{Config.CURRENCY_SYMBOL}{total_amount:,.0f}.",
                    "success",
                )
                return redirect(url_for("expenses"))

            # Step 1: parse and validate the uploaded file, show a preview.
            file = request.files.get("csv_file")
            if not file or file.filename == "":
                flash("Please choose a CSV file to upload.", "error")
                return redirect(url_for("import_csv"))

            if not file.filename.lower().endswith(".csv"):
                flash("Only .csv files are supported.", "error")
                return redirect(url_for("import_csv"))

            filename = secure_filename(file.filename)
            result = csv_service.validate_and_parse_csv(file.stream)

            if "error" in result:
                flash(result["error"], "error")
                return redirect(url_for("import_csv"))

            import json as _json

            serializable_rows = [
                {**row, "date": row["date"].isoformat()} for row in result["valid_rows"]
            ]
            result["valid_rows_json"] = _json.dumps(serializable_rows)
            result["valid_rows"] = serializable_rows
            preview = result
            preview["filename"] = filename

        return render_template(
            "expenses.html",
            import_preview=preview,
            active_page="expenses",
            import_mode=True,
            expenses=[],
            pagination=None,
            filters=empty_filters,
        )

    @app.route("/export-csv")
    def export_csv():
        expenses_list = Expense.query.order_by(Expense.date.desc()).all()
        csv_data = csv_service.export_expenses_to_csv(expenses_list)
        buffer = io.BytesIO(csv_data.encode("utf-8"))
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"expenses_export_{date.today().isoformat()}.csv",
            mimetype="text/csv",
        )

    # ---------------- JSON APIs ----------------

    @app.route("/api/dashboard")
    def api_dashboard():
        return jsonify(
            {
                "summary": analyzer.get_dashboard_summary(),
                "monthly_trend": analyzer.get_monthly_trend(),
                "category_distribution": analyzer.get_category_distribution(month_only=True),
                "daily_spending": analyzer.get_daily_spending(days=14),
            }
        )

    @app.route("/api/analytics")
    def api_analytics():
        return jsonify(
            {
                "monthly_trend": analyzer.get_monthly_trend(months=12),
                "category_distribution": analyzer.get_category_distribution(),
                "payment_method_distribution": analyzer.get_payment_method_distribution(),
                "weekday_distribution": analyzer.get_weekday_distribution(),
                "weekly_spending": analyzer.get_weekly_spending(),
                "daily_spending": analyzer.get_daily_spending(days=30),
                "summary": analyzer.get_analytics_summary(),
            }
        )

    @app.route("/api/ai-insights")
    def api_ai_insights():
        return jsonify({"insights": ai_insights.generate_insights(limit=8)})

    @app.route("/api/notifications")
    def api_notifications():
        notifications = ai_insights.generate_notifications(limit=10)
        return jsonify({"notifications": notifications, "count": len(notifications)})

    @app.route("/api/suggest-category")
    def api_suggest_category():
        description = request.args.get("description", "")
        return jsonify({"category": analyzer.suggest_category(description)})

    @app.route("/api/check-anomaly")
    def api_check_anomaly():
        try:
            amount = float(request.args.get("amount", 0))
        except ValueError:
            amount = 0
        category = request.args.get("category", "")
        return jsonify(analyzer.detect_anomaly(amount, category))

    @app.errorhandler(404)
    def not_found(e):
        return render_template("base.html", error_message="Page not found."), 404


def _validate_expense_form(form):
    """Validate the Add/Edit expense form. Returns an error message or None."""
    amount = form.get("amount", "")
    category = form.get("category", "")
    description = form.get("description", "").strip()
    exp_date = form.get("date", "")
    payment_method = form.get("payment_method", "")

    try:
        amount_val = float(amount)
    except (TypeError, ValueError):
        return "Please enter a valid amount."

    if amount_val <= 0:
        return "Amount must be greater than zero."

    if category not in Config.CATEGORIES:
        return "Please select a valid category."

    if not description:
        return "Please enter a description."

    if payment_method not in Config.PAYMENT_METHODS:
        return "Please select a valid payment method."

    try:
        datetime.strptime(exp_date, "%Y-%m-%d")
    except (TypeError, ValueError):
        return "Please enter a valid date."

    return None


def _build_text_report(report, recommendations):
    symbol = Config.CURRENCY_SYMBOL
    lines = []
    lines.append(f"EXPENSE REPORT - {report['month_name']}")
    lines.append("=" * 50)
    lines.append("")
    lines.append(f"Total Spending: {symbol}{report['total_spending']:,.2f}")
    lines.append(f"Average Daily Spending: {symbol}{report['average_daily_spending']:,.2f}")
    lines.append(f"Total Transactions: {report['transaction_count']}")
    lines.append(f"Total Budget: {symbol}{report['total_budget']:,.2f}")
    lines.append("")
    lines.append("CATEGORY BREAKDOWN")
    lines.append("-" * 50)
    for c in report["category_breakdown"]:
        lines.append(f"{c['category']:<15} {symbol}{c['amount']:>10,.2f}   ({c['percentage']}%)")
    lines.append("")
    if report["highest_expense"]:
        h = report["highest_expense"]
        lines.append("HIGHEST EXPENSE")
        lines.append("-" * 50)
        lines.append(f"{h['category']} - {h['description']} - {symbol}{h['amount']:,.2f} on {h['date']}")
        lines.append("")
    lines.append("BUDGET STATUS")
    lines.append("-" * 50)
    for b in report["budget_status"]:
        lines.append(
            f"{b['category']:<15} spent {symbol}{b['spent']:,.2f} of {symbol}{b['budget']:,.2f} "
            f"({b['percentage']}% used, {b['status']})"
        )
    lines.append("")
    lines.append("AI RECOMMENDATIONS")
    lines.append("-" * 50)
    for r in recommendations:
        lines.append(f"- {r}")
    lines.append("")
    return "\n".join(lines)


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
