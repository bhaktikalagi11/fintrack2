"""Calculation helpers used by the dashboard, reports and budgets."""
import calendar
from collections import OrderedDict
from datetime import date
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from .models import Account, Budget, Investment, Transaction

ZERO = Decimal('0.00')
PALETTE = ['#176b4d', '#2f80ed', '#f2994a', '#9b51e0', '#eb5757',
           '#27ae60', '#f2c94c', '#56ccf2', '#bb6bd9', '#6fcf97', '#828282']


def parse_month(value):
    """'2026-11' -> date(2026, 11, 1). Falls back to the current month."""
    today = timezone.localdate()
    try:
        year, month = value.split('-')
        return date(int(year), int(month), 1)
    except (AttributeError, ValueError):
        return today.replace(day=1)


def shift_month(first_day, delta):
    index = first_day.year * 12 + (first_day.month - 1) + delta
    return date(index // 12, index % 12 + 1, 1)


def month_range(first_day):
    """Return (start, end) where end is the last day of the month."""
    last = calendar.monthrange(first_day.year, first_day.month)[1]
    return first_day, first_day.replace(day=last)


def _sum(qs):
    return qs.aggregate(t=Sum('amount'))['t'] or ZERO


def totals_between(user, start, end):
    qs = Transaction.objects.filter(user=user, date__gte=start, date__lte=end)
    income = _sum(qs.filter(kind=Transaction.INCOME))
    expense = _sum(qs.filter(kind=Transaction.EXPENSE))
    saved = income - expense
    rate = (saved / income * 100).quantize(Decimal('0.1')) if income > 0 else Decimal('0.0')
    return {'income': income, 'expense': expense, 'saved': saved, 'rate': rate}


def donut_gradient(items):
    """Build a CSS conic-gradient from [{'pct': Decimal, ...}] and annotate colours."""
    stops, cursor = [], Decimal('0')
    for index, item in enumerate(items):
        item['color'] = PALETTE[index % len(PALETTE)]
        end = cursor + item['pct']
        stops.append(f"{item['color']} {cursor:.2f}% {end:.2f}%")
        cursor = end
    return ', '.join(stops) if stops else '#e2e9e5 0% 100%'


def expense_breakdown(user, start, end):
    rows = (
        Transaction.objects.filter(
            user=user, kind=Transaction.EXPENSE, date__gte=start, date__lte=end
        )
        .values('category__name')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )
    grand = sum((r['total'] for r in rows), ZERO)
    items = [
        {
            'name': r['category__name'] or 'Uncategorised',
            'total': r['total'],
            'pct': (r['total'] / grand * 100) if grand else Decimal('0'),
        }
        for r in rows
    ]
    gradient = donut_gradient(items)
    return items, gradient, grand


def budget_status(user, start, end):
    spent_by_cat = {
        r['category']: r['total']
        for r in Transaction.objects.filter(
            user=user, kind=Transaction.EXPENSE, date__gte=start, date__lte=end
        ).values('category').annotate(total=Sum('amount'))
    }
    rows = []
    for budget in Budget.objects.filter(user=user).select_related('category'):
        spent = spent_by_cat.get(budget.category_id, ZERO)
        pct = (spent / budget.amount * 100).quantize(Decimal('1')) if budget.amount else Decimal('0')
        state = 'ok' if pct < 80 else 'warn' if pct <= 100 else 'over'
        rows.append({
            'budget': budget, 'spent': spent, 'remaining': budget.amount - spent,
            'pct': pct, 'state': state,
        })
    rows.sort(key=lambda r: r['pct'], reverse=True)
    return rows


def monthly_trend(user, end_month, months=6):
    """Income vs expense for the `months` months ending at end_month (first-of-month date)."""
    data = []
    for offset in range(months - 1, -1, -1):
        first = shift_month(end_month, -offset)
        start, end = month_range(first)
        t = totals_between(user, start, end)
        data.append({'label': first.strftime('%b %y'), **t})
    peak = max([d['income'] for d in data] + [d['expense'] for d in data] + [Decimal('1')])
    for d in data:
        d['income_h'] = int(d['income'] / peak * 100)
        d['expense_h'] = int(d['expense'] / peak * 100)
    return data


def portfolio_summary(user):
    holdings = list(Investment.objects.filter(user=user))
    invested = sum((h.invested for h in holdings), ZERO)
    value = sum((h.current_value for h in holdings), ZERO)
    gain = value - invested
    gain_pct = (gain / invested * 100).quantize(Decimal('0.1')) if invested else Decimal('0.0')

    by_type = OrderedDict()
    labels = dict(Investment.TYPES)
    for h in holdings:
        by_type.setdefault(h.asset_type, ZERO)
        by_type[h.asset_type] += h.current_value
    allocation = [
        {'name': labels[k], 'total': v, 'pct': (v / value * 100) if value else Decimal('0')}
        for k, v in sorted(by_type.items(), key=lambda kv: kv[1], reverse=True)
    ]
    gradient = donut_gradient(allocation)
    return {
        'holdings': holdings, 'invested': invested, 'value': value,
        'gain': gain, 'gain_pct': gain_pct,
        'allocation': allocation, 'gradient': gradient,
    }


def cash_total(user):
    return sum((a.balance for a in Account.objects.filter(user=user)), ZERO)
