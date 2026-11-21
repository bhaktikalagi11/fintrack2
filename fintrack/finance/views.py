import csv
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction as db_transaction
from django.db.models import F, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from . import utils
from .forms import (AccountForm, BudgetForm, CategoryForm, ContributeForm, GoalForm,
                    InvestmentForm, RegisterForm, TransactionForm)
from .models import (Account, Budget, Category, Goal, Investment, Transaction,
                     create_default_categories)


# ---------------------------------------------------------------- helpers
def _form_page(request, form_class, *, instance=None, title, back_url, message, intro=''):
    """Shared add/edit view for every user-owned model."""
    if request.method == 'POST':
        form = form_class(request.POST, instance=instance, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, message)
            return redirect(back_url)
    else:
        form = form_class(instance=instance, user=request.user)
    return render(request, 'form.html', {
        'form': form, 'page_title': title, 'back_url': back_url, 'intro': intro,
        'submit_label': 'Save changes' if instance else 'Save',
    })


def _delete_page(request, obj, *, back_url, label, warning=''):
    """Shared confirm-and-delete view (GET shows the page, POST deletes)."""
    if request.method == 'POST':
        obj.delete()
        messages.success(request, f'{label} deleted.')
        return redirect(back_url)
    return render(request, 'confirm_delete.html', {
        'object': obj, 'label': label, 'back_url': back_url, 'warning': warning,
    })


# ---------------------------------------------------------------- auth
def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            create_default_categories(user)
            Account.objects.create(user=user, name='Cash', account_type=Account.CASH)
            login(request, user)
            messages.success(request, 'Welcome to FinTrack! Add your first account or transaction.')
            return redirect('dashboard')
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})


def user_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST.get('username'),
            password=request.POST.get('password'),
        )
        if user is not None:
            login(request, user)
            target = request.GET.get('next', '')
            if target and url_has_allowed_host_and_scheme(target, {request.get_host()}):
                return redirect(target)
            return redirect('dashboard')
        messages.error(request, 'Invalid credentials')
    return render(request, 'login.html')


@require_POST
def user_logout(request):
    logout(request)
    return redirect('login')


def not_found(request, exception):
    return render(request, '404.html', status=404)


# ---------------------------------------------------------------- dashboard
@login_required
def dashboard(request):
    user = request.user
    month = utils.parse_month(request.GET.get('month'))
    start, end = utils.month_range(month)

    summary = utils.totals_between(user, start, end)
    breakdown, gradient, _ = utils.expense_breakdown(user, start, end)
    portfolio = utils.portfolio_summary(user)
    cash = utils.cash_total(user)

    recent = Transaction.objects.filter(user=user).select_related('account', 'category')[:6]
    goals = Goal.objects.filter(user=user)[:3]

    return render(request, 'dashboard.html', {
        'month': month,
        'prev_month': utils.shift_month(month, -1).strftime('%Y-%m'),
        'next_month': utils.shift_month(month, 1).strftime('%Y-%m'),
        'is_current': month == timezone.localdate().replace(day=1),
        'summary': summary,
        'breakdown': breakdown[:6],
        'gradient': gradient,
        'budgets': utils.budget_status(user, start, end)[:5],
        'portfolio': portfolio,
        'cash': cash,
        'net_worth': cash + portfolio['value'],
        'recent': recent,
        'goals': goals,
        'has_accounts': Account.objects.filter(user=user).exists(),
    })


# ---------------------------------------------------------------- transactions
def _safe_date(value):
    try:
        return parse_date(value or '')
    except ValueError:
        return None


def _filtered_transactions(request):
    qs = Transaction.objects.filter(user=request.user).select_related(
        'account', 'to_account', 'category'
    )
    g = request.GET
    if g.get('q'):
        qs = qs.filter(Q(description__icontains=g['q']) | Q(category__name__icontains=g['q']))
    if g.get('kind') in dict(Transaction.KINDS):
        qs = qs.filter(kind=g['kind'])
    if g.get('account', '').isdigit():
        qs = qs.filter(Q(account_id=g['account']) | Q(to_account_id=g['account']))
    if g.get('category', '').isdigit():
        qs = qs.filter(category_id=g['category'])
    start, end = _safe_date(g.get('start')), _safe_date(g.get('end'))
    if start:
        qs = qs.filter(date__gte=start)
    if end:
        qs = qs.filter(date__lte=end)
    return qs


@login_required
def transactions(request):
    qs = _filtered_transactions(request)
    page = Paginator(qs, 20).get_page(request.GET.get('page'))
    params = request.GET.copy()
    params.pop('page', None)
    return render(request, 'transactions.html', {
        'page': page,
        'accounts': Account.objects.filter(user=request.user),
        'categories': Category.objects.filter(user=request.user),
        'filters': request.GET,
        'querystring': params.urlencode(),
        'kinds': Transaction.KINDS,
    })


@login_required
def add_transaction(request):
    initial_kind = request.GET.get('kind')
    if request.method == 'POST':
        form = TransactionForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Transaction saved.')
            return redirect('transactions')
    else:
        initial = {'kind': initial_kind} if initial_kind in dict(Transaction.KINDS) else {}
        form = TransactionForm(user=request.user, initial=initial)
    return render(request, 'form.html', {
        'form': form, 'page_title': 'Add a transaction', 'back_url': 'transactions',
        'submit_label': 'Save', 'intro': 'Record income, an expense, or a transfer between accounts.',
    })


@login_required
def update_transaction(request, id):
    obj = get_object_or_404(Transaction, id=id, user=request.user)
    return _form_page(request, TransactionForm, instance=obj, title='Edit transaction',
                      back_url='transactions', message='Transaction updated.')


@login_required
def delete_transaction(request, id):
    obj = get_object_or_404(Transaction, id=id, user=request.user)
    return _delete_page(request, obj, back_url='transactions', label='Transaction')


@login_required
def export_transactions(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="transactions.csv"'
    writer = csv.writer(response)
    writer.writerow(['Date', 'Type', 'Amount', 'Account', 'To account', 'Category', 'Description'])
    for t in _filtered_transactions(request):
        writer.writerow([
            t.date.isoformat(), t.kind, t.amount, t.account.name,
            t.to_account.name if t.to_account else '',
            t.category.name if t.category else '', t.description,
        ])
    return response


# ---------------------------------------------------------------- accounts
@login_required
def accounts(request):
    rows = [{'account': a, 'balance': a.balance} for a in Account.objects.filter(user=request.user)]
    return render(request, 'accounts.html', {
        'rows': rows, 'total': sum((r['balance'] for r in rows), Decimal('0.00')),
    })


@login_required
def add_account(request):
    return _form_page(request, AccountForm, title='Add an account', back_url='accounts',
                      message='Account added.',
                      intro='Bank accounts, cash, cards and wallets all live here.')


@login_required
def update_account(request, id):
    obj = get_object_or_404(Account, id=id, user=request.user)
    return _form_page(request, AccountForm, instance=obj, title=f'Edit {obj.name}',
                      back_url='accounts', message='Account updated.')


@login_required
def delete_account(request, id):
    obj = get_object_or_404(Account, id=id, user=request.user)
    return _delete_page(
        request, obj, back_url='accounts', label='Account',
        warning='All transactions in this account (and transfers into it) will be deleted too.',
    )


# ---------------------------------------------------------------- categories
@login_required
def categories(request):
    cats = Category.objects.filter(user=request.user)
    return render(request, 'categories.html', {
        'income': cats.filter(kind=Category.INCOME),
        'expense': cats.filter(kind=Category.EXPENSE),
    })


@login_required
def add_category(request):
    return _form_page(request, CategoryForm, title='Add a category', back_url='categories',
                      message='Category added.')


@login_required
def update_category(request, id):
    obj = get_object_or_404(Category, id=id, user=request.user)
    return _form_page(request, CategoryForm, instance=obj, title=f'Edit {obj.name}',
                      back_url='categories', message='Category updated.')


@login_required
def delete_category(request, id):
    obj = get_object_or_404(Category, id=id, user=request.user)
    return _delete_page(
        request, obj, back_url='categories', label='Category',
        warning='Transactions using it stay, but become uncategorised. Its budget is removed.',
    )


# ---------------------------------------------------------------- budgets
@login_required
def budgets(request):
    month = utils.parse_month(request.GET.get('month'))
    start, end = utils.month_range(month)
    rows = utils.budget_status(request.user, start, end)
    total_budget = sum((r['budget'].amount for r in rows), Decimal('0.00'))
    total_spent = sum((r['spent'] for r in rows), Decimal('0.00'))
    return render(request, 'budgets.html', {
        'rows': rows, 'month': month,
        'prev_month': utils.shift_month(month, -1).strftime('%Y-%m'),
        'next_month': utils.shift_month(month, 1).strftime('%Y-%m'),
        'total_budget': total_budget, 'total_spent': total_spent,
    })


@login_required
def add_budget(request):
    return _form_page(request, BudgetForm, title='Set a budget', back_url='budgets',
                      message='Budget saved.',
                      intro='Set a monthly spending limit for an expense category.')


@login_required
def update_budget(request, id):
    obj = get_object_or_404(Budget, id=id, user=request.user)
    return _form_page(request, BudgetForm, instance=obj, title=f'Edit {obj.category.name} budget',
                      back_url='budgets', message='Budget updated.')


@login_required
def delete_budget(request, id):
    obj = get_object_or_404(Budget, id=id, user=request.user)
    return _delete_page(request, obj, back_url='budgets', label='Budget')


# ---------------------------------------------------------------- investments
@login_required
def investments(request):
    portfolio = utils.portfolio_summary(request.user)
    return render(request, 'investments.html', {'portfolio': portfolio})


@login_required
def add_investment(request):
    return _form_page(request, InvestmentForm, title='Add an investment',
                      back_url='investments', message='Investment added.',
                      intro='Track stocks, funds, gold, deposits and more. '
                            'Update the current price whenever you like.')


@login_required
def update_investment(request, id):
    obj = get_object_or_404(Investment, id=id, user=request.user)
    return _form_page(request, InvestmentForm, instance=obj, title=f'Edit {obj.name}',
                      back_url='investments', message='Investment updated.')


@login_required
@require_POST
def update_price(request, id):
    obj = get_object_or_404(Investment, id=id, user=request.user)
    try:
        price = Decimal(request.POST.get('current_price', ''))
        if price < 0:
            raise ValueError
    except Exception:
        messages.error(request, 'Enter a valid price.')
    else:
        obj.current_price = price
        obj.save(update_fields=['current_price', 'updated_at'])
        messages.success(request, f'Updated price for {obj.name}.')
    return redirect('investments')


@login_required
def delete_investment(request, id):
    obj = get_object_or_404(Investment, id=id, user=request.user)
    return _delete_page(request, obj, back_url='investments', label='Investment')


# ---------------------------------------------------------------- goals
@login_required
def goals(request):
    return render(request, 'goals.html', {
        'goals': Goal.objects.filter(user=request.user),
        'form': ContributeForm(),
    })


@login_required
def add_goal(request):
    return _form_page(request, GoalForm, title='Create a savings goal', back_url='goals',
                      message='Goal created.',
                      intro='An emergency fund, a trip, a new laptop - whatever you are saving for.')


@login_required
def update_goal(request, id):
    obj = get_object_or_404(Goal, id=id, user=request.user)
    return _form_page(request, GoalForm, instance=obj, title=f'Edit {obj.name}',
                      back_url='goals', message='Goal updated.')


@login_required
@require_POST
def contribute_goal(request, id):
    form = ContributeForm(request.POST)
    if form.is_valid():
        with db_transaction.atomic():
            goal = get_object_or_404(Goal.objects.select_for_update(), id=id, user=request.user)
            goal.saved_amount = F('saved_amount') + form.cleaned_data['amount']
            goal.save(update_fields=['saved_amount'])
        messages.success(request, 'Contribution added.')
    else:
        get_object_or_404(Goal, id=id, user=request.user)
        messages.error(request, 'Enter a valid amount.')
    return redirect('goals')


@login_required
def delete_goal(request, id):
    obj = get_object_or_404(Goal, id=id, user=request.user)
    return _delete_page(request, obj, back_url='goals', label='Goal')


# ---------------------------------------------------------------- reports
@login_required
def reports(request):
    user = request.user
    month = utils.parse_month(request.GET.get('month'))
    trend = utils.monthly_trend(user, month, months=12)
    year_start = month.replace(month=1)
    year_end = month.replace(month=12, day=31)
    breakdown, gradient, grand = utils.expense_breakdown(user, year_start, year_end)
    year_totals = utils.totals_between(user, year_start, year_end)
    return render(request, 'reports.html', {
        'month': month, 'trend': trend, 'breakdown': breakdown, 'gradient': gradient,
        'year': month.year, 'year_totals': year_totals, 'expense_total': grand,
        'portfolio': utils.portfolio_summary(user),
    })
