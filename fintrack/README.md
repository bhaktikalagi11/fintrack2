# FinTrack - Personal Finance Manager

A Django app for tracking your money: accounts, income and spending, budgets,
investments and savings goals. Built with the same structure and styling as the
`django-fs-ecom` reference project (Django 4.2, SQLite, function-based views,
app-level templates, `₹` currency).

## Features

- **Accounts** - bank, savings, cash, credit card and wallet balances, calculated live
- **Transactions** - income, expenses and transfers between accounts; search, filters, pagination, CSV export
- **Categories** - starter set created on sign-up; add, rename or remove your own
- **Budgets** - monthly limit per expense category with green / amber / red progress bars
- **Investments** - stocks, funds, ETFs, gold, FDs, crypto and more with P&L, return % and allocation chart
- **Goals** - savings goals with progress and quick contributions
- **Dashboard and reports** - net worth, monthly cash flow, savings rate, spending breakdown, 12-month trend
- Every record belongs to a user; nobody can see or edit anyone else's data

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python manage.py makemigrations finance   # safe to run; does nothing if already up to date
python manage.py migrate
python manage.py seed_demo                 # optional: demo / demo12345 with sample data
python manage.py createsuperuser           # optional: for /admin/
python manage.py runserver
```

Open http://127.0.0.1:8000/ and register (or log in as `demo`).

## Run the tests

```bash
python manage.py test
```

## Project layout

```
config/                 project settings and root urls
finance/
  models.py             Account, Category, Transaction, Budget, Investment, Goal
  forms.py              user-scoped model forms with validation
  views.py              function-based views
  utils.py              dashboard / budget / portfolio calculations
  templates/            base.html + one template per page
  management/commands/  seed_demo
  tests.py
```

## Notes

- Investment prices are entered by hand (use "Set" on the Investments page). Live market prices would need an external API.
- Change `CURRENCY_SYMBOL` in `config/settings.py` to switch currency.
- Before deploying: set a real `SECRET_KEY`, `DEBUG = False` and `ALLOWED_HOSTS`.
