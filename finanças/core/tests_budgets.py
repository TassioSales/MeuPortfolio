import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from .models import Budget, Category, Transaction
from .services import budget_spent_map


class BudgetSpentMapTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="gina", password="pass12345")
        self.cat_food = Category.objects.create(user=self.user, name="Comida", type="DESPESA")
        self.cat_fun = Category.objects.create(user=self.user, name="Lazer", type="DESPESA")
        today = datetime.date.today()
        Transaction.objects.create(user=self.user, category=self.cat_food, type="DESPESA", amount=Decimal("120.00"), date=today)
        Transaction.objects.create(user=self.user, category=self.cat_fun, type="DESPESA", amount=Decimal("40.00"), date=today)
        self.budget_food = Budget.objects.create(user=self.user, category=self.cat_food, limit=Decimal("300.00"), period="MENSAL")
        self.budget_fun = Budget.objects.create(user=self.user, category=self.cat_fun, limit=Decimal("100.00"), period="ANUAL")

    def test_spent_map_returns_correct_totals_per_period(self):
        result = budget_spent_map(self.user, [self.budget_food, self.budget_fun])
        self.assertEqual(result[self.budget_food.id], Decimal("120.00"))
        self.assertEqual(result[self.budget_fun.id], Decimal("40.00"))

    def test_spent_map_uses_two_queries_regardless_of_budget_count(self):
        cat_extra = Category.objects.create(user=self.user, name="Transporte", type="DESPESA")
        budget_extra = Budget.objects.create(user=self.user, category=cat_extra, limit=Decimal("200.00"), period="MENSAL")
        budgets = [self.budget_food, self.budget_fun, budget_extra]
        with self.assertNumQueries(2):
            budget_spent_map(self.user, budgets)

    def test_budget_with_no_transactions_returns_zero(self):
        cat_empty = Category.objects.create(user=self.user, name="Vazia", type="DESPESA")
        budget_empty = Budget.objects.create(user=self.user, category=cat_empty, limit=Decimal("50.00"), period="MENSAL")
        result = budget_spent_map(self.user, [budget_empty])
        self.assertEqual(result[budget_empty.id], Decimal("0"))
