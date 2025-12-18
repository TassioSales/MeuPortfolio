from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Transaction, Category
from django.utils import timezone
import datetime

class CalendarTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client = Client()
        self.client.login(username='testuser', password='password')
        self.category = Category.objects.create(user=self.user, name='Test Cat', type='DESPESA')
        self.url = reverse('calendar')

    def test_calendar_load(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Calendário Financeiro')

    def test_transaction_in_calendar(self):
        today = timezone.now().date()
        Transaction.objects.create(
            user=self.user,
            category=self.category,
            type='DESPESA',
            amount=100,
            date=today,
            description='Calendar Test Transaction'
        )
        
        response = self.client.get(self.url)
        self.assertContains(response, 'Calendar Test Transaction')
        self.assertContains(response, '100')

    def test_navigation(self):
        # Test navigation to previous month
        today = timezone.now().date()
        prev_month = today.month - 1 if today.month > 1 else 12
        prev_year = today.year if today.month > 1 else today.year - 1
        
        response = self.client.get(f"{self.url}?month={prev_month}&year={prev_year}")
        self.assertEqual(response.status_code, 200)
