from decimal import Decimal, InvalidOperation

from django import template
from django.conf import settings
from django.contrib.humanize.templatetags.humanize import intcomma

register = template.Library()


@register.filter
def money(value, decimals=2):
    """Format a number as currency: 12345.5 -> ₹12,345.50 (negatives -> -₹12,345.50)."""
    symbol = getattr(settings, 'CURRENCY_SYMBOL', '₹')
    try:
        number = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return f'{symbol}0.00'
    decimals = int(decimals)
    sign = '-' if number < 0 else ''
    text = f'{abs(number):.{decimals}f}'
    whole, _, frac = text.partition('.')
    out = f'{symbol}{intcomma(int(whole))}'
    if frac:
        out += f'.{frac}'
    return sign + out


@register.filter
def pct(value, decimals=1):
    try:
        return f'{Decimal(value):.{int(decimals)}f}%'
    except (InvalidOperation, TypeError, ValueError):
        return '0.0%'


@register.filter
def clamp100(value):
    """Clamp a percentage to 0-100 for progress bar widths."""
    try:
        return max(0, min(100, int(Decimal(value))))
    except (InvalidOperation, TypeError, ValueError):
        return 0
