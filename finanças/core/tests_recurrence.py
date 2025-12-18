from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Transaction, RecurringTransaction, Category
from .services import process_recurring_transactions
import datetime

class RecurrenceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.category = Category.objects.create(user=self.user, name='Test Cat', type='DESPESA')

    def test_daily_recurrence(self):
        # Create a recurring transaction due today
        today = timezone.now().date()
        recurring = RecurringTransaction.objects.create(
            user=self.user,
            category=self.category,
            type='DESPESA',
            amount=100,
            frequency='DIARIO',
            next_run_date=today,
            description='Daily Test'
        )
        
        # Process
        count = process_recurring_transactions(self.user)
        self.assertEqual(count, 1)
        
        # Check if transaction was created
        self.assertEqual(Transaction.objects.count(), 1)
        tx = Transaction.objects.first()
        self.assertEqual(tx.description, 'Daily Test (Recorrente)')
        self.assertEqual(tx.date, today)
        
        # Check next run date
        recurring.refresh_from_db()
        self.assertEqual(recurring.next_run_date, today + datetime.timedelta(days=1))

    def test_monthly_recurrence(self):
        # Create a recurring transaction due today
        today = timezone.now().date()
        recurring = RecurringTransaction.objects.create(
            user=self.user,
            category=self.category,
            type='DESPESA',
            amount=200,
            frequency='MENSAL',
            next_run_date=today,
            description='Monthly Test'
        )
        
        # Process
        count = process_recurring_transactions(self.user)
        self.assertEqual(count, 1)
        
        # Check next run date logic (simple check)
        recurring.refresh_from_db()
        # Logic is complex for end of month, but for today it should be roughly +30 days
        self.assertTrue(recurring.next_run_date > today)
        self.assertTrue(recurring.next_run_date <= today + datetime.timedelta(days=32))

    def test_future_recurrence(self):
        # Create a recurring transaction due tomorrow
        today = timezone.now().date()
        tomorrow = today + datetime.timedelta(days=1)
        recurring = RecurringTransaction.objects.create(
            user=self.user,
            category=self.category,
            type='DESPESA',
            amount=300,
            frequency='SEMANAL',
            next_run_date=tomorrow,
            description='Future Test'
        )
        
        # Process
        count = process_recurring_transactions(self.user)
        self.assertEqual(count, 0)
        self.assertEqual(Transaction.objects.count(), 0)
