import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Category, Transaction


class TransactionListFilterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="nina", password="pass12345")
        self.client.login(username="nina", password="pass12345")
        self.cat_food = Category.objects.create(user=self.user, name="Comida", type="DESPESA")
        self.cat_salary = Category.objects.create(user=self.user, name="Salário", type="RECEITA")

        self.tx_food = Transaction.objects.create(
            user=self.user, category=self.cat_food, type="DESPESA", amount=Decimal("50.00"),
            date=datetime.date(2026, 1, 10), description="Almoço no restaurante",
        )
        self.tx_salary = Transaction.objects.create(
            user=self.user, category=self.cat_salary, type="RECEITA", amount=Decimal("5000.00"),
            date=datetime.date(2026, 1, 5), description="Pagamento mensal",
        )

    def test_search_filters_by_description(self):
        response = self.client.get(reverse("transaction_list"), {"search": "almoço"})
        transactions = list(response.context["transactions"])
        self.assertEqual(transactions, [self.tx_food])

    def test_type_filter(self):
        response = self.client.get(reverse("transaction_list"), {"type": "RECEITA"})
        transactions = list(response.context["transactions"])
        self.assertEqual(transactions, [self.tx_salary])

    def test_category_filter(self):
        response = self.client.get(reverse("transaction_list"), {"category": self.cat_food.pk})
        transactions = list(response.context["transactions"])
        self.assertEqual(transactions, [self.tx_food])

    def test_date_range_filter(self):
        response = self.client.get(reverse("transaction_list"), {"start_date": "2026-01-08", "end_date": "2026-01-31"})
        transactions = list(response.context["transactions"])
        self.assertEqual(transactions, [self.tx_food])

    def test_pagination_splits_results_across_pages(self):
        for i in range(30):
            Transaction.objects.create(
                user=self.user, category=self.cat_food, type="DESPESA", amount=Decimal("10.00"),
                date=datetime.date(2026, 2, 1), description=f"Item {i}",
            )
        response = self.client.get(reverse("transaction_list"))
        self.assertTrue(response.context["is_paginated"])
        self.assertEqual(len(response.context["transactions"]), 25)


class TransactionBulkDeleteTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="oscar", password="pass12345")
        self.client.login(username="oscar", password="pass12345")
        self.tx1 = Transaction.objects.create(
            user=self.user, type="DESPESA", amount=Decimal("10.00"), date=datetime.date(2026, 1, 1), description="A"
        )
        self.tx2 = Transaction.objects.create(
            user=self.user, type="DESPESA", amount=Decimal("20.00"), date=datetime.date(2026, 1, 2), description="B"
        )
        self.tx3 = Transaction.objects.create(
            user=self.user, type="DESPESA", amount=Decimal("30.00"), date=datetime.date(2026, 1, 3), description="C"
        )

        self.other_user = User.objects.create_user(username="paula", password="pass12345")
        self.other_tx = Transaction.objects.create(
            user=self.other_user, type="DESPESA", amount=Decimal("99.00"), date=datetime.date(2026, 1, 1), description="Other"
        )

    def test_deletes_only_selected_transactions(self):
        response = self.client.post(reverse("transaction_bulk_delete"), {"ids": [self.tx1.pk, self.tx2.pk]})
        self.assertRedirects(response, reverse("transaction_list"))
        self.assertFalse(Transaction.objects.filter(pk=self.tx1.pk).exists())
        self.assertFalse(Transaction.objects.filter(pk=self.tx2.pk).exists())
        self.assertTrue(Transaction.objects.filter(pk=self.tx3.pk).exists())

    def test_cannot_delete_another_users_transaction(self):
        response = self.client.post(reverse("transaction_bulk_delete"), {"ids": [self.other_tx.pk]})
        self.assertRedirects(response, reverse("transaction_list"))
        self.assertTrue(Transaction.objects.filter(pk=self.other_tx.pk).exists())

    def test_no_ids_selected_does_not_error(self):
        response = self.client.post(reverse("transaction_bulk_delete"), {})
        self.assertRedirects(response, reverse("transaction_list"))
        self.assertEqual(Transaction.objects.filter(user=self.user).count(), 3)

    def test_requires_post(self):
        response = self.client.get(reverse("transaction_bulk_delete"))
        self.assertEqual(response.status_code, 405)
