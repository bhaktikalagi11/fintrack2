from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),

    path('transactions/', views.transactions, name='transactions'),
    path('transactions/add/', views.add_transaction, name='add_transaction'),
    path('transactions/export/', views.export_transactions, name='export_transactions'),
    path('transactions/update/<int:id>/', views.update_transaction, name='update_transaction'),
    path('transactions/delete/<int:id>/', views.delete_transaction, name='delete_transaction'),

    path('accounts/', views.accounts, name='accounts'),
    path('accounts/add/', views.add_account, name='add_account'),
    path('accounts/update/<int:id>/', views.update_account, name='update_account'),
    path('accounts/delete/<int:id>/', views.delete_account, name='delete_account'),

    path('categories/', views.categories, name='categories'),
    path('categories/add/', views.add_category, name='add_category'),
    path('categories/update/<int:id>/', views.update_category, name='update_category'),
    path('categories/delete/<int:id>/', views.delete_category, name='delete_category'),

    path('budgets/', views.budgets, name='budgets'),
    path('budgets/add/', views.add_budget, name='add_budget'),
    path('budgets/update/<int:id>/', views.update_budget, name='update_budget'),
    path('budgets/delete/<int:id>/', views.delete_budget, name='delete_budget'),

    path('investments/', views.investments, name='investments'),
    path('investments/add/', views.add_investment, name='add_investment'),
    path('investments/update/<int:id>/', views.update_investment, name='update_investment'),
    path('investments/price/<int:id>/', views.update_price, name='update_price'),
    path('investments/delete/<int:id>/', views.delete_investment, name='delete_investment'),

    path('goals/', views.goals, name='goals'),
    path('goals/add/', views.add_goal, name='add_goal'),
    path('goals/update/<int:id>/', views.update_goal, name='update_goal'),
    path('goals/contribute/<int:id>/', views.contribute_goal, name='contribute_goal'),
    path('goals/delete/<int:id>/', views.delete_goal, name='delete_goal'),

    path('reports/', views.reports, name='reports'),
]
