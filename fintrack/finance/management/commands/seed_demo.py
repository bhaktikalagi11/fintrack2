import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from finance.models import (Account, Budget, Category, Goal, Investment, Transaction,
                            create_default_categories)


class Command(BaseCommand):
    help = 'Create a demo user (demo / demo12345) with sample accounts, transactions, budgets and investments.'

    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(username='demo')
        if not created:
            self.stdout.write(self.style.WARNING('Demo user already exists - nothing changed.'))
            return
        user.set_password('demo12345')
        user.save()
        create_default_categories(user)
        random.seed(7)

        bank = Account.objects.create(user=user, name='HDFC Savings', account_type=Account.SAVINGS,
                                      opening_balance=Decimal('50000'))
        cash = Account.objects.create(user=user, name='Cash', account_type=Account.CASH,
                                      opening_balance=Decimal('2000'))
        card = Account.objects.create(user=user, name='Credit Card', account_type=Account.CARD)

        cat = {c.name: c for c in Category.objects.filter(user=user, kind=Category.EXPENSE)}
        salary = Category.objects.get(user=user, name='Salary', kind=Category.INCOME)
        today = timezone.localdate()

        spend = [
            ('Rent', 15000, 1, bank), ('Utilities', 2200, 1, bank), ('Groceries', 4200, 3, card),
            ('Food & Dining', 650, 6, card), ('Transport', 900, 9, cash), ('Entertainment', 1200, 4, card),
            ('Shopping', 3000, 2, card), ('Health', 800, 1, cash),
        ]
        for months_back in range(5, -1, -1):
            index = today.year * 12 + today.month - 1 - months_back
            first = today.replace(year=index // 12, month=index % 12 + 1, day=1)
            Transaction.objects.create(user=user, account=bank, category=salary,
                                       kind=Transaction.INCOME, amount=Decimal('85000'),
                                       date=first, description='Monthly salary')
            for name, base, times, account in spend:
                for n in range(times):
                    day = min(first.day + random.randint(0, 26), 28)
                    amount = Decimal(base) * Decimal(random.uniform(0.8, 1.2)).quantize(Decimal('0.01'))
                    if name in ('Rent', 'Utilities'):
                        amount = Decimal(base)
                    date = first.replace(day=day)
                    if date > today:
                        continue
                    Transaction.objects.create(user=user, account=account, category=cat[name],
                                               kind=Transaction.EXPENSE, amount=amount.quantize(Decimal('0.01')),
                                               date=date, description=f'{name} #{n + 1}')
        Transaction.objects.create(user=user, account=bank, to_account=cash, kind=Transaction.TRANSFER,
                                   amount=Decimal('3000'), date=today - timedelta(days=2),
                                   description='ATM withdrawal')

        for name, limit in [('Food & Dining', 5000), ('Groceries', 10000), ('Shopping', 6000),
                            ('Entertainment', 3000), ('Transport', 4000)]:
            Budget.objects.create(user=user, category=cat[name], amount=Decimal(limit))

        for name, symbol, kind, qty, buy, now in [
            ('Nifty 50 Index Fund', 'NIFTYBEES', Investment.ETF, 120, 215.50, 241.30),
            ('Reliance Industries', 'RELIANCE', Investment.STOCK, 15, 2450, 2890),
            ('Parag Parikh Flexi Cap', 'PPFCF', Investment.MUTUAL_FUND, 850.25, 62.10, 78.45),
            ('Sovereign Gold Bond', 'SGB', Investment.GOLD, 10, 5900, 7450),
            ('Bank FD (7.1%)', '', Investment.FD, 1, 100000, 103550),
        ]:
            Investment.objects.create(user=user, name=name, symbol=symbol, asset_type=kind,
                                      quantity=Decimal(str(qty)), buy_price=Decimal(str(buy)),
                                      current_price=Decimal(str(now)),
                                      purchase_date=today - timedelta(days=200))

        Goal.objects.create(user=user, name='Emergency fund', target_amount=Decimal('300000'),
                            saved_amount=Decimal('120000'), target_date=today + timedelta(days=365))
        Goal.objects.create(user=user, name='Goa trip', target_amount=Decimal('40000'),
                            saved_amount=Decimal('26500'), target_date=today + timedelta(days=90))

        self.stdout.write(self.style.SUCCESS('Demo data created. Log in with demo / demo12345'))
