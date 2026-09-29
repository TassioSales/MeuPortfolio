from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Category


class NegativeAmountValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="dora", password="pass12345")
        self.client.login(username="dora", password="pass12345")
        self.category = Category.objects.create(user=self.user, name="Mercado", type="DESPESA")

    def test_transaction_rejects_negative_amount(self):
        response = self.client.post(reverse("transaction_add"), {
            "category": self.category.pk,
            "type": "DESPESA",
            "amount": "-50,00",
            "date": "2026-01-10",
            "payment_method": "DINHEIRO",
            "description": "Valor inválido",
            "installments": 1,
        })
        form = response.context["form"]
        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)

    def test_transaction_rejects_zero_amount(self):
        response = self.client.post(reverse("transaction_add"), {
            "category": self.category.pk,
            "type": "DESPESA",
            "amount": "0",
            "date": "2026-01-10",
            "payment_method": "DINHEIRO",
            "description": "Valor zero",
            "installments": 1,
        })
        form = response.context["form"]
        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)

    def test_budget_rejects_negative_limit(self):
        response = self.client.post(reverse("budget_add"), {
            "category": self.category.pk,
            "limit": "-100,00",
            "period": "MENSAL",
            "start_date": "2026-01-01",
        })
        form = response.context["form"]
        self.assertFalse(form.is_valid())
        self.assertIn("limit", form.errors)

    def test_goal_rejects_negative_target(self):
        response = self.client.post(reverse("goal_add"), {
            "name": "Viagem",
            "target_amount": "-1000,00",
            "current_amount": "0",
            "deadline": "2026-12-31",
            "description": "",
        })
        form = response.context["form"]
        self.assertFalse(form.is_valid())
        self.assertIn("target_amount", form.errors)
