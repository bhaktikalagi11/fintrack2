from django.conf import settings


def currency(request):
    return {'CURRENCY': getattr(settings, 'CURRENCY_SYMBOL', '₹')}
