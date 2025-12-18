from django.test import TestCase
from django.contrib.auth.models import User
from .models import Category, Transaction, Budget, Investment
from decimal import Decimal
from django.urls import reverse
from django.utils import timezone
import datetime

class ModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.category = Category.objects.create(user=self.user, name='Food', type='DESPESA')

    def test_category_creation(self):
        self.assertEqual(str(self.category), "Food")
        self.assertEqual(self.category.type, 'DESPESA')

    def test_transaction_creation(self):
        t = Transaction.objects.create(
            user=self.user,
            category=self.category,
            type='DESPESA',
            amount=Decimal('100.00'),
            date=timezone.now().date(),
            description='Lunch'
        )
        self.assertEqual(t.amount, Decimal('100.00'))
        self.assertEqual(str(t), f"Despesa - 100.00 - {t.date}")

    def test_budget_creation(self):
        b = Budget.objects.create(
            user=self.user,
            category=self.category,
            limit=Decimal('500.00'),
            period='MENSAL'
        )
        self.assertEqual(b.limit, Decimal('500.00'))
        self.assertEqual(str(b), "Orçamento para Food: 500.00")

class ViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client.login(username='testuser', password='password')
        self.category = Category.objects.create(user=self.user, name='Food', type='DESPESA')

    def test_dashboard_view(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/dashboard.html')

    def test_category_list_view(self):
        response = self.client.get(reverse('category_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Food')

    def test_transaction_list_view(self):
        Transaction.objects.create(
            user=self.user,
            category=self.category,
            type='DESPESA',
            amount=Decimal('50.00'),
            date=timezone.now().date()
        )
        response = self.client.get(reverse('transaction_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '50,00')

    def test_reports_view(self):
        response = self.client.get(reverse('reports'))
        self.assertEqual(response.status_code, 200)
