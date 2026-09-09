from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
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

    def test_catches_up_multiple_missed_occurrences(self):
        # A lapsed daily recurrence 2 days behind: one call should catch up all 3.
        today = timezone.now().date()
        recurring = RecurringTransaction.objects.create(
            user=self.user,
            category=self.category,
            type='DESPESA',
            amount=50,
            frequency='DIARIO',
            next_run_date=today - datetime.timedelta(days=2),
            description='Missed Days'
        )

        count = process_recurring_transactions(self.user)
        self.assertEqual(count, 3)
        self.assertEqual(Transaction.objects.count(), 3)

        recurring.refresh_from_db()
        self.assertEqual(recurring.next_run_date, today + datetime.timedelta(days=1))

    def test_projects_forward_when_up_to_date_is_in_the_future(self):
        # Browsing ahead to a future month must pre-materialize recurring
        # transactions up through that month, not just up to today.
        today = timezone.now().date()
        recurring = RecurringTransaction.objects.create(
            user=self.user,
            category=self.category,
            type='DESPESA',
            amount=520,
            frequency='DIARIO',
            next_run_date=today,
            description='Assinatura'
        )
        future_date = today + datetime.timedelta(days=3)

        count = process_recurring_transactions(self.user, up_to_date=future_date)
        self.assertEqual(count, 4)  # today, +1, +2, +3
        self.assertEqual(Transaction.objects.count(), 4)

        recurring.refresh_from_db()
        self.assertEqual(recurring.next_run_date, today + datetime.timedelta(days=4))

    def test_dashboard_navigating_to_a_future_month_materializes_recurring_expense(self):
        # End-to-end reproduction of the reported bug: a monthly recurring
        # expense created today must already show up when browsing the
        # dashboard forward to next month, without waiting for real time
        # to pass.
        self.client.login(username='testuser', password='password')
        today = timezone.now().date()
        RecurringTransaction.objects.create(
            user=self.user,
            category=self.category,
            type='DESPESA',
            amount=520,
            frequency='MENSAL',
            next_run_date=today,
            description='Dívida recorrente'
        )

        next_month = today.month + 1
        next_year = today.year
        if next_month > 12:
            next_month = 1
            next_year += 1

        response = self.client.get(reverse('dashboard'), {'month': next_month, 'year': next_year})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Transaction.objects.filter(
                description__contains='Dívida recorrente', date__month=next_month, date__year=next_year
            ).exists()
        )
