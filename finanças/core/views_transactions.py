"""Transaction CRUD + import view."""
import calendar
import csv
import datetime
import io
import uuid

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.functional import cached_property
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from django.db import transaction as db_transaction

from .analytics import (
    TxFilter, by_payment_method, by_subcategory, filter_ui_context, kpis_with_comparison,
    monthly_series,
)
from .dates import add_months, month_bounds, month_label, today
from .forms import ImportFileForm, TransactionBulkUpdateForm, TransactionForm
from .models import Budget, Category, RecurringTransaction, Transaction
from .money import split_installments
from .services import next_occurrence
from loguru import logger as log

_DATE_FORMATS = [
    "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y",
    "%m/%d/%Y", "%d/%m/%y", "%Y/%m/%d",
]


def _parse_date(value: str):
    value = str(value).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Data inválida: '{value}' — use DD/MM/AAAA ou AAAA-MM-DD")


def _parse_rows_csv(file_bytes: bytes) -> list[dict]:
    text = file_bytes.decode("utf-8-sig").splitlines()
    reader = csv.reader(text)
    next(reader, None)
    rows = []
    for i, row in enumerate(reader, start=2):
        if len(row) < 3:
            continue
        try:
            date = _parse_date(row[0])
            description = row[1].strip()
            raw = row[2].strip().replace("R$", "").replace(".", "").replace(",", ".").strip()
            amount = float(raw)
            category_name = row[3].strip() if len(row) > 3 else ""
            rows.append({"row": i, "date": date, "description": description,
                         "amount": amount, "category": category_name, "error": None})
        except Exception as e:
            rows.append({"row": i, "date": None, "description": "", "amount": 0,
                         "category": "", "error": str(e)})
    return rows


def _parse_rows_xlsx(file_bytes: bytes) -> list[dict]:
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    ws = wb.active
    rows = []
    first = True
    for i, row in enumerate(ws.iter_rows(values_only=True), start=1):
        if first:
            first = False
            continue
        if not any(row):
            continue
        try:
            raw_date = row[0]
            if isinstance(raw_date, (datetime.datetime, datetime.date)):
                date = raw_date.date() if isinstance(raw_date, datetime.datetime) else raw_date
            else:
                date = _parse_date(str(raw_date))
            description = str(row[1]).strip()
            raw_val = str(row[2]).replace("R$", "").replace(".", "").replace(",", ".").strip()
            amount = float(raw_val)
            category_name = str(row[3]).strip() if len(row) > 3 and row[3] else ""
            rows.append({"row": i + 1, "date": date, "description": description,
                         "amount": amount, "category": category_name, "error": None})
        except Exception as e:
            rows.append({"row": i + 1, "date": None, "description": "", "amount": 0,
                         "category": "", "error": str(e)})
    wb.close()
    return rows


PER_PAGE_CHOICES = (25, 50, 100)


class TransactionListView(LoginRequiredMixin, ListView):
    model = Transaction
    template_name = "core/transaction_list.html"
    context_object_name = "transactions"
    paginate_by = 25

    def get_paginate_by(self, queryset):
        per_page = self.request.GET.get("per_page", "")
        return int(per_page) if per_page.isdigit() and int(per_page) in PER_PAGE_CHOICES else 25

    @cached_property
    def filter(self):
        return TxFilter.from_request(self.request, default_preset="all")

    def get_queryset(self):
        qs = self.filter.apply().select_related("category", "category__parent", "account", "loan")
        return self.filter.ordered(qs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        flt = self.filter
        user = self.request.user
        per_page = self.get_paginate_by(None)
        per_page_param = per_page if per_page != 25 else None
        context.update(filter_ui_context(flt, per_page=per_page_param))
        context.update(
            kpis=kpis_with_comparison(flt),
            per_page=per_page,
            per_page_choices=PER_PAGE_CHOICES,
            page_qs=flt.querystring(per_page=per_page_param),
            current_qs=self.request.GET.urlencode(),
            sort_links=_sort_links(flt, per_page_param),
            page_total=_page_totals(context["transactions"]),
            bulk_form=TransactionBulkUpdateForm(user),
            today=today(),
        )
        cat = flt.single_category
        if cat:
            context["category_insight"] = category_insight(flt, cat)
        return context


def _sort_links(flt, per_page_param):
    """Para cada coluna: querystring que alterna asc/desc e o ícone atual."""
    links = {}
    for col, default_desc in (("date", True), ("amount", True), ("description", False), ("created", True)):
        if flt.sort.lstrip("-") == col:
            nxt = col if flt.sort.startswith("-") else f"-{col}"
            icon = "bi-sort-down" if flt.sort.startswith("-") else "bi-sort-up"
        else:
            nxt = f"-{col}" if default_desc else col
            icon = ""
        links[col] = {
            "qs": flt.querystring(sort=nxt if nxt != "-date" else None, per_page=per_page_param),
            "icon": icon,
        }
    return links


def _page_totals(page_transactions):
    income = sum((t.amount for t in page_transactions if t.type == "RECEITA"), Decimal("0"))
    expense = sum((t.amount for t in page_transactions if t.type == "DESPESA"), Decimal("0"))
    return {"income": income, "expense": expense, "net": income - expense}


def category_insight(flt, cat):
    """Painel da categoria selecionada: total, participação, orçamento,
    evolução de 12 meses e quebras por subcategoria/forma de pagamento."""
    type_ = cat.type
    cat_qs = flt.apply().filter(type=type_)
    agg = cat_qs.aggregate(t=Sum("amount"))
    total = agg["t"] or Decimal("0")
    all_total = flt.apply(category=False).filter(type=type_).aggregate(t=Sum("amount"))["t"] or Decimal("0")
    share = (total / all_total * 100) if all_total else None

    anchor = (flt.end or today()).replace(day=1)
    first = add_months(anchor, -11, day=1)
    series = monthly_series(flt.apply(period=False).filter(type=type_), first, anchor)
    values = series["expense"] if type_ == "DESPESA" else series["income"]
    nonzero = [v for v in values if v]
    avg = round(sum(nonzero) / len(nonzero), 2) if nonzero else 0

    budget_info = None
    budget = Budget.objects.filter(user=flt.user, category=cat).order_by("-start_date").first()
    if budget and type_ == "DESPESA":
        if budget.period == "MENSAL":
            ref = flt.anchor if flt.preset == "month" and flt.anchor else today().replace(day=1)
            b_start, b_end = month_bounds(ref.year, ref.month)
            period_label = month_label(b_start, short=False)
        else:
            ref = flt.anchor or today()
            b_start, b_end = datetime.date(ref.year, 1, 1), datetime.date(ref.year, 12, 31)
            period_label = str(ref.year)
        spent = (
            Transaction.objects.filter(user=flt.user, type="DESPESA", category_id__in=flt.category_ids,
                                       date__gte=b_start, date__lte=b_end)
            .aggregate(t=Sum("amount"))["t"] or Decimal("0")
        )
        t = today()
        projected = None
        if b_start <= t <= b_end:
            elapsed = (t - b_start).days + 1
            projected = spent / elapsed * ((b_end - b_start).days + 1)
        budget_info = {
            "budget": budget, "spent": spent, "remaining": budget.limit - spent,
            "pct": min(float(spent / budget.limit * 100), 999) if budget.limit else 0,
            "projected": projected, "period_label": period_label,
        }

    return {
        "category": cat,
        "type": type_,
        "total": total,
        "count": cat_qs.count(),
        "share": share,
        "all_total": all_total,
        "series_labels": series["labels"],
        "series_values": values,
        "series_avg": avg,
        "subcategories": by_subcategory(flt.apply(), cat) if cat.subcategories.exists() else [],
        "payment_methods": by_payment_method(flt.apply(), type_=type_),
        "budget": budget_info,
    }


class TransactionCreateView(LoginRequiredMixin, CreateView):
    model = Transaction
    form_class = TransactionForm
    template_name = "core/form.html"
    success_url = reverse_lazy("transaction_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user

        payment_method = form.cleaned_data.get("payment_method")
        if payment_method == "CREDITO":
            installments = form.cleaned_data.get("installments") or 1
            first_due_date = form.cleaned_data.get("first_due_date")
            total_amount = form.cleaned_data.get("amount")
            description = form.cleaned_data.get("description")
            category = form.cleaned_data.get("category")
            group = uuid.uuid4()

            with db_transaction.atomic():
                for i, part in enumerate(split_installments(total_amount, installments)):
                    Transaction.objects.create(
                        user=self.request.user,
                        category=category,
                        type=form.cleaned_data.get("type") or "DESPESA",
                        amount=part,
                        date=add_months(first_due_date, i),
                        payment_method="CREDITO",
                        account=form.cleaned_data.get("account"),
                        description=f"{description} ({i + 1}/{installments})",
                        origin=Transaction.ORIGIN_PARCELA,
                        installment_group=group,
                        installment_number=i + 1,
                        installment_total=installments,
                    )
            messages.success(self.request, f"{installments} parcelas criadas com sucesso!")
            return redirect(self.success_url)

        recurring = form.cleaned_data.get("recurring")
        if recurring:
            frequency = form.cleaned_data.get("frequency")
            recurrence_end_date = form.cleaned_data.get("recurrence_end_date")
            with db_transaction.atomic():
                rt = RecurringTransaction.objects.create(
                    user=self.request.user,
                    category=form.instance.category,
                    type=form.instance.type,
                    amount=form.instance.amount,
                    payment_method=form.instance.payment_method,
                    frequency=frequency,
                    description=form.instance.description,
                    next_run_date=next_occurrence(form.instance.date, frequency),
                    end_date=recurrence_end_date,
                    active=True,
                )
                form.instance.origin = Transaction.ORIGIN_RECORRENTE
                form.instance.recurring_source = rt
                response = super().form_valid(form)
            messages.success(self.request, "Transação recorrente criada com sucesso!")
            return response

        return super().form_valid(form)


class TransactionUpdateView(LoginRequiredMixin, UpdateView):
    model = Transaction
    form_class = TransactionForm
    template_name = "core/form.html"
    success_url = reverse_lazy("transaction_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    def form_valid(self, form):
        scope = form.cleaned_data.get("apply_scope") or TransactionForm.SCOPE_ONLY
        with db_transaction.atomic():
            response = super().form_valid(form)
            tx = self.object
            if scope != TransactionForm.SCOPE_ONLY:
                others = _siblings(tx, scope).exclude(pk=tx.pk)
                n = others.update(
                    category=tx.category, type=tx.type, payment_method=tx.payment_method,
                    account=tx.account, amount=tx.amount,
                )
                if tx.installment_group:
                    base = tx.description.rsplit(" (", 1)[0]
                    for sib in others:
                        sib.description = f"{base} ({sib.installment_number}/{sib.installment_total})"
                        sib.save(update_fields=["description"])
                elif tx.recurring_source_id:
                    others.update(description=tx.description)
                    rt = tx.recurring_source
                    rt.amount, rt.category, rt.type = tx.amount, tx.category, tx.type
                    rt.payment_method = tx.payment_method
                    rt.description = tx.description.replace(" (Recorrente)", "")
                    rt.save()
                messages.success(self.request, f"Lançamento atualizado (+{n} relacionado(s)).")
        return response


def _siblings(tx, scope):
    """Lançamentos ligados a `tx` (mesma compra parcelada ou mesma recorrência)."""
    if tx.installment_group:
        qs = Transaction.objects.filter(user=tx.user, installment_group=tx.installment_group)
        if scope == TransactionForm.SCOPE_NEXT and tx.installment_number:
            qs = qs.filter(installment_number__gte=tx.installment_number)
        return qs
    if tx.recurring_source_id:
        return Transaction.objects.filter(user=tx.user, recurring_source_id=tx.recurring_source_id,
                                          date__gte=tx.date)
    return Transaction.objects.filter(pk=tx.pk)


class TransactionDeleteView(LoginRequiredMixin, DeleteView):
    model = Transaction
    template_name = "core/confirm_delete.html"
    success_url = reverse_lazy("transaction_list")

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tx = self.object
        if tx.installment_group:
            context["scope_choices"] = [
                ("only", "Só esta parcela"),
                ("next", "Esta e as próximas parcelas"),
                ("all", "Todas as parcelas desta compra"),
            ]
        elif tx.recurring_source_id:
            context["scope_choices"] = [
                ("only", "Só esta ocorrência"),
                ("next", "Esta e as próximas (encerra a recorrência)"),
            ]
        if tx.loan_id:
            context["delete_warning"] = (
                "Este lançamento pertence a um empréstimo. Para desfazer um pagamento use a tela do "
                "empréstimo; parcelas previstas excluídas voltam quando o empréstimo for recalculado."
            )
        return context

    def form_valid(self, form):
        tx = self.object
        scope = self.request.POST.get("scope", "only")
        with db_transaction.atomic():
            if scope in ("next", "all") and (tx.installment_group or tx.recurring_source_id):
                qs = _siblings(tx, scope)
                if tx.recurring_source_id and scope == "next":
                    rt = tx.recurring_source
                    rt.active = False
                    rt.save(update_fields=["active"])
                count = qs.count()
                qs.delete()
                messages.success(self.request, f"{count} lançamento(s) excluído(s).")
                return redirect(self.success_url)
            tx.delete()
        messages.success(self.request, "Lançamento excluído.")
        return redirect(self.success_url)


@login_required
@require_POST
def transaction_bulk_delete(request):
    ids = request.POST.getlist("ids")
    qs = Transaction.objects.filter(user=request.user, pk__in=ids)
    # Count before deleting: qs.delete()'s own count includes any cascaded
    # related rows (e.g. a linked Investment), not just these transactions.
    count = qs.count()
    qs.delete()
    if count:
        messages.success(request, f"{count} transação(ões) excluída(s) com sucesso!")
    else:
        messages.info(request, "Nenhuma transação selecionada.")
    return _back_to_list(request)


@login_required
@require_POST
def transaction_bulk_update(request):
    ids = request.POST.getlist("ids")
    form = TransactionBulkUpdateForm(request.user, request.POST)
    qs = Transaction.objects.filter(user=request.user, pk__in=ids)
    if not ids or not form.is_valid():
        messages.info(request, "Nenhuma transação selecionada.")
        return _back_to_list(request)
    changes = {k: v for k, v in form.cleaned_data.items() if v}
    if not changes:
        messages.info(request, "Escolha ao menos um campo para alterar.")
        return _back_to_list(request)
    count = qs.update(**changes)
    messages.success(request, f"{count} transação(ões) atualizada(s).")
    return _back_to_list(request)


def _back_to_list(request):
    qs = request.POST.get("return_qs", "")
    url = reverse("transaction_list")
    return redirect(f"{url}?{qs}" if qs else url)


@login_required
def transaction_duplicate(request, pk):
    """Abre o formulário de novo lançamento pré-preenchido com os dados de `pk`."""
    src = get_object_or_404(Transaction, pk=pk, user=request.user)
    description = src.description or ""
    if src.installment_group:
        description = description.rsplit(" (", 1)[0]
    description = description.replace(" (Recorrente)", "")
    form = TransactionForm(user=request.user, initial={
        "category": src.category_id, "type": src.type, "amount": f"{src.amount:.2f}",
        "date": today(), "payment_method": "PIX" if src.payment_method == "CREDITO" else src.payment_method,
        "account": src.account_id, "description": description,
    })
    return render(request, "core/form.html", {"form": form, "form_action": reverse("transaction_add")})


@login_required
def import_transactions(request):
    # ── Step 2: Confirm import (rows stored in session) ───────────────────────
    if request.method == "POST" and request.POST.get("action") == "confirm":
        import json
        rows_json = request.session.pop("import_rows", "[]")
        rows = json.loads(rows_json)
        count = 0
        for r in rows:
            if r.get("skip"):
                continue
            try:
                date = datetime.date.fromisoformat(r["date"])
                amount = float(r["amount"])
                type_ = "RECEITA" if amount > 0 else "DESPESA"
                category = None
                if r.get("category"):
                    category, _ = Category.objects.get_or_create(
                        user=request.user,
                        name=r["category"],
                        defaults={"type": type_},
                    )
                Transaction.objects.create(
                    user=request.user,
                    date=date,
                    description=r["description"],
                    amount=abs(amount),
                    type=type_,
                    category=category,
                    origin=Transaction.ORIGIN_IMPORTACAO,
                )
                count += 1
            except Exception as e:
                log.warning(f"Skipped import row {r.get('row', '?')} for user {request.user.username}: {e}")
                continue
        messages.success(request, f"{count} transações importadas com sucesso!")
        return redirect("transaction_list")

    # ── Step 1: Upload file → preview ─────────────────────────────────────────
    if request.method == "POST":
        form = ImportFileForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded = request.FILES["file"]
            name = uploaded.name.lower()
            file_bytes = uploaded.read()
            try:
                if name.endswith(".xlsx"):
                    rows = _parse_rows_xlsx(file_bytes)
                else:
                    rows = _parse_rows_csv(file_bytes)
            except Exception as e:
                messages.error(request, f"Erro ao ler arquivo: {e}")
                return render(request, "core/import.html", {"form": form})

            valid = [r for r in rows if not r["error"]]
            errors = [r for r in rows if r["error"]]

            # Serialise valid rows to session for confirm step
            import json
            request.session["import_rows"] = json.dumps([
                {**r, "date": r["date"].isoformat()}
                for r in valid
            ])
            return render(request, "core/import_preview.html", {
                "valid_rows": valid,
                "error_rows": errors,
                "filename": uploaded.name,
            })
    else:
        form = ImportFileForm()

    return render(request, "core/import.html", {"form": form})
