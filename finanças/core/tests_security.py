from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Category


class CrossUserCategoryLeakTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username="alice", password="pass12345")
        self.user_b = User.objects.create_user(username="bob", password="pass12345")
        self.category_b = Category.objects.create(user=self.user_b, name="Categoria do Bob", type="DESPESA")
        self.client.login(username="alice", password="pass12345")

    def test_transaction_form_excludes_other_users_categories(self):
        response = self.client.get(reverse("transaction_add"))
        form = response.context["form"]
        self.assertNotIn(self.category_b, form.fields["category"].queryset)

    def test_cannot_attach_transaction_to_other_users_category(self):
        response = self.client.post(reverse("transaction_add"), {
            "category": self.category_b.pk,
            "type": "DESPESA",
            "amount": "50,00",
            "date": "2026-01-10",
            "payment_method": "DINHEIRO",
            "description": "Tentativa de vazamento",
            "installments": 1,
        })
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertFalse(form.is_valid())
        self.assertIn("category", form.errors)

    def test_budget_form_excludes_other_users_categories(self):
        response = self.client.get(reverse("budget_add"))
        form = response.context["form"]
        self.assertNotIn(self.category_b, form.fields["category"].queryset)
