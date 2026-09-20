from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import BankAccount, Loan, Transaction, Transfer


class TransferAtomicityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="eve", password="pass12345")
        self.client.login(username="eve", password="pass12345")
        self.acc_a = BankAccount.objects.create(user=self.user, name="Conta A", balance=Decimal("100.00"))
        self.acc_b = BankAccount.objects.create(user=self.user, name="Conta B", balance=Decimal("50.00"))

    def test_failed_transfer_does_not_partially_update_balances(self):
        with patch("core.views_accounts.AuditLog.objects.create", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                self.client.post(reverse("transfer_create"), {
                    "from_account": self.acc_a.pk,
                    "to_account": self.acc_b.pk,
                    "amount": "30,00",
                    "date": "2026-01-10",
                    "description": "Teste",
                })
        self.acc_a.refresh_from_db()
        self.acc_b.refresh_from_db()
        self.assertEqual(self.acc_a.balance, Decimal("100.00"))
        self.assertEqual(self.acc_b.balance, Decimal("50.00"))
        self.assertEqual(Transfer.objects.count(), 0)


class LoanPaymentAtomicityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="fred", password="pass12345")
        self.client.login(username="fred", password="pass12345")
        self.loan = Loan.objects.create(
            user=self.user, name="Empréstimo Teste", lender="Banco X",
            loan_type="REDUCAO_SALDO", principal=Decimal("1000.00"),
            interest_rate=Decimal("1.0"), interest_period="MENSAL",
            start_date=timezone.now().date(), current_balance=Decimal("1000.00"),
        )

    def test_failed_payment_does_not_change_loan_balance(self):
        with patch("core.views_loans.AuditLog.objects.create", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                self.client.post(reverse("loan_pay", args=[self.loan.pk]), {
                    "payment_date": "2026-01-10",
                    "amount_paid": "50,00",
                    "notes": "",
                })
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.current_balance, Decimal("1000.00"))
        self.assertEqual(self.loan.payments.count(), 0)
        self.assertEqual(Transaction.objects.filter(user=self.user).count(), 0)
