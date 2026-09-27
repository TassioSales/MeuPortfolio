import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Loan, Transaction
from .services_loans import (
    add_funds, build_schedule, pending_installments, register_payment, revert_payment,
    sync_loan_income, sync_loan_installments,
)
from .testing import frozen_today

TODAY = datetime.date(2026, 9, 27)


def make_loan(user, **kw):
    data = dict(
        user=user, name="Empréstimo", lender="Banco", loan_type="PRICE",
        principal=Decimal("1200.00"), current_balance=Decimal("1200.00"),
        interest_rate=Decimal("1.0"), interest_period="MENSAL",
        start_date=datetime.date(2026, 9, 1), due_day=10, num_installments=12,
        register_income=False,
    )
    data.update(kw)
    return Loan.objects.create(**data)


class ScheduleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ana", password="x")

    def test_price_schedule_pays_off_exactly(self):
        loan = make_loan(self.user)
        schedule = build_schedule(loan)
        self.assertEqual(len(schedule), 12)
        self.assertEqual(schedule[-1]["balance"], Decimal("0.00"))
        # Parcela Price de 1200 a 1% em 12x ≈ 106,62
        self.assertEqual(schedule[0]["payment"], Decimal("106.62"))
        self.assertIsInstance(schedule[0]["payment"], Decimal)

    def test_sac_principal_is_constant(self):
        loan = make_loan(self.user, loan_type="SAC")
        schedule = build_schedule(loan)
        self.assertTrue(all(r["principal"] == Decimal("100.00") for r in schedule))
        self.assertGreater(schedule[0]["payment"], schedule[-1]["payment"])

    def test_simples_interest_only_then_principal(self):
        loan = make_loan(self.user, loan_type="SIMPLES", num_installments=3)
        schedule = build_schedule(loan)
        self.assertEqual([r["payment"] for r in schedule],
                         [Decimal("12.00"), Decimal("12.00"), Decimal("1212.00")])

    def test_informal_zero_interest_has_no_forecast(self):
        loan = make_loan(self.user, loan_type="REDUCAO_SALDO", num_installments=None,
                         interest_rate=Decimal("0"))
        self.assertEqual(build_schedule(loan), [])

    def test_planned_payment_overrides_any_type(self):
        loan = make_loan(self.user, loan_type="REDUCAO_SALDO", num_installments=None,
                         interest_rate=Decimal("0"), planned_payment=Decimal("500"))
        schedule = build_schedule(loan)
        self.assertEqual([r["payment"] for r in schedule],
                         [Decimal("500.00"), Decimal("500.00"), Decimal("200.00")])


class SyncTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("bia", password="x")

    def test_installments_materialized_as_expenses(self):
        with frozen_today(TODAY):
            loan = make_loan(self.user)
            created = sync_loan_installments(loan)
        self.assertEqual(created, 12)
        txs = list(pending_installments(loan).order_by("date"))
        self.assertEqual(txs[0].date, datetime.date(2026, 10, 10))
        self.assertEqual(txs[0].type, "DESPESA")
        self.assertEqual(txs[0].origin, Transaction.ORIGIN_EMPRESTIMO)
        self.assertEqual(txs[0].category.name, "Empréstimos")
        self.assertIn("parcela 1/12", txs[0].description)

    def test_sync_is_idempotent(self):
        with frozen_today(TODAY):
            loan = make_loan(self.user)
            sync_loan_installments(loan)
            sync_loan_installments(loan)
        self.assertEqual(pending_installments(loan).count(), 12)

    def test_capped_at_24_months(self):
        with frozen_today(TODAY):
            loan = make_loan(self.user, loan_type="SIMPLES", num_installments=60,
                             principal=Decimal("52000"), current_balance=Decimal("52000"))
            sync_loan_installments(loan)
        self.assertLessEqual(pending_installments(loan).count(), 24)

    def test_income_registered_when_requested(self):
        with frozen_today(TODAY):
            loan = make_loan(self.user, register_income=True, iof_rate=Decimal("3"))
            sync_loan_income(loan)
        income = loan.transactions.get(type="RECEITA")
        self.assertEqual(income.amount, Decimal("1164.00"))
        loan.register_income = False
        sync_loan_income(loan)
        self.assertFalse(loan.transactions.filter(type="RECEITA").exists())


class PaymentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("caio", password="x")

    def test_payment_reconciles_forecast_instead_of_duplicating(self):
        with frozen_today(TODAY):
            loan = make_loan(self.user)
            sync_loan_installments(loan)
            register_payment(loan, Decimal("106.62"), datetime.date(2026, 10, 9))
        loan.refresh_from_db()
        oct_txs = Transaction.objects.filter(user=self.user, date__year=2026, date__month=10, type="DESPESA")
        self.assertEqual(oct_txs.count(), 1)
        self.assertTrue(hasattr(oct_txs.first(), "loan_payment"))
        self.assertEqual(loan.current_balance, Decimal("1105.38"))
        # continua com 11 parcelas previstas (12 - 1 paga)
        self.assertEqual(pending_installments(loan).count(), 11)

    def test_extra_payment_creates_new_transaction(self):
        with frozen_today(TODAY):
            loan = make_loan(self.user, loan_type="REDUCAO_SALDO", num_installments=None,
                             interest_rate=Decimal("0"))
            sync_loan_installments(loan)
            register_payment(loan, Decimal("300"), TODAY)
        loan.refresh_from_db()
        self.assertEqual(loan.current_balance, Decimal("900.00"))
        self.assertEqual(loan.transactions.filter(type="DESPESA").count(), 1)

    def test_revert_restores_balance_and_forecast(self):
        with frozen_today(TODAY):
            loan = make_loan(self.user)
            sync_loan_installments(loan)
            payment = register_payment(loan, Decimal("106.62"), datetime.date(2026, 10, 9))
            revert_payment(payment)
        loan.refresh_from_db()
        self.assertEqual(loan.current_balance, Decimal("1200.00"))
        self.assertEqual(loan.payments.count(), 0)
        self.assertEqual(pending_installments(loan).count(), 12)

    def test_only_latest_payment_can_be_reverted(self):
        with frozen_today(TODAY):
            loan = make_loan(self.user)
            first = register_payment(loan, Decimal("100"), datetime.date(2026, 10, 9))
            register_payment(loan, Decimal("100"), datetime.date(2026, 11, 9))
            with self.assertRaises(ValueError):
                revert_payment(first)

    def test_add_funds_increases_balance_and_resyncs(self):
        with frozen_today(TODAY):
            loan = make_loan(self.user, loan_type="REDUCAO_SALDO", num_installments=None,
                             planned_payment=Decimal("100"), register_income=True)
            add_funds(loan, Decimal("300"), TODAY)
        loan.refresh_from_db()
        self.assertEqual(loan.current_balance, Decimal("1500.00"))
        self.assertTrue(loan.transactions.filter(type="RECEITA", loan_disbursement__isnull=False).exists())


class LoanFormViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("duda", password="x")
        self.client.login(username="duda", password="x")

    def post_loan(self, **overrides):
        data = {
            "name": "Empréstimo do tio", "lender": "Tio", "loan_type": "REDUCAO_SALDO",
            "principal": "5.000,00", "current_balance": "", "interest_rate": "0",
            "interest_period": "MENSAL", "iof_rate": "", "insurance_monthly": "",
            "start_date": "2026-09-01", "due_day": "10", "num_installments": "0",
            "planned_payment": "", "notes": "", "is_active": "True",
        }
        data.update(overrides)
        return self.client.post(reverse("loan_add"), data)

    def test_zero_installments_is_accepted(self):
        with frozen_today(TODAY):
            resp = self.post_loan()
        if resp.status_code != 302:
            self.fail(resp.context["form"].errors)
        loan = Loan.objects.get(user=self.user)
        self.assertIsNone(loan.num_installments)
        self.assertEqual(pending_installments(loan).count(), 0)

    def test_planned_payment_enters_expenses(self):
        with frozen_today(TODAY):
            self.post_loan(planned_payment="1.000,00")
        loan = Loan.objects.get(user=self.user)
        self.assertEqual(loan.planned_payment, Decimal("1000.00"))
        self.assertEqual(pending_installments(loan).count(), 5)

    def test_edit_to_zero_installments_resyncs(self):
        with frozen_today(TODAY):
            loan = make_loan(self.user, loan_type="SIMPLES", num_installments=60,
                             principal=Decimal("52000"), current_balance=Decimal("52000"))
            sync_loan_installments(loan)
            resp = self.client.post(reverse("loan_edit", args=[loan.pk]), {
                "name": loan.name, "lender": loan.lender, "loan_type": "REDUCAO_SALDO",
                "principal": "52.000,00", "current_balance": "52.000,00", "interest_rate": "0",
                "interest_period": "MENSAL", "start_date": "2026-09-01", "due_day": "10",
                "num_installments": "0", "planned_payment": "800,00", "is_active": "True",
            })
        if resp.status_code != 302:
            self.fail(resp.context["form"].errors)
        loan.refresh_from_db()
        self.assertIsNone(loan.num_installments)
        amounts = set(pending_installments(loan).values_list("amount", flat=True))
        self.assertEqual(amounts, {Decimal("800.00")})

    def test_payment_view_and_revert(self):
        with frozen_today(TODAY):
            loan = make_loan(self.user)
            sync_loan_installments(loan)
            self.client.post(reverse("loan_pay", args=[loan.pk]), {
                "payment_date": "2026-10-09", "amount_paid": "106,62", "notes": "",
            })
            payment = loan.payments.get()
            self.client.post(reverse("loan_payment_revert", args=[loan.pk, payment.pk]))
        loan.refresh_from_db()
        self.assertEqual(loan.current_balance, Decimal("1200.00"))

    def test_other_user_cannot_revert(self):
        other = User.objects.create_user("intruso", password="x")
        with frozen_today(TODAY):
            loan = make_loan(other)
            payment = register_payment(loan, Decimal("100"), TODAY)
        resp = self.client.post(reverse("loan_payment_revert", args=[loan.pk, payment.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_detail_page_renders(self):
        with frozen_today(TODAY):
            loan = make_loan(self.user)
            sync_loan_installments(loan)
            resp = self.client.get(reverse("loan_detail", args=[loan.pk]) + "?sim=200")
            list_resp = self.client.get(reverse("loan_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "10/10/2026")
        self.assertEqual(list_resp.status_code, 200)


class PaymentEditDeleteTests(TestCase):
    """Pagamento de empréstimo: editar/excluir mantém o saldo devedor correto,
    inclusive quando a ação parte da tela de Transações."""

    def setUp(self):
        self.user = User.objects.create_user("elis", password="x")
        self.client.login(username="elis", password="x")
        with frozen_today(TODAY):
            self.loan = make_loan(self.user, loan_type="SIMPLES", num_installments=60,
                                  principal=Decimal("52000"), current_balance=Decimal("52000"))
            sync_loan_installments(self.loan)
            self.payment = register_payment(self.loan, Decimal("1000"), TODAY)

    def test_edit_recalculates_interest_and_balance(self):
        with frozen_today(TODAY):
            resp = self.client.post(reverse("loan_payment_edit", args=[self.loan.pk, self.payment.pk]), {
                "payment_date": "2026-09-27", "amount_paid": "600,00", "notes": "corrigido",
            })
        self.assertEqual(resp.status_code, 302)
        self.loan.refresh_from_db()
        p = self.loan.payments.get()
        self.assertEqual(p.amount_paid, Decimal("600.00"))
        self.assertEqual(p.interest_paid, Decimal("520.00"))
        self.assertEqual(self.loan.current_balance, Decimal("51920.00"))
        self.assertEqual(p.transaction.amount, Decimal("600.00"))

    def test_edit_form_prefilled(self):
        with frozen_today(TODAY):
            resp = self.client.get(reverse("loan_payment_edit", args=[self.loan.pk, self.payment.pk]))
        self.assertContains(resp, "Editar Pagamento")
        self.assertContains(resp, 'value="1000,00"')

    def test_delete_restores_balance(self):
        with frozen_today(TODAY):
            self.client.post(reverse("loan_payment_delete", args=[self.loan.pk, self.payment.pk]))
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.current_balance, Decimal("52000.00"))
        self.assertFalse(Transaction.objects.filter(pk=self.payment.transaction_id).exists())

    def test_transaction_edit_redirects_to_payment_edit(self):
        resp = self.client.get(reverse("transaction_edit", args=[self.payment.transaction_id]))
        self.assertRedirects(resp, reverse("loan_payment_edit", args=[self.loan.pk, self.payment.pk]),
                             fetch_redirect_response=False)

    def test_transaction_delete_goes_through_loan(self):
        with frozen_today(TODAY):
            resp = self.client.post(reverse("transaction_delete", args=[self.payment.transaction_id]))
        self.assertEqual(resp.status_code, 302)
        with frozen_today(TODAY):
            self.client.post(resp.url)
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.current_balance, Decimal("52000.00"))

    def test_bulk_delete_skips_loan_payments(self):
        self.client.post(reverse("transaction_bulk_delete"), {"ids": [self.payment.transaction_id]})
        self.assertTrue(Transaction.objects.filter(pk=self.payment.transaction_id).exists())

    def test_list_labels_payment_actions(self):
        with frozen_today(TODAY):
            resp = self.client.get(reverse("transaction_list"))
        self.assertContains(resp, "Editar pagamento")
