# Expense Tracker (Streamlit + SQLite)

A modern, resume-ready expense tracker built with Streamlit and SQLite. Includes authentication, dashboards, budgets, and CSV import/export.

## Features

- Authentication with hashed passwords
- Add, edit, delete transactions (expense/income)
- Powerful filters (date range, category, type)
- Dashboard with KPIs and Plotly charts
- Monthly budgets (overall and per category) with progress bars
- CSV import and export

## Setup

```bash
# Create/activate a virtual environment (recommended)
python -m venv .venv
. .venv/Scripts/activate   # on Windows PowerShell

# Install dependencies
pip install -r requirements.txt

# Run the app (multi-page)
streamlit run Home.py
```

The database file `expense_tracker.db` will be created automatically in the project root. A dark theme is configured in `.streamlit/config.toml`.

## CSV Import Format

Required columns: `date` (YYYY-MM-DD), `amount`, `type` (Expense/Income)
Optional columns: `category`, `description`, `payment_method`, `tags`

## Notes

- Authentication is handled fully on the server using Passlib (bcrypt).
- Budgets are tracked by month (`YYYY-MM`) and optionally per category.
- You can change the database location by setting the environment variable `EXPENSE_TRACKER_DB`.

