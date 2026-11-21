from decimal import Decimal

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Account, Budget, Category, Goal, Investment, Transaction


class DateInput(forms.DateInput):
    input_type = 'date'

    def __init__(self, **kwargs):
        kwargs.setdefault('format', '%Y-%m-%d')
        super().__init__(**kwargs)


class UserScopedForm(forms.ModelForm):
    """ModelForm that stamps the owner on save and lets subclasses scope choices."""

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.user = self.user
        if commit:
            obj.save()
        return obj


# REGISTER FORM
class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')


# ACCOUNT FORM
class AccountForm(UserScopedForm):
    class Meta:
        model = Account
        fields = ['name', 'account_type', 'opening_balance']

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        clash = Account.objects.filter(user=self.user, name__iexact=name)
        if self.instance.pk:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise forms.ValidationError('You already have an account with this name.')
        return name


# CATEGORY FORM
class CategoryForm(UserScopedForm):
    class Meta:
        model = Category
        fields = ['name', 'kind']

    def clean(self):
        cleaned = super().clean()
        name, kind = cleaned.get('name'), cleaned.get('kind')
        if name and kind:
            clash = Category.objects.filter(user=self.user, name__iexact=name.strip(), kind=kind)
            if self.instance.pk:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                raise forms.ValidationError('That category already exists.')
        return cleaned


# TRANSACTION FORM
class TransactionForm(UserScopedForm):
    class Meta:
        model = Transaction
        fields = ['kind', 'amount', 'date', 'account', 'to_account', 'category', 'description']
        widgets = {'date': DateInput()}
        labels = {'to_account': 'Transfer to account'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        accounts = Account.objects.filter(user=self.user)
        self.fields['account'].queryset = accounts
        self.fields['to_account'].queryset = accounts
        self.fields['category'].queryset = Category.objects.filter(user=self.user)
        self.fields['category'].required = False
        self.fields['to_account'].required = False
        self.fields['amount'].widget.attrs.update({'step': '0.01', 'min': '0.01'})

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get('kind')
        account = cleaned.get('account')
        to_account = cleaned.get('to_account')
        category = cleaned.get('category')

        if kind == Transaction.TRANSFER:
            if not to_account:
                self.add_error('to_account', 'Choose the account the money moves to.')
            elif account and to_account == account:
                self.add_error('to_account', 'Pick a different account than the source.')
            cleaned['category'] = None
        else:
            cleaned['to_account'] = None
            if category and category.kind != kind:
                self.add_error('category', f'Pick a {kind} category.')
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.category = self.cleaned_data.get('category')
        obj.to_account = self.cleaned_data.get('to_account')
        obj.user = self.user
        if commit:
            obj.save()
        return obj


# BUDGET FORM
class BudgetForm(UserScopedForm):
    class Meta:
        model = Budget
        fields = ['category', 'amount']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.filter(
            user=self.user, kind=Category.EXPENSE
        )

    def clean_category(self):
        category = self.cleaned_data['category']
        clash = Budget.objects.filter(user=self.user, category=category)
        if self.instance.pk:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise forms.ValidationError('You already set a budget for this category.')
        return category


# INVESTMENT FORM
class InvestmentForm(UserScopedForm):
    class Meta:
        model = Investment
        fields = ['name', 'symbol', 'asset_type', 'quantity', 'buy_price',
                  'current_price', 'purchase_date', 'notes']
        widgets = {'purchase_date': DateInput()}


# GOAL FORM
class GoalForm(UserScopedForm):
    class Meta:
        model = Goal
        fields = ['name', 'target_amount', 'saved_amount', 'target_date']
        widgets = {'target_date': DateInput()}


class ContributeForm(forms.Form):
    amount = forms.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal('0.01'))
