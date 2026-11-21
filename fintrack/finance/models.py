from decimal import Decimal

from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum
from django.utils import timezone

MONEY = dict(max_digits=14, decimal_places=2)
POSITIVE = [MinValueValidator(Decimal('0.01'))]


# ACCOUNT MODEL (bank, cash, card, wallet...)
class Account(models.Model):
    BANK = 'bank'
    CASH = 'cash'
    CARD = 'card'
    WALLET = 'wallet'
    SAVINGS = 'savings'
    TYPES = [
        (BANK, 'Bank account'),
        (SAVINGS, 'Savings account'),
        (CASH, 'Cash'),
        (CARD, 'Credit card'),
        (WALLET, 'Digital wallet'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accounts')
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=TYPES, default=BANK)
    opening_balance = models.DecimalField(default=Decimal('0.00'), **MONEY)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        unique_together = [('user', 'name')]

    def __str__(self):
        return self.name

    @property
    def balance(self):
        """Opening balance + income - expenses + transfers in - transfers out."""
        def total(qs):
            return qs.aggregate(t=Sum('amount'))['t'] or Decimal('0.00')

        own = self.transactions.all()
        incoming = Transaction.objects.filter(to_account=self, kind=Transaction.TRANSFER)
        return (
            self.opening_balance
            + total(own.filter(kind=Transaction.INCOME))
            - total(own.filter(kind=Transaction.EXPENSE))
            - total(own.filter(kind=Transaction.TRANSFER))
            + total(incoming)
        )


# CATEGORY MODEL
class Category(models.Model):
    INCOME = 'income'
    EXPENSE = 'expense'
    KINDS = [(INCOME, 'Income'), (EXPENSE, 'Expense')]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=80)
    kind = models.CharField(max_length=10, choices=KINDS, default=EXPENSE)

    class Meta:
        ordering = ['kind', 'name']
        unique_together = [('user', 'name', 'kind')]
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name


# TRANSACTION MODEL
class Transaction(models.Model):
    INCOME = 'income'
    EXPENSE = 'expense'
    TRANSFER = 'transfer'
    KINDS = [(INCOME, 'Income'), (EXPENSE, 'Expense'), (TRANSFER, 'Transfer')]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transactions')
    to_account = models.ForeignKey(
        Account, on_delete=models.CASCADE, null=True, blank=True,
        related_name='incoming_transfers',
        help_text='Only for transfers: the account the money moves to.',
    )
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    kind = models.CharField(max_length=10, choices=KINDS, default=EXPENSE)
    amount = models.DecimalField(validators=POSITIVE, **MONEY)
    date = models.DateField(default=timezone.localdate)
    description = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-id']

    def __str__(self):
        return f'{self.get_kind_display()} {self.amount} on {self.date}'


# BUDGET MODEL (monthly limit per expense category)
class Budget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budgets')
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, limit_choices_to={'kind': Category.EXPENSE}
    )
    amount = models.DecimalField(
        'monthly limit', validators=POSITIVE, **MONEY
    )

    class Meta:
        ordering = ['category__name']
        unique_together = [('user', 'category')]

    def __str__(self):
        return f'{self.category.name}: {self.amount}/month'


# INVESTMENT MODEL
class Investment(models.Model):
    STOCK = 'stock'
    MUTUAL_FUND = 'mutual_fund'
    ETF = 'etf'
    BOND = 'bond'
    FD = 'fd'
    GOLD = 'gold'
    CRYPTO = 'crypto'
    REAL_ESTATE = 'real_estate'
    PPF = 'ppf'
    OTHER = 'other'
    TYPES = [
        (STOCK, 'Stock'),
        (MUTUAL_FUND, 'Mutual fund'),
        (ETF, 'ETF'),
        (BOND, 'Bond'),
        (FD, 'Fixed deposit'),
        (GOLD, 'Gold'),
        (CRYPTO, 'Crypto'),
        (REAL_ESTATE, 'Real estate'),
        (PPF, 'PPF / EPF / NPS'),
        (OTHER, 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='investments')
    name = models.CharField(max_length=150)
    symbol = models.CharField('ticker / code', max_length=30, blank=True)
    asset_type = models.CharField(max_length=20, choices=TYPES, default=STOCK)
    quantity = models.DecimalField(
        'units', max_digits=16, decimal_places=4, default=Decimal('1'),
        validators=[MinValueValidator(Decimal('0.0001'))],
    )
    buy_price = models.DecimalField('average buy price per unit', max_digits=14, decimal_places=4,
                                    validators=[MinValueValidator(Decimal('0'))])
    current_price = models.DecimalField('current price per unit', max_digits=14, decimal_places=4,
                                        validators=[MinValueValidator(Decimal('0'))])
    purchase_date = models.DateField(default=timezone.localdate)
    notes = models.CharField(max_length=200, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def invested(self):
        return (self.quantity * self.buy_price).quantize(Decimal('0.01'))

    @property
    def current_value(self):
        return (self.quantity * self.current_price).quantize(Decimal('0.01'))

    @property
    def gain(self):
        return self.current_value - self.invested

    @property
    def gain_pct(self):
        if not self.invested:
            return Decimal('0.0')
        return (self.gain / self.invested * 100).quantize(Decimal('0.1'))


# SAVINGS GOAL MODEL
class Goal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='goals')
    name = models.CharField(max_length=120)
    target_amount = models.DecimalField(validators=POSITIVE, **MONEY)
    saved_amount = models.DecimalField(default=Decimal('0.00'), **MONEY)
    target_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['target_date', 'name']

    def __str__(self):
        return self.name

    @property
    def progress(self):
        if not self.target_amount:
            return Decimal('0')
        return (self.saved_amount / self.target_amount * 100).quantize(Decimal('0.1'))

    @property
    def remaining(self):
        return max(self.target_amount - self.saved_amount, Decimal('0.00'))


DEFAULT_EXPENSE_CATEGORIES = [
    'Food & Dining', 'Groceries', 'Rent', 'Utilities', 'Transport', 'Shopping',
    'Health', 'Entertainment', 'Education', 'Travel', 'Insurance', 'EMI / Loans', 'Other',
]
DEFAULT_INCOME_CATEGORIES = ['Salary', 'Business', 'Interest', 'Dividends', 'Gifts', 'Other']


def create_default_categories(user):
    """Give a new user a sensible starting set of categories."""
    existing = set(Category.objects.filter(user=user).values_list('name', 'kind'))
    new = []
    for name in DEFAULT_EXPENSE_CATEGORIES:
        if (name, Category.EXPENSE) not in existing:
            new.append(Category(user=user, name=name, kind=Category.EXPENSE))
    for name in DEFAULT_INCOME_CATEGORIES:
        if (name, Category.INCOME) not in existing:
            new.append(Category(user=user, name=name, kind=Category.INCOME))
    Category.objects.bulk_create(new)
