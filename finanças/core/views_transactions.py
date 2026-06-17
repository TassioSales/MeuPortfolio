"""Transaction CRUD + import view."""
import calendar
import csv
import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import ImportFileForm, TransactionForm
from .models import Category, RecurringTransaction, Transaction


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
    if request.method == "POST":
        form = ImportFileForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES["file"]
            try:
                decoded_file = csv_file.read().decode("utf-8").splitlines()
                reader = csv.reader(decoded_file)
                next(reader, None)

                count = 0
                for row in reader:
                    if len(row) >= 3:
                        date_str = row[0].strip()
                        description = row[1].strip()
                        amount = float(row[2].strip())
                        category_name = row[3].strip() if len(row) > 3 else None
                        type_ = "RECEITA" if amount > 0 else "DESPESA"

                        category = None
                        if category_name:
                            category, _ = Category.objects.get_or_create(
                                user=request.user,
                                name=category_name,
                                defaults={"type": type_},
                            )

                        Transaction.objects.create(
                            user=request.user,
                            date=date_str,
                            description=description,
                            amount=abs(amount),
                            type=type_,
                            category=category,
                        )
                        count += 1
                messages.success(request, f"{count} transações importadas com sucesso!")
                return redirect("transaction_list")
            except Exception as e:
                messages.error(request, f"Erro ao importar arquivo: {e}")
    else:
        form = ImportFileForm()

    return render(request, "core/import.html", {"form": form})
