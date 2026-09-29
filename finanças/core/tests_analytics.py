import datetime
import uuid
from decimal import Decimal

from django.contrib.auth.models import User
from django.http import QueryDict
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .analytics import TxFilter, by_category, kpis, recent
from .models import Budget, Category, Transaction
from .money import split_installments
from .testing import frozen_today

TODAY = datetime.date(2026, 9, 27)


def tx(user, amount, date, type_="DESPESA", category=None, **kw):
    return Transaction.objects.create(
        user=user, amount=Decimal(str(amount)), date=date, type=type_, category=category,
        description=kw.pop("description", f"tx {amount}"), **kw,
    )


class MoneyTests(TestCase):
    def test_split_installments_sums_exactly(self):
        parts = split_installments(Decimal("100"), 3)
        self.assertEqual(parts, [Decimal("33.33"), Decimal("33.33"), Decimal("33.34")])
        self.assertEqual(sum(parts), Decimal("100.00"))


class TxFilterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ana", password="x")
        self.other = User.objects.create_user("bob", password="x")
        self.food = Category.objects.create(user=self.user, name="Alimentação")
        self.market = Category.objects.create(user=self.user, name="Mercado", parent=self.food)
        self.foreign = Category.objects.create(user=self.other, name="Alheia")

    def flt(self, qs):
        with frozen_today(TODAY):
            return TxFilter.from_params(self.user, QueryDict(qs))

    def test_invalid_values_are_ignored(self):
        f = self.flt("start_date=banana&end_date=2026-13-40&category=abc&type=XYZ&min_amount=zzz")
        self.assertIsNone(f.start)
        self.assertIsNone(f.end)
        self.assertEqual(f.category_ids, ())
        self.assertIsNone(f.type)
        self.assertIsNone(f.min_amount)

    def test_other_users_category_is_dropped(self):
        f = self.flt(f"category={self.foreign.id}")
        self.assertEqual(f.selected_categories, ())

    def test_parent_category_includes_children(self):
        f = self.flt(f"category={self.food.id}")
        self.assertEqual(set(f.category_ids), {self.food.id, self.market.id})

    def test_month_preset_and_navigation(self):
        f = self.flt("period=month&month=2&year=2026")
        self.assertEqual((f.start, f.end), (datetime.date(2026, 2, 1), datetime.date(2026, 2, 28)))
        prev = f.shifted(-1)
        self.assertEqual(prev.start, datetime.date(2026, 1, 1))
        self.assertEqual(f.previous_period().end, datetime.date(2026, 1, 31))

    def test_3m_preset(self):
        f = self.flt("period=3m&month=9&year=2026")
        self.assertEqual((f.start, f.end), (datetime.date(2026, 7, 1), datetime.date(2026, 9, 30)))

    def test_legacy_date_params_become_custom(self):
        f = self.flt("start_date=2026-01-01&end_date=2026-01-31")
        self.assertEqual(f.preset, "custom")
        self.assertEqual(f.days, 31)

    def test_querystring_round_trip(self):
        f = self.flt(f"period=3m&category={self.food.id}&payment=PIX&search=pão")
        again = self.flt(f.querystring())
        self.assertEqual(again.selected_categories, f.selected_categories)
        self.assertEqual(again.payment_methods, ("PIX",))
        self.assertEqual(again.search, "pão")
        self.assertEqual(again.preset, "3m")

    def test_exclusion_toggles(self):
        inv = Category.objects.create(user=self.user, name="Investimentos", nature=Category.NATURE_INVESTIMENTO)
        tx(self.user, 100, TODAY, category=self.food)
        tx(self.user, 500, TODAY, category=inv, origin=Transaction.ORIGIN_INVESTIMENTO)
        tx(self.user, 300, TODAY, origin=Transaction.ORIGIN_EMPRESTIMO)
        with frozen_today(TODAY):
            f = TxFilter.from_params(self.user, QueryDict("loans=0&investments=0"))
            self.assertEqual(kpis(f.apply())["expense"], Decimal("100"))
            f = TxFilter.from_params(self.user, QueryDict(""))
            self.assertEqual(kpis(f.apply())["expense"], Decimal("900"))


class KpiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("carla", password="x")

    def test_kpis_split_realized_and_forecast(self):
        tx(self.user, 1000, TODAY, type_="RECEITA")
        tx(self.user, 200, TODAY - datetime.timedelta(days=1))
        tx(self.user, 50, TODAY + datetime.timedelta(days=3), payment_method="CREDITO")
        with frozen_today(TODAY):
            k = kpis(Transaction.objects.filter(user=self.user))
        self.assertEqual(k["income"], Decimal("1000"))
        self.assertEqual(k["expense"], Decimal("250"))
        self.assertEqual(k["expense_realized"], Decimal("200"))
        self.assertEqual(k["expense_forecast"], Decimal("50"))
        self.assertEqual(k["expense_card"], Decimal("50"))
        self.assertEqual(k["net"], Decimal("750"))
        self.assertEqual(k["savings_rate"], Decimal("75"))

    def test_by_category_rolls_up_to_root(self):
        food = Category.objects.create(user=self.user, name="Alimentação")
        market = Category.objects.create(user=self.user, name="Mercado", parent=food)
        tx(self.user, 100, TODAY, category=food)
        tx(self.user, 50, TODAY, category=market)
        rows = by_category(Transaction.objects.filter(user=self.user))
        self.assertEqual(rows[0]["name"], "Alimentação")
        self.assertEqual(rows[0]["total"], Decimal("150"))


class RecentFeedTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("davi", password="x")

    def test_recent_orders_by_creation_not_by_date_or_amount(self):
        # Parcelas futuras grandes criadas antes; um lançamento pequeno criado por último.
        group = uuid.uuid4()
        for i in range(10):
            tx(self.user, 900, TODAY + datetime.timedelta(days=30 * i), payment_method="CREDITO",
               origin=Transaction.ORIGIN_PARCELA, installment_group=group,
               installment_number=i + 1, installment_total=10, description=f"TV ({i + 1}/10)")
        small = tx(self.user, 12.5, TODAY - datetime.timedelta(days=2), description="Padaria")
        with frozen_today(TODAY):
            items = recent(self.user, limit=5)
        self.assertEqual(items[0]["tx"].pk, small.pk)
        # As 10 parcelas viram um único item agrupado.
        self.assertEqual(len(items), 2)
        self.assertEqual(items[1]["kind"], "grp")
        self.assertEqual(items[1]["count"], 10)
        self.assertEqual(items[1]["title"], "TV")


class TransactionListViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("eva", password="x")
        self.client.login(username="eva", password="x")
        self.food = Category.objects.create(user=self.user, name="Alimentação")
        self.market = Category.objects.create(user=self.user, name="Mercado", parent=self.food)
        self.fun = Category.objects.create(user=self.user, name="Lazer")
        tx(self.user, 1000, TODAY, type_="RECEITA")
        tx(self.user, 100, TODAY, category=self.food)
        tx(self.user, 60, TODAY, category=self.market)
        tx(self.user, 40, TODAY, category=self.fun)

    def get(self, qs=""):
        with frozen_today(TODAY):
            return self.client.get(reverse("transaction_list") + ("?" + qs if qs else ""))

    def test_invalid_querystring_does_not_500(self):
        resp = self.get("start_date=xx&end_date=yy&category=abc&sort=hack&per_page=9999")
        self.assertEqual(resp.status_code, 200)

    def test_kpis_cover_all_pages(self):
        for i in range(30):
            tx(self.user, 1, TODAY)
        resp = self.get()
        self.assertEqual(resp.context["kpis"]["count"], 34)
        self.assertEqual(resp.context["kpis"]["expense"], Decimal("230"))
        self.assertEqual(len(resp.context["transactions"]), 25)

    def test_category_insight_totals_and_share(self):
        resp = self.get(f"category={self.food.id}")
        ci = resp.context["category_insight"]
        self.assertEqual(ci["total"], Decimal("160"))  # inclui a subcategoria Mercado
        self.assertEqual(ci["all_total"], Decimal("200"))
        self.assertEqual(ci["share"], Decimal("80"))
        self.assertEqual(len(ci["subcategories"]), 2)
        self.assertContains(resp, "Por subcategoria")

    def test_category_insight_with_budget(self):
        Budget.objects.create(user=self.user, category=self.food, limit=Decimal("200"), period="MENSAL",
                              start_date=datetime.date(2026, 1, 1))
        resp = self.get(f"category={self.food.id}&period=month&month=9&year=2026")
        self.assertEqual(resp.context["category_insight"]["budget"]["spent"], Decimal("160"))

    def test_sort_by_amount_is_stable(self):
        resp = self.get("sort=-amount")
        amounts = [t.amount for t in resp.context["transactions"]]
        self.assertEqual(amounts, sorted(amounts, reverse=True))

    def test_pagination_keeps_filters(self):
        for i in range(30):
            tx(self.user, 1, TODAY, category=self.fun)
        resp = self.get(f"category={self.fun.id}")
        self.assertIn(f"category={self.fun.id}", resp.context["page_qs"])

    def test_bulk_update_category(self):
        ids = list(Transaction.objects.filter(user=self.user, type="DESPESA").values_list("id", flat=True))
        self.client.post(reverse("transaction_bulk_update"), {"ids": ids, "category": self.fun.id})
        self.assertEqual(Transaction.objects.filter(user=self.user, category=self.fun).count(), 3)

    def test_bulk_update_ignores_other_users_rows(self):
        other = User.objects.create_user("zed", password="x")
        foreign = tx(other, 10, TODAY)
        self.client.post(reverse("transaction_bulk_update"), {"ids": [foreign.id], "payment_method": "PIX"})
        foreign.refresh_from_db()
        self.assertEqual(foreign.payment_method, "DINHEIRO")

    def test_export_csv_uses_same_filter(self):
        resp = self.client.get(reverse("export_csv") + f"?category={self.food.id}")
        body = resp.content.decode()
        self.assertEqual(body.count("\n"), 3)  # cabeçalho + 2 linhas (pai + subcategoria)


class InstallmentFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("fabi", password="x")
        self.client.login(username="fabi", password="x")
        self.cat = Category.objects.create(user=self.user, name="Casa")

    def create(self):
        return self.client.post(reverse("transaction_add"), {
            "category": self.cat.id, "type": "DESPESA", "amount": "100,00", "date": "2026-09-27",
            "payment_method": "CREDITO", "description": "Cadeira", "installments": "3",
            "first_due_date": "2026-10-10",
        })

    def test_installments_sum_to_total_and_are_grouped(self):
        self.create()
        txs = list(Transaction.objects.filter(user=self.user).order_by("date"))
        self.assertEqual(sum(t.amount for t in txs), Decimal("100.00"))
        self.assertEqual(len({t.installment_group for t in txs}), 1)
        self.assertEqual([t.installment_number for t in txs], [1, 2, 3])
        self.assertTrue(all(t.origin == Transaction.ORIGIN_PARCELA for t in txs))

    def test_edit_existing_credit_installment_does_not_require_installments(self):
        self.create()
        first = Transaction.objects.filter(user=self.user).order_by("date").first()
        resp = self.client.post(reverse("transaction_edit", args=[first.pk]), {
            "category": self.cat.id, "type": "DESPESA", "amount": "40,00", "date": first.date.isoformat(),
            "payment_method": "CREDITO", "description": first.description, "apply_scope": "only",
        })
        self.assertEqual(resp.status_code, 302)

    def test_edit_all_installments(self):
        self.create()
        first = Transaction.objects.filter(user=self.user).order_by("date").first()
        self.client.post(reverse("transaction_edit", args=[first.pk]), {
            "category": self.cat.id, "type": "DESPESA", "amount": "50,00", "date": first.date.isoformat(),
            "payment_method": "CREDITO", "description": "Cadeira gamer (1/3)", "apply_scope": "all",
        })
        txs = Transaction.objects.filter(user=self.user).order_by("date")
        self.assertEqual({t.amount for t in txs}, {Decimal("50.00")})
        self.assertEqual(txs.last().description, "Cadeira gamer (3/3)")

    def test_delete_this_and_next(self):
        self.create()
        second = Transaction.objects.filter(user=self.user, installment_number=2).get()
        self.client.post(reverse("transaction_delete", args=[second.pk]), {"scope": "next"})
        self.assertEqual(list(Transaction.objects.filter(user=self.user).values_list("installment_number", flat=True)), [1])

    def test_recurring_creates_linked_source(self):
        self.client.post(reverse("transaction_add"), {
            "category": self.cat.id, "type": "DESPESA", "amount": "50,00", "date": "2026-09-01",
            "payment_method": "PIX", "description": "", "recurring": "on", "frequency": "MENSAL",
        })
        t = Transaction.objects.get(user=self.user)
        self.assertEqual(t.origin, Transaction.ORIGIN_RECORRENTE)
        self.assertIsNotNone(t.recurring_source)
        self.assertEqual(t.description, "Casa")  # descrição vazia → nome da categoria
        self.assertEqual(t.recurring_source.next_run_date, datetime.date(2026, 10, 1))

    def test_duplicate_prefills_form(self):
        self.create()
        first = Transaction.objects.filter(user=self.user).order_by("date").first()
        resp = self.client.get(reverse("transaction_duplicate", args=[first.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["form"].initial["description"], "Cadeira")
