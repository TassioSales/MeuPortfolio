"""Transaction CRUD + import view."""
import calendar
import csv
import datetime
import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import ImportFileForm, TransactionForm
from .models import Category, RecurringTransaction, Transaction

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


class TransactionListView(LoginRequiredMixin, ListView):
    model = Transaction
    template_name = "core/transaction_list.html"
    context_object_name = "transactions"

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user).order_by("-date")


class TransactionCreateView(LoginRequiredMixin, CreateView):
    model = Transaction
    form_class = TransactionForm
    template_name = "core/form.html"
    success_url = reverse_lazy("transaction_list")

    def form_valid(self, form):
        form.instance.user = self.request.user

        payment_method = form.cleaned_data.get("payment_method")
        if payment_method == "CREDITO":
            installments = form.cleaned_data.get("installments")
            first_due_date = form.cleaned_data.get("first_due_date")
            total_amount = form.cleaned_data.get("amount")
            description = form.cleaned_data.get("description")
            category = form.cleaned_data.get("category")

            installment_amount = total_amount / installments
            for i in range(installments):
                month = first_due_date.month - 1 + i
                year = first_due_date.year + month // 12
                month = month % 12 + 1
                day = min(first_due_date.day, calendar.monthrange(year, month)[1])
                due_date = datetime.date(year, month, day)
                Transaction.objects.create(
                    user=self.request.user,
                    category=category,
                    type="DESPESA",
                    amount=installment_amount,
                    date=due_date,
                    payment_method="CREDITO",
                    description=f"{description} ({i + 1}/{installments})",
                )
            messages.success(self.request, f"{installments} parcelas criadas com sucesso!")
            return redirect(self.success_url)

        recurring = form.cleaned_data.get("recurring")
        if recurring:
            frequency = form.cleaned_data.get("frequency")
            response = super().form_valid(form)

            next_date = form.instance.date
            if frequency == "DIARIO":
                next_date += datetime.timedelta(days=1)
            elif frequency == "SEMANAL":
                next_date += datetime.timedelta(weeks=1)
            elif frequency == "QUINZENAL":
                next_date += datetime.timedelta(days=15)
            elif frequency == "MENSAL":
                m = next_date.month - 1 + 1
                y = next_date.year + m // 12
                m = m % 12 + 1
                d = min(next_date.day, calendar.monthrange(y, m)[1])
                next_date = datetime.date(y, m, d)
            elif frequency == "ANUAL":
                next_date = next_date.replace(year=next_date.year + 1)

            RecurringTransaction.objects.create(
                user=self.request.user,
                category=form.instance.category,
                type=form.instance.type,
                amount=form.instance.amount,
                payment_method=form.instance.payment_method,
                frequency=frequency,
                description=form.instance.description,
                next_run_date=next_date,
                active=True,
            )
            messages.success(self.request, "Transação recorrente criada com sucesso!")
            return response

        return super().form_valid(form)


class TransactionUpdateView(LoginRequiredMixin, UpdateView):
    model = Transaction
    form_class = TransactionForm
    template_name = "core/form.html"
    success_url = reverse_lazy("transaction_list")

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)


class TransactionDeleteView(LoginRequiredMixin, DeleteView):
    model = Transaction
    template_name = "core/confirm_delete.html"
    success_url = reverse_lazy("transaction_list")

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)


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
                )
                count += 1
            except Exception:
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
