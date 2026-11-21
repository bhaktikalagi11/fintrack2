from django.contrib import admin

from .models import Account, Budget, Category, Goal, Investment, Transaction


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'account_type', 'opening_balance')
    list_filter = ('account_type',)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('date', 'user', 'kind', 'amount', 'account', 'category', 'description')
    list_filter = ('kind', 'date')
    search_fields = ('description',)


@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'asset_type', 'quantity', 'buy_price', 'current_price')
    list_filter = ('asset_type',)


admin.site.register(Category)
admin.site.register(Budget)
admin.site.register(Goal)
