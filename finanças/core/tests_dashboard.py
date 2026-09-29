import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from .models import Transaction
from .views_dashboard import _income_expense_totals


class IncomeExpenseTotalsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="hank", password="pass12345")
        today = datetime.date.today()
        Transaction.objects.create(user=self.user, type="RECEITA", amount=Decimal("500.00"), date=today)
        Transaction.objects.create(user=self.user, type="RECEITA", amount=Decimal("200.00"), date=today)
        Transaction.objects.create(user=self.user, type="DESPESA", amount=Decimal("150.00"), date=today)

    def test_totals_computed_in_a_single_query(self):
        qs = Transaction.objects.filter(user=self.user)
        with self.assertNumQueries(1):
            income, expense = _income_expense_totals(qs)
        self.assertEqual(income, Decimal("700.00"))
        self.assertEqual(expense, Decimal("150.00"))

    def test_totals_are_zero_for_empty_queryset(self):
        qs = Transaction.objects.filter(user=self.user, date__lt=datetime.date(2000, 1, 1))
        income, expense = _income_expense_totals(qs)
        self.assertEqual(income, 0)
        self.assertEqual(expense, 0)
