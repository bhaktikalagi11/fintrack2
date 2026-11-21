import decimal

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('account_type', models.CharField(choices=[('bank', 'Bank account'), ('savings', 'Savings account'), ('cash', 'Cash'), ('card', 'Credit card'), ('wallet', 'Digital wallet')], default='bank', max_length=20)),
                ('opening_balance', models.DecimalField(decimal_places=2, default=decimal.Decimal('0.00'), max_digits=14)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='accounts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['name'],
                'unique_together': {('user', 'name')},
            },
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=80)),
                ('kind', models.CharField(choices=[('income', 'Income'), ('expense', 'Expense')], default='expense', max_length=10)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='categories', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'categories',
                'ordering': ['kind', 'name'],
                'unique_together': {('user', 'name', 'kind')},
            },
        ),
        migrations.CreateModel(
            name='Goal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('target_amount', models.DecimalField(decimal_places=2, max_digits=14, validators=[django.core.validators.MinValueValidator(decimal.Decimal('0.01'))])),
                ('saved_amount', models.DecimalField(decimal_places=2, default=decimal.Decimal('0.00'), max_digits=14)),
                ('target_date', models.DateField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='goals', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['target_date', 'name'],
            },
        ),
        migrations.CreateModel(
            name='Investment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150)),
                ('symbol', models.CharField(blank=True, max_length=30, verbose_name='ticker / code')),
                ('asset_type', models.CharField(choices=[('stock', 'Stock'), ('mutual_fund', 'Mutual fund'), ('etf', 'ETF'), ('bond', 'Bond'), ('fd', 'Fixed deposit'), ('gold', 'Gold'), ('crypto', 'Crypto'), ('real_estate', 'Real estate'), ('ppf', 'PPF / EPF / NPS'), ('other', 'Other')], default='stock', max_length=20)),
                ('quantity', models.DecimalField(decimal_places=4, default=decimal.Decimal('1'), max_digits=16, validators=[django.core.validators.MinValueValidator(decimal.Decimal('0.0001'))], verbose_name='units')),
                ('buy_price', models.DecimalField(decimal_places=4, max_digits=14, validators=[django.core.validators.MinValueValidator(decimal.Decimal('0'))], verbose_name='average buy price per unit')),
                ('current_price', models.DecimalField(decimal_places=4, max_digits=14, validators=[django.core.validators.MinValueValidator(decimal.Decimal('0'))], verbose_name='current price per unit')),
                ('purchase_date', models.DateField(default=django.utils.timezone.localdate)),
                ('notes', models.CharField(blank=True, max_length=200)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='investments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Budget',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=14, validators=[django.core.validators.MinValueValidator(decimal.Decimal('0.01'))], verbose_name='monthly limit')),
                ('category', models.ForeignKey(limit_choices_to={'kind': 'expense'}, on_delete=django.db.models.deletion.CASCADE, to='finance.category')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='budgets', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['category__name'],
                'unique_together': {('user', 'category')},
            },
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(choices=[('income', 'Income'), ('expense', 'Expense'), ('transfer', 'Transfer')], default='expense', max_length=10)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=14, validators=[django.core.validators.MinValueValidator(decimal.Decimal('0.01'))])),
                ('date', models.DateField(default=django.utils.timezone.localdate)),
                ('description', models.CharField(blank=True, max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='finance.account')),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='finance.category')),
                ('to_account', models.ForeignKey(blank=True, help_text='Only for transfers: the account the money moves to.', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='incoming_transfers', to='finance.account')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-date', '-id'],
            },
        ),
    ]
