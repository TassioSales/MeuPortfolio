from django.test import TestCase
from django.contrib.auth.models import User
from .models import Account, Category, Transaction, Budget
from decimal import Decimal
from django.urls import reverse
from django.utils import timezone

class ModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.account = Account.objects.create(user=self.user, name='Bank', initial_balance=1000)
        self.category = Category.objects.create(user=self.user, name='Food', type='DESPESA')

    def test_account_creation(self):
        self.assertEqual(self.account.current_balance, 1000)
        self.assertEqual(str(self.account), "Bank (Bancária)")

    def test_transaction_creation(self):
        t = Transaction.objects.create(
            user=self.user,
            source_account=self.account,
            category=self.category,
            type='DESPESA',
            amount=100,
            date=timezone.now().date()
        )
        self.assertEqual(t.amount, 100)
        # Note: current_balance property in model is currently just initial_balance
        # Logic for dynamic balance needs to be implemented or tested if implemented

class ViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client.login(username='testuser', password='password')

    def test_dashboard_view(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/dashboard.html')

    def test_account_list_view(self):
        response = self.client.get(reverse('account_list'))
        self.assertEqual(response.status_code, 200)

    def test_reports_view(self):
        response = self.client.get(reverse('reports'))
        self.assertEqual(response.status_code, 200)
