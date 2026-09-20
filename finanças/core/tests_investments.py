import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from .models import Investment


class InvestmentSaveQueryCountTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="carla", password="pass12345")

    def test_create_does_not_issue_extra_update_on_investment(self):
        with CaptureQueriesContext(connection) as ctx:
            inv = Investment.objects.create(
                user=self.user,
                category_type="VARIABLE",
                symbol="PETR4.SA",
                quantity=Decimal("10"),
                purchase_price=Decimal("30.00"),
                date=datetime.date.today(),
            )
        update_queries = [
            q["sql"] for q in ctx.captured_queries
            if q["sql"].upper().startswith("UPDATE") and "core_investment" in q["sql"].lower()
        ]
        self.assertEqual(len(update_queries), 0, f"Expected no UPDATEs on core_investment during create, got: {update_queries}")
        self.assertIsNotNone(inv.transaction)
        self.assertEqual(inv.transaction.amount, inv.total_cost)
