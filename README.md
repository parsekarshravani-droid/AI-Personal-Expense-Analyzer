# SpendWise AI — Personal Expense Analyzer

A modern, fintech-style personal expense tracker with AI-powered (rule-based)
financial insights, budget tracking, analytics, and CSV import/export.
Built entirely in Python with Flask, SQLAlchemy, Pandas and Chart.js.

![Status](https://img.shields.io/badge/status-ready--to--run-brightgreen)

---

## 1. Overview

SpendWise AI helps you record, analyze, and understand your personal spending.
It ships with realistic demo data (in Indian Rupees) so the dashboard is
fully populated the first time you run it, and every insight, chart, and
report is generated dynamically from the data in your local SQLite database
— nothing is hard-coded.

The AI layer is **fully rule-based by default** and requires no external API
key or internet connection. An optional `AI_API_KEY` slot exists in `.env`
for anyone who wants to layer an external LLM on top later, but the app is
100% functional without it.

---

## 2. Features

- **Dashboard** — total/month/today spend, average daily spend, highest
  category, remaining budget, transaction count, monthly trend line chart,
  category doughnut chart, daily spending bar chart, recent transactions,
  AI insights, and budget progress bars.
- **Add Expense** — validated form with amount, category, description, date,
  payment method, and notes. Includes **smart category suggestion** based on
  the description you type, and **real-time anomaly detection** that warns
  you when an entry looks unusually large for that category.
- **Expense Management** — searchable, filterable (category, payment method,
  date range), sortable (date/amount), paginated table with edit/delete.
- **Budgets** — set monthly budgets per category, see spent/remaining and a
  color-coded progress bar (green under 70%, orange 70–90%, red above 90%),
  with contextual alerts.
- **AI Insights** — dynamically generated observations: month-over-month
  category changes, top spending category, budget alerts, savings
  opportunities, weekend-vs-weekday patterns, and recurring expenses.
- **Analytics** — 12-month trend, category & payment-method distribution,
  weekday/weekly/daily breakdowns, highest expense, average transaction,
  and a table of statistically unusual expenses.
- **CSV Import** — upload a CSV, see a validation preview (valid/invalid
  row counts and total amount) before committing the import.
- **CSV Export** — one-click export of all expenses to a CSV file.
- **Reports** — month-by-month report with category breakdown, budget
  status, highest expense, and AI recommendations, downloadable as a
  text file.
- **Responsive, premium UI** — collapsible sidebar on mobile, single-column
  cards, horizontally scrollable tables, and charts that resize automatically.

---

## 3. Technology Stack

| Layer          | Technology                              |
|----------------|------------------------------------------|
| Backend        | Python 3.11+, Flask                      |
| Database       | SQLite via SQLAlchemy (Flask-SQLAlchemy) |
| Data analysis  | Pandas, NumPy                            |
| Frontend       | HTML5, CSS3 (custom design system), vanilla JavaScript |
| Charts         | Chart.js                                 |
| Icons          | Lucide Icons                             |
| Config         | python-dotenv                            |

---

## 4. Folder Structure

```
AI-Personal-Expense-Analyzer/
│
├── app.py                     # Flask app factory + all routes
├── config.py                  # Central configuration (env vars, categories, etc.)
├── requirements.txt
├── README.md
├── .env.example
│
├── database/
│   └── expense.db             # Created automatically on first run
│
├── models/
│   ├── __init__.py             # Shared SQLAlchemy `db` instance
│   └── expense.py             # Expense and Budget ORM models
│
├── services/
│   ├── __init__.py
│   ├── expense_analyzer.py    # Pandas/NumPy-based analytics, classification, anomaly detection
│   ├── ai_insights.py         # Rule-based AI insight & recommendation generation
│   └── csv_service.py         # CSV import validation and export
│
├── templates/
│   ├── base.html              # Sidebar, topbar, toasts, shared layout
│   ├── dashboard.html
│   ├── expenses.html
│   ├── add_expense.html
│   ├── analytics.html
│   ├── budgets.html
│   └── reports.html
│
├── static/
│   ├── css/style.css
│   ├── js/
│   │   ├── app.js             # Sidebar toggle, toasts, global search
│   │   ├── dashboard.js       # Dashboard Chart.js rendering
│   │   └── analytics.js       # Analytics Chart.js rendering
│   └── images/
│
└── uploads/                   # Temporary storage for CSV uploads
```

---

## 5. Installation (Windows + VS Code)

### Prerequisites
- Python 3.11 or newer installed and available on your PATH
- VS Code (recommended) with the Python extension

### Step-by-step

1. **Open the project folder in VS Code**
   `File > Open Folder...` and select `AI-Personal-Expense-Analyzer`.

2. **Open a terminal in VS Code** (`` Ctrl+` ``) and create a virtual environment:

   ```
   python -m venv venv
   ```

3. **Activate the virtual environment:**

   ```
   venv\Scripts\activate
   ```

   You should see `(venv)` appear at the start of your terminal prompt.

4. **Install dependencies:**

   ```
   pip install -r requirements.txt
   ```

5. **(Optional) Create your own environment file:**

   Copy `.env.example` to `.env` and edit values if you want to change the
   secret key or (optionally) add an external AI API key. This step can be
   skipped entirely — the app works with sensible defaults.

6. **Run the application:**

   ```
   python app.py
   ```

7. **Open your browser** and go to:

   ```
   http://127.0.0.1:5000
   ```

The SQLite database (`database/expense.db`) and sample Indian-Rupee demo
data are created automatically the first time you run the app.

---

## 6. Database Setup

No manual setup is required. On startup, `app.py`:

1. Creates the `database/` folder if it doesn't exist.
2. Calls `db.create_all()` to create the `expenses` and `budgets` tables.
3. If the `expenses` table is empty, seeds it with ~40 realistic sample
   transactions spread across several months (so charts have meaningful
   data), plus starter budgets for common categories.

To reset the app to a clean state, simply stop the server and delete
`database/expense.db`, then run `python app.py` again.

---

## 7. How to Import CSV

1. Go to **Expenses > Import CSV**.
2. Choose a `.csv` file with these columns (header row required):
   `date, amount, category, description, payment_method` (an optional
   `notes` column is also supported).
3. Click **Preview Import** — you'll see how many rows are valid vs.
   invalid, and the total amount that will be imported.
4. Click **Confirm Import** to commit the valid rows to your database.

Invalid rows (bad dates, non-positive amounts, missing fields) are skipped
and listed with the reason, so nothing bad silently corrupts your data.

## 8. How to Export CSV

Go to **Expenses** and click **Export CSV** — this downloads every expense
in your database as a CSV file you can open in Excel or re-import elsewhere.

---

## 9. How AI Insights Work

All insights are computed **locally, from your actual data**, using Pandas:

- Category totals for the current and previous month are compared to
  detect significant increases ("Spending Alert") or decreases
  ("Positive Habit").
- The category with the highest spend this month is surfaced as the
  "Top Category" insight.
- Budget progress (spend ÷ budget) is checked against 80%+ thresholds
  for "Budget Alert" insights.
- Discretionary categories (Food, Shopping, Entertainment) are used to
  estimate a realistic "Saving Opportunity" (20% reduction scenario).
- Weekend spending as a share of the month is used for weekly-limit
  recommendations.
- Repeated identical descriptions are flagged as "Recurring Expense"
  candidates.
- Unusual expense detection uses a simple statistical rule
  (mean + 2 standard deviations per category) via NumPy/Pandas.

If you add an `AI_API_KEY` in `.env`, the application detects it
(`ai_insights.is_external_ai_configured()`) but **all current functionality
runs fully offline** — the key is reserved for anyone who wants to extend
`ai_insights.py` to call an external LLM for more natural phrasing on top
of these same, real, locally-computed findings.

---

## 10. Currency

All amounts are displayed in Indian Rupees (₹) using Indian digit grouping
(e.g. ₹1,24,580) via a custom `inr` Jinja filter defined in `app.py`.

---

## 11. Screenshots

_Add your own screenshots here after running the app locally:_

- `docs/screenshot-dashboard.png`
- `docs/screenshot-analytics.png`
- `docs/screenshot-budgets.png`

---

## 12. Troubleshooting

- **Port already in use** — another process is using port 5000. Stop it,
  or change the port in the last line of `app.py`
  (`app.run(..., port=5000)`).
- **`ModuleNotFoundError`** — make sure the virtual environment is
  activated (`venv\Scripts\activate`) before running `pip install` and
  `python app.py`.
- **Database looks stale/empty** — delete `database/expense.db` and
  restart the app to regenerate fresh sample data.

---

Built with Python, Flask, and a genuine appreciation for well-organized
spreadsheets.
