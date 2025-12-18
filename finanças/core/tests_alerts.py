from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Transaction, Category, Budget
from django.utils import timezone
import datetime

class BudgetAlertTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client = Client()
        self.client.login(username='testuser', password='password')
        self.category = Category.objects.create(user=self.user, name='Food', type='DESPESA')
        self.url = reverse('dashboard')

    def test_no_alert_within_budget(self):
        # Budget of 1000, spent 500 (50%)
        Budget.objects.create(user=self.user, category=self.category, limit=1000, period='MENSAL')
        Transaction.objects.create(
            user=self.user,
            category=self.category,
            type='DESPESA',
            amount=500,
            date=timezone.now().date(),
            description='Groceries'
        )
        
        response = self.client.get(self.url)
        self.assertNotContains(response, 'Atenção: Você já consumiu')

    def test_alert_near_limit(self):
        # Budget of 1000, spent 950 (95%)
        Budget.objects.create(user=self.user, category=self.category, limit=1000, period='MENSAL')
        Transaction.objects.create(
            user=self.user,
            category=self.category,
            type='DESPESA',
            amount=950,
            date=timezone.now().date(),
            description='Big Shopping'
        )
        
        response = self.client.get(self.url)
        self.assertContains(response, 'Atenção:')
        self.assertContains(response, '95%')
        self.assertContains(response, 'Food')

    def test_alert_over_limit(self):
        # Budget of 1000, spent 1100 (110%)
        Budget.objects.create(user=self.user, category=self.category, limit=1000, period='MENSAL')
        Transaction.objects.create(
            user=self.user,
            category=self.category,
            type='DESPESA',
            amount=1100,
            date=timezone.now().date(),
            description='Overspending'
        )
        
        response = self.client.get(self.url)
        self.assertContains(response, 'alert-danger')
        self.assertContains(response, '110%')
