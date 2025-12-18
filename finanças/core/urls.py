from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Auth
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),
    
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('calendar/', views.calendar_view, name='calendar'),

    # Categories
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('categories/add/', views.CategoryCreateView.as_view(), name='category_add'),
    path('categories/<int:pk>/edit/', views.CategoryUpdateView.as_view(), name='category_edit'),
    path('categories/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),

    # Transactions
    path('transactions/', views.TransactionListView.as_view(), name='transaction_list'),
    path('transactions/import/', views.import_transactions, name='transaction_import'),
    path('transactions/add/', views.TransactionCreateView.as_view(), name='transaction_add'),
    path('transactions/<int:pk>/edit/', views.TransactionUpdateView.as_view(), name='transaction_edit'),
    path('transactions/<int:pk>/delete/', views.TransactionDeleteView.as_view(), name='transaction_delete'),

    # Budgets
    path('budgets/', views.BudgetListView.as_view(), name='budget_list'),
    path('budgets/add/', views.BudgetCreateView.as_view(), name='budget_add'),
    path('budgets/<int:pk>/edit/', views.BudgetUpdateView.as_view(), name='budget_edit'),
    path('budgets/<int:pk>/delete/', views.BudgetDeleteView.as_view(), name='budget_delete'),

    # Reports
    path('reports/', views.reports, name='reports'),
    path('reports/export/', views.export_csv, name='export_csv'),
    path('reports/export/pdf/', views.export_pdf, name='export_pdf'),
    # Investments
    path('investments/', views.investment_dashboard, name='investment_dashboard'),
    path('investments/search/', views.search_ticker, name='search_ticker'),
    path('investments/list/', views.InvestmentListView.as_view(), name='investment_list'),
    path('investments/add/', views.InvestmentCreateView.as_view(), name='investment_add'),
    path('investments/<int:pk>/edit/', views.InvestmentUpdateView.as_view(), name='investment_edit'),
    path('investments/<int:pk>/delete/', views.InvestmentDeleteView.as_view(), name='investment_delete'),
    
    # Goals
    path('goals/', views.GoalListView.as_view(), name='goal_list'),
    path('goals/add/', views.GoalCreateView.as_view(), name='goal_add'),
    path('goals/<int:pk>/edit/', views.GoalUpdateView.as_view(), name='goal_edit'),
    path('goals/<int:pk>/delete/', views.GoalDeleteView.as_view(), name='goal_delete'),
]
# Force reload
