"""Bank account and transfer views."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import BankAccountForm, TransferForm
from .models import AuditLog, BankAccount, Transfer


class BankAccountListView(LoginRequiredMixin, ListView):
    model = BankAccount
    template_name = "core/account_list.html"
    context_object_name = "accounts"

    def get_queryset(self):
        return BankAccount.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["transfers"] = Transfer.objects.filter(user=self.request.user)[:10]
        context["total_balance"] = self.get_queryset().aggregate(Sum("balance"))["balance__sum"] or 0
        return context


class BankAccountCreateView(LoginRequiredMixin, CreateView):
    model = BankAccount
    form_class = BankAccountForm
    template_name = "core/form.html"
    success_url = reverse_lazy("account_list")

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        AuditLog.objects.create(
            user=self.request.user, action="CREATE", model_name="BankAccount",
            object_id=self.object.pk, description=f"Conta criada: {self.object.name}"
        )
        messages.success(self.request, "Conta bancária criada com sucesso!")
        return response


class BankAccountUpdateView(LoginRequiredMixin, UpdateView):
    model = BankAccount
    form_class = BankAccountForm
    template_name = "core/form.html"
    success_url = reverse_lazy("account_list")

    def get_queryset(self):
        return BankAccount.objects.filter(user=self.request.user)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Conta atualizada com sucesso!")
        return response


class BankAccountDeleteView(LoginRequiredMixin, DeleteView):
    model = BankAccount
    template_name = "core/confirm_delete.html"
    success_url = reverse_lazy("account_list")

    def get_queryset(self):
        return BankAccount.objects.filter(user=self.request.user)


@login_required
def transfer_create(request):
    if request.method == "POST":
        form = TransferForm(request.user, request.POST)
        if form.is_valid():
            transfer = form.save(commit=False)
            transfer.user = request.user
            transfer.save()
            # Update account balances
            transfer.from_account.balance -= transfer.amount
            transfer.from_account.save()
            transfer.to_account.balance += transfer.amount
            transfer.to_account.save()
            AuditLog.objects.create(
                user=request.user, action="CREATE", model_name="Transfer",
                object_id=transfer.pk,
                description=f"Transferência R$ {transfer.amount} de {transfer.from_account} para {transfer.to_account}"
            )
            messages.success(request, "Transferência realizada com sucesso!")
            return redirect("account_list")
    else:
        form = TransferForm(request.user)
    return render(request, "core/transfer_form.html", {"form": form})
