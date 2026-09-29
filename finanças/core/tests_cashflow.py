import datetime
import uuid
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Category, Loan, RecurringTransaction, Transaction
from .services import process_recurring_transactions
from .services_cashflow import build_forecast
from .testing import frozen_today

TODAY = datetime.date(2026, 9, 15)


def tx(user, amount, date, type_="DESPESA", **kw):
    return Transaction.objects.create(user=user, amount=Decimal(str(amount)), date=date, type=type_,
                                      description=kw.pop("description", "x"), **kw)


class ForecastTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ana", password="x")

    def forecast(self, **kw):
        with frozen_today(TODAY):
            return build_forecast(self.user, **kw)

    def test_cash_today_ignores_future(self):
        tx(self.user, 1000, datetime.date(2026, 9, 1), "RECEITA")
        tx(self.user, 300, datetime.date(2027, 3, 1), payment_method="CREDITO", origin=Transaction.ORIGIN_PARCELA)
        f = self.forecast()
        self.assertEqual(f["cash_today"], Decimal("1000"))

    def test_variable_estimate_uses_median_of_past_full_months_only(self):
        for month, amount in ((6, 100), (7, 300), (8, 200)):
            tx(self.user, amount, datetime.date(2026, month, 10))
        # mês futuro e mês corrente não entram no histórico
        tx(self.user, 9999, datetime.date(2026, 11, 10))
        tx(self.user, 5000, datetime.date(2026, 9, 2))
        f = self.forecast()
        self.assertEqual([h["expense"] for h in f["history"]], [Decimal("100"), Decimal("300"), Decimal("200")])
        self.assertEqual(f["estimate"]["expense"], Decimal("200.00"))

    def test_scenarios_only_change_estimated_part(self):
        for month, amount in ((5, 100), (6, 200), (7, 300), (8, 400)):
            tx(self.user, amount, datetime.date(2026, month, 10))
        tx(self.user, 50, datetime.date(2026, 11, 5), origin=Transaction.ORIGIN_RECORRENTE)
        base = self.forecast(horizon=3)
        pess = self.forecast(horizon=3, scenario="pessimista")
        otim = self.forecast(horizon=3, scenario="otimista")
        nov = lambda f: f["months"][2]
        self.assertEqual(nov(base)["out"]["fixed"], nov(pess)["out"]["fixed"])
        self.assertGreater(nov(pess)["out"]["variable"], nov(base)["out"]["variable"])
        self.assertLess(nov(otim)["out"]["variable"], nov(base)["out"]["variable"])

    def test_materialized_recurring_is_not_double_counted(self):
        cat = Category.objects.create(user=self.user, name="Aluguel")
        RecurringTransaction.objects.create(
            user=self.user, category=cat, type="DESPESA", amount=Decimal("1000"), frequency="MENSAL",
            description="Aluguel", next_run_date=datetime.date(2026, 10, 5),
        )
        with frozen_today(TODAY):
            process_recurring_transactions(self.user, up_to_date=datetime.date(2026, 12, 31))
        f = self.forecast(horizon=3)
        self.assertEqual([m["out"]["fixed"] for m in f["months"]],
                         [Decimal("0"), Decimal("1000"), Decimal("1000"), Decimal("1000")])

    def test_current_month_is_hybrid(self):
        tx(self.user, 2000, datetime.date(2026, 9, 1), "RECEITA")
        tx(self.user, 500, datetime.date(2026, 9, 10))                 # realizado
        tx(self.user, 200, datetime.date(2026, 9, 25), origin=Transaction.ORIGIN_RECORRENTE)  # certo
        f = self.forecast(horizon=1)
        cur = f["months"][0]
        self.assertEqual(cur["opening"], Decimal("0"))
        self.assertEqual(cur["out_realized"], Decimal("500"))
        self.assertEqual(cur["out"]["fixed"], Decimal("200"))
        self.assertEqual(cur["closing"], Decimal("1300.00"))

    def test_lowest_balance_date(self):
        tx(self.user, 1000, datetime.date(2026, 9, 1), "RECEITA")
        tx(self.user, 1500, datetime.date(2026, 10, 10), origin=Transaction.ORIGIN_RECORRENTE)
        tx(self.user, 2000, datetime.date(2026, 10, 20), "RECEITA", origin=Transaction.ORIGIN_RECORRENTE)
        f = self.forecast(horizon=2)
        self.assertEqual(f["lowest"]["date"], datetime.date(2026, 10, 10))
        self.assertEqual(f["lowest"]["balance"], Decimal("-500.00"))

    def test_toggle_excludes_future_loan_installments(self):
        tx(self.user, 700, datetime.date(2026, 10, 10), origin=Transaction.ORIGIN_EMPRESTIMO)
        with_loans = self.forecast(horizon=1)
        without = self.forecast(horizon=1, include_loans=False)
        self.assertEqual(with_loans["months"][1]["out"]["loans"], Decimal("700"))
        self.assertEqual(without["months"][1]["out"]["loans"], Decimal("0"))

    def test_horizon_12(self):
        f = self.forecast(horizon=12)
        self.assertEqual(len(f["months"]), 13)


class CashFlowViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("bia", password="x")
        self.client.login(username="bia", password="x")

    def test_view_renders_all_scenarios_and_horizons(self):
        tx(self.user, 1000, datetime.date(2026, 8, 1), "RECEITA")
        tx(self.user, 300, datetime.date(2026, 8, 5))
        with frozen_today(TODAY):
            for qs in ("", "?months=12&scenario=pessimista", "?months=1&scenario=otimista&loans=0", "?months=abc"):
                resp = self.client.get(reverse("cash_flow_forecast") + qs)
                self.assertEqual(resp.status_code, 200, qs)
        self.assertContains(resp, "Extrato do futuro")
        self.assertContains(resp, "Como calculamos")

    def test_loan_installments_show_up(self):
        with frozen_today(TODAY):
            Loan.objects.create(
                user=self.user, name="Carro", lender="Banco", loan_type="PRICE",
                principal=Decimal("1200"), current_balance=Decimal("1200"), interest_rate=Decimal("1"),
                start_date=datetime.date(2026, 9, 1), due_day=10, num_installments=12, register_income=False,
            )
            resp = self.client.get(reverse("cash_flow_forecast") + "?months=3")
        months = resp.context["f"]["months"]
        self.assertEqual(months[1]["out"]["loans"], Decimal("106.62"))


class DashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("caio", password="x")
        self.client.login(username="caio", password="x")
        self.cat = Category.objects.create(user=self.user, name="Casa")

    def get(self, qs=""):
        with frozen_today(TODAY):
            return self.client.get(reverse("dashboard") + qs)

    def test_recent_activity_shows_last_created_not_biggest(self):
        group = uuid.uuid4()
        for i in range(3):
            tx(self.user, 2000, datetime.date(2026, 9, 28), payment_method="CREDITO", category=self.cat,
               origin=Transaction.ORIGIN_PARCELA, installment_group=group, installment_number=i + 1,
               installment_total=3, description=f"Sofá ({i + 1}/3)")
        tx(self.user, 9, datetime.date(2026, 9, 3), category=self.cat, description="Café")
        resp = self.get()
        items = resp.context["recent_items"]
        self.assertEqual(items[0]["title"], "Café")
        self.assertContains(resp, "Café")

    def test_loan_installments_count_in_expenses(self):
        with frozen_today(TODAY):
            Loan.objects.create(
                user=self.user, name="Tio", lender="Tio", loan_type="REDUCAO_SALDO",
                principal=Decimal("5000"), current_balance=Decimal("5000"), interest_rate=Decimal("0"),
                start_date=datetime.date(2026, 8, 1), due_day=20, planned_payment=Decimal("500"),
                register_income=False,
            )
        resp = self.get()
        self.assertEqual(resp.context["kpis"]["expense"], Decimal("500"))
        self.assertEqual(resp.context["kpis"]["expense_loans"], Decimal("500"))
        self.assertEqual(resp.context["position"]["debt"], Decimal("5000"))
        resp = self.get("?loans=0")
        self.assertEqual(resp.context["kpis"]["expense"], Decimal("0"))

    def test_investments_excluded_by_default(self):
        inv = Category.objects.create(user=self.user, name="Investimentos", nature=Category.NATURE_INVESTIMENTO)
        tx(self.user, 800, TODAY, category=inv, origin=Transaction.ORIGIN_INVESTIMENTO)
        tx(self.user, 100, TODAY, category=self.cat)
        resp = self.get()
        self.assertEqual(resp.context["kpis"]["expense"], Decimal("100"))
        resp = self.get("?investments=1")
        self.assertEqual(resp.context["kpis"]["expense"], Decimal("900"))

    def test_filters_presets_and_category(self):
        tx(self.user, 100, TODAY, category=self.cat)
        for qs in ("?period=3m", "?period=12m", "?period=year", "?period=all",
                   "?period=custom&start_date=2026-09-01&end_date=2026-09-30",
                   f"?category={self.cat.id}", "?month=13&year=abc"):
            resp = self.get(qs)
            self.assertEqual(resp.status_code, 200, qs)
        resp = self.get(f"?category={self.cat.id}")
        self.assertIn("category_insight", resp.context)

    def test_filter_is_remembered_but_not_the_month(self):
        self.get(f"?period=3m&month=1&year=2026&type=DESPESA")
        resp = self.get()
        flt = resp.context["filter"]
        self.assertEqual(flt.preset, "3m")
        self.assertEqual(flt.type, "DESPESA")
        self.assertEqual(flt.anchor, datetime.date(2026, 9, 1))
        resp = self.get("?clear=1")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self.get().context["filter"].preset, "month")

    def test_saldo_hoje_vs_projetado(self):
        tx(self.user, 1000, datetime.date(2026, 9, 1), "RECEITA", category=self.cat)
        tx(self.user, 400, datetime.date(2026, 9, 25), category=self.cat)
        resp = self.get()
        self.assertEqual(resp.context["position"]["cash"], Decimal("1000"))
        self.assertEqual(resp.context["kpis"]["end_balance"], Decimal("600"))


class DashboardMonthOutlookTests(TestCase):
    """Linha 'o mês': quanto falta pagar/receber e a parcela do empréstimo —
    sem a dívida total."""

    def setUp(self):
        self.user = User.objects.create_user("duda", password="x")
        self.client.login(username="duda", password="x")
        with frozen_today(TODAY):
            from .services_loans import on_loan_saved
            self.loan = Loan.objects.create(
                user=self.user, name="Apto", lender="Banco", loan_type="PRICE",
                principal=Decimal("1200"), current_balance=Decimal("1200"), interest_rate=Decimal("1"),
                start_date=datetime.date(2026, 9, 1), first_due_date=datetime.date(2026, 9, 20), due_day=20,
                num_installments=12, register_income=False,
            )
            on_loan_saved(self.loan)
        tx(self.user, 300, datetime.date(2026, 9, 25))
        tx(self.user, 1000, datetime.date(2026, 9, 28), "RECEITA")

    def test_first_due_date_puts_installment_in_current_month(self):
        first = self.loan.transactions.filter(type="DESPESA").order_by("date").first()
        self.assertEqual(first.date, datetime.date(2026, 9, 20))

    def test_outlook_shows_remaining_and_loan_installment(self):
        with frozen_today(TODAY):
            resp = self.client.get(reverse("dashboard"))
        mo = resp.context["month_outlook"]
        self.assertEqual(mo["loan_total"], Decimal("106.62"))
        self.assertEqual(mo["loan_next"].date, datetime.date(2026, 9, 20))
        self.assertEqual(mo["to_pay"], Decimal("406.62"))    # parcela + conta do dia 25
        self.assertEqual(mo["to_receive"], Decimal("1000"))
        self.assertNotContains(resp, "Patrimônio líquido")
        self.assertNotContains(resp, "Dívida de empréstimos")

    def test_projected_balance_includes_next_installment(self):
        with frozen_today(TODAY):
            resp = self.client.get(reverse("dashboard"))
        k = resp.context["kpis"]
        # saldo hoje 0 + 1000 a receber − (106,62 + 300) a pagar
        self.assertEqual(k["end_balance"], Decimal("593.38"))
        self.assertContains(resp, "a pagar até")

    def test_form_first_due_date_sets_due_day(self):
        with frozen_today(TODAY):
            self.client.post(reverse("loan_edit", args=[self.loan.pk]), {
                "name": "Apto", "lender": "Banco", "loan_type": "PRICE", "principal": "1.200,00",
                "current_balance": "1.200,00", "interest_rate": "1", "interest_period": "MENSAL",
                "start_date": "2026-09-01", "first_due_date": "2026-10-05", "due_day": "20",
                "num_installments": "12", "is_active": "True",
            })
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.due_day, 5)
        dates = list(self.loan.transactions.filter(type="DESPESA").order_by("date").values_list("date", flat=True)[:2])
        self.assertEqual(dates, [datetime.date(2026, 10, 5), datetime.date(2026, 11, 5)])
