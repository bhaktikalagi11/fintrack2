from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import (Account, Budget, Category, Goal, Investment, Transaction,
                     create_default_categories)


class FinanceBase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='test-password')
        create_default_categories(self.user)
        self.bank = Account.objects.create(user=self.user, name='Bank', opening_balance=Decimal('1000'))
        self.cash = Account.objects.create(user=self.user, name='Cash')
        self.food = Category.objects.get(user=self.user, name='Food & Dining')
        self.salary = Category.objects.get(user=self.user, name='Salary')
        self.client.force_login(self.user)


class ModelTests(FinanceBase):
    def test_account_balance_includes_income_expense_and_transfers(self):
        today = timezone.localdate()
        Transaction.objects.create(user=self.user, account=self.bank, kind='income',
                                   category=self.salary, amount=500, date=today)
        Transaction.objects.create(user=self.user, account=self.bank, kind='expense',
                                   category=self.food, amount=200, date=today)
        Transaction.objects.create(user=self.user, account=self.bank, to_account=self.cash,
                                   kind='transfer', amount=100, date=today)
        self.assertEqual(self.bank.balance, Decimal('1200.00'))
        self.assertEqual(self.cash.balance, Decimal('100.00'))

    def test_investment_gain_calculations(self):
        inv = Investment.objects.create(user=self.user, name='Fund', quantity=Decimal('10'),
                                        buy_price=Decimal('100'), current_price=Decimal('125'))
        self.assertEqual(inv.invested, Decimal('1000.00'))
        self.assertEqual(inv.current_value, Decimal('1250.00'))
        self.assertEqual(inv.gain, Decimal('250.00'))
        self.assertEqual(inv.gain_pct, Decimal('25.0'))

    def test_goal_progress(self):
        goal = Goal.objects.create(user=self.user, name='Trip', target_amount=1000, saved_amount=250)
        self.assertEqual(goal.progress, Decimal('25.0'))
        self.assertEqual(goal.remaining, Decimal('750'))


class PageTests(FinanceBase):
    def test_login_required_redirects_anonymous_users(self):
        self.client.logout()
        for name in ['dashboard', 'transactions', 'accounts', 'budgets', 'investments', 'goals', 'reports']:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302, name)
            self.assertIn('/login/', response['Location'])

    def test_all_pages_render_for_logged_in_user(self):
        for name in ['dashboard', 'transactions', 'accounts', 'categories', 'budgets', 'investments',
                     'goals', 'reports', 'add_transaction', 'add_account', 'add_category',
                     'add_budget', 'add_investment', 'add_goal']:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200, name)

    def test_register_creates_starter_data_and_logs_in(self):
        self.client.logout()
        response = self.client.post(reverse('register'), {
            'username': 'bob', 'password1': 'S3cure-pass-987', 'password2': 'S3cure-pass-987',
        })
        self.assertRedirects(response, reverse('dashboard'))
        bob = User.objects.get(username='bob')
        self.assertTrue(Category.objects.filter(user=bob).exists())
        self.assertTrue(Account.objects.filter(user=bob, name='Cash').exists())

    def test_custom_not_found_page_is_rendered(self):
        with override_settings(DEBUG=False):
            response = self.client.get('/this-page-does-not-exist/')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "We couldn't find that page", status_code=404)

    def test_logout_requires_post(self):
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.client.post(reverse('logout'))
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 302)


class TransactionTests(FinanceBase):
    def test_add_expense(self):
        response = self.client.post(reverse('add_transaction'), {
            'kind': 'expense', 'amount': '49.99', 'date': '2026-11-01',
            'account': self.bank.id, 'category': self.food.id, 'description': 'Lunch',
        })
        self.assertRedirects(response, reverse('transactions'))
        t = Transaction.objects.get()
        self.assertEqual(t.user, self.user)
        self.assertEqual(t.amount, Decimal('49.99'))

    def test_transfer_requires_different_destination(self):
        response = self.client.post(reverse('add_transaction'), {
            'kind': 'transfer', 'amount': '10', 'date': '2026-11-01',
            'account': self.bank.id, 'to_account': self.bank.id,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_category_must_match_transaction_type(self):
        response = self.client.post(reverse('add_transaction'), {
            'kind': 'expense', 'amount': '10', 'date': '2026-11-01',
            'account': self.bank.id, 'category': self.salary.id,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_amount_must_be_positive(self):
        response = self.client.post(reverse('add_transaction'), {
            'kind': 'expense', 'amount': '-5', 'date': '2026-11-01', 'account': self.bank.id,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_filtering_and_csv_export(self):
        Transaction.objects.create(user=self.user, account=self.bank, kind='expense',
                                   category=self.food, amount=20, description='Pizza night')
        Transaction.objects.create(user=self.user, account=self.bank, kind='income',
                                   category=self.salary, amount=900, description='Pay')
        response = self.client.get(reverse('transactions'), {'q': 'pizza'})
        self.assertContains(response, 'Pizza night')
        self.assertNotContains(response, 'Pay</span>')
        export = self.client.get(reverse('export_transactions'), {'kind': 'income'})
        self.assertEqual(export['Content-Type'], 'text/csv')
        self.assertIn('Pay', export.content.decode())
        self.assertNotIn('Pizza', export.content.decode())

    def test_delete_requires_post_confirmation(self):
        t = Transaction.objects.create(user=self.user, account=self.bank, kind='expense', amount=5)
        self.client.get(reverse('delete_transaction', args=[t.id]))
        self.assertTrue(Transaction.objects.filter(id=t.id).exists())
        self.client.post(reverse('delete_transaction', args=[t.id]))
        self.assertFalse(Transaction.objects.filter(id=t.id).exists())


class PrivacyTests(FinanceBase):
    def test_users_cannot_touch_each_others_data(self):
        other = User.objects.create_user(username='mallory', password='test-password')
        theirs = Account.objects.create(user=other, name='Secret')
        their_txn = Transaction.objects.create(user=other, account=theirs, kind='expense', amount=9)
        their_goal = Goal.objects.create(user=other, name='Private', target_amount=100)

        self.assertEqual(self.client.get(reverse('update_account', args=[theirs.id])).status_code, 404)
        self.assertEqual(self.client.post(reverse('delete_transaction', args=[their_txn.id])).status_code, 404)
        self.assertEqual(self.client.post(reverse('contribute_goal', args=[their_goal.id]),
                                          {'amount': '10'}).status_code, 404)
        self.assertNotContains(self.client.get(reverse('accounts')), 'Secret')

    def test_cannot_post_transaction_to_someone_elses_account(self):
        other = User.objects.create_user(username='mallory', password='test-password')
        theirs = Account.objects.create(user=other, name='Secret')
        response = self.client.post(reverse('add_transaction'), {
            'kind': 'expense', 'amount': '10', 'date': '2026-11-01', 'account': theirs.id,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Transaction.objects.count(), 0)


class BudgetAndGoalTests(FinanceBase):
    def test_budget_status_flags_overspend(self):
        Budget.objects.create(user=self.user, category=self.food, amount=100)
        Transaction.objects.create(user=self.user, account=self.bank, kind='expense',
                                   category=self.food, amount=150, date=timezone.localdate())
        response = self.client.get(reverse('budgets'))
        self.assertContains(response, 'over budget')
        self.assertEqual(response.context['rows'][0]['state'], 'over')

    def test_one_budget_per_category(self):
        Budget.objects.create(user=self.user, category=self.food, amount=100)
        response = self.client.post(reverse('add_budget'), {'category': self.food.id, 'amount': '50'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Budget.objects.count(), 1)

    def test_goal_contribution_adds_to_saved_amount(self):
        goal = Goal.objects.create(user=self.user, name='Trip', target_amount=1000)
        self.client.post(reverse('contribute_goal', args=[goal.id]), {'amount': '125.50'})
        goal.refresh_from_db()
        self.assertEqual(goal.saved_amount, Decimal('125.50'))

    def test_update_investment_price(self):
        inv = Investment.objects.create(user=self.user, name='Fund', quantity=2,
                                        buy_price=10, current_price=10)
        self.client.post(reverse('update_price', args=[inv.id]), {'current_price': '15.5'})
        inv.refresh_from_db()
        self.assertEqual(inv.current_price, Decimal('15.5'))


class DashboardTests(FinanceBase):
    def test_net_worth_combines_accounts_and_investments(self):
        Investment.objects.create(user=self.user, name='Fund', quantity=10,
                                  buy_price=50, current_price=60)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['net_worth'], Decimal('1000.00') + Decimal('600.00'))
