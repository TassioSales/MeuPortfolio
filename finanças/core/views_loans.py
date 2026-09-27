"""Loan management views — create, track, and simulate loans with full amortization.

A matemática e a integração com as transações ficam em `services_loans`.
"""
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, ListView, UpdateView
from loguru import logger as log

from .dates import today
from .forms import LoanAddFundsForm, LoanForm, LoanPaymentForm
from .models import AuditLog, Loan, LoanPayment
from .services_loans import (
    add_funds, build_schedule, calc_cet, delete_loan, monthly_rate, next_payment_amount,
    on_loan_saved, payoff_months, pending_installments, register_payment, revert_payment,
)

# Nomes antigos mantidos para quem importava daqui.
_build_schedule = build_schedule
_calc_cet = calc_cet


class LoanListView(LoginRequiredMixin, ListView):
    model = Loan
    template_name = "core/loan_list.html"
    context_object_name = "loans"

    def get_queryset(self):
        return Loan.objects.filter(user=self.request.user).annotate(
            total_paid_sum=Sum("payments__amount_paid")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        loans = list(context["loans"])
        t = today()
        next_by_loan = {}
        for tx in pending_installments_for(self.request.user):
            next_by_loan.setdefault(tx.loan_id, tx)

        total_debt = Decimal("0")
        total_next = Decimal("0")
        month_total = Decimal("0")
        active_count = 0
        for loan in loans:
            loan.next_installment = next_by_loan.get(loan.pk)
            loan.min_payment_display = (
                loan.next_installment.amount if loan.next_installment else next_payment_amount(loan)
            )
            loan.pct_paid = (
                round((1 - float(loan.current_balance) / float(loan.principal)) * 100, 1)
                if loan.principal else 100
            )
            loan.pct_paid = max(0, min(100, loan.pct_paid))
            if loan.is_active and loan.current_balance > 0:
                active_count += 1
                total_debt += loan.current_balance
                total_next += loan.min_payment_display
                nxt = loan.next_installment
                if nxt and nxt.date.year == t.year and nxt.date.month == t.month:
                    month_total += nxt.amount

        context.update(
            loans=loans,
            total_debt=total_debt,
            total_min_next=total_next,
            month_installments=month_total,
            total_paid=sum((l.total_paid_sum or Decimal("0") for l in loans), Decimal("0")),
            active_count=active_count,
        )
        return context


def pending_installments_for(user):
    from .models import Transaction
    return (
        Transaction.objects.filter(
            user=user, origin=Transaction.ORIGIN_EMPRESTIMO, type="DESPESA",
            loan__isnull=False, loan_payment__isnull=True, date__gte=today().replace(day=1),
        ).order_by("date", "id")
    )


class LoanCreateView(LoginRequiredMixin, CreateView):
    model = Loan
    form_class = LoanForm
    template_name = "core/loan_form.html"
    success_url = reverse_lazy("loan_list")

    def get_initial(self):
        return {"register_income": True, "is_active": True, "start_date": today()}

    def form_valid(self, form):
        form.instance.user = self.request.user
        if not form.instance.current_balance:
            form.instance.current_balance = form.instance.principal
        with transaction.atomic():
            response = super().form_valid(form)
            on_loan_saved(self.object)
            AuditLog.objects.create(
                user=self.request.user, action="CREATE", model_name="Loan",
                object_id=self.object.pk,
                description=f"Empréstimo criado: {self.object.name} R$ {self.object.principal}"
            )
        log.info(f"Loan {self.object.pk} created for {self.request.user.username}")
        messages.success(self.request, "Empréstimo cadastrado! As parcelas previstas já entram nas despesas.")
        return response


class LoanUpdateView(LoginRequiredMixin, UpdateView):
    model = Loan
    form_class = LoanForm
    template_name = "core/loan_form.html"
    success_url = reverse_lazy("loan_list")

    def get_queryset(self):
        return Loan.objects.filter(user=self.request.user)

    def form_valid(self, form):
        with transaction.atomic():
            response = super().form_valid(form)
            on_loan_saved(self.object)
        messages.success(self.request, "Empréstimo atualizado! Parcelas previstas recalculadas.")
        return response


class LoanDeleteView(LoginRequiredMixin, DeleteView):
    model = Loan
    template_name = "core/confirm_delete.html"
    success_url = reverse_lazy("loan_list")

    def get_queryset(self):
        return Loan.objects.filter(user=self.request.user)

    def form_valid(self, form):
        delete_loan(self.get_object())
        messages.success(self.request, "Empréstimo excluído. Pagamentos já feitos continuam no histórico.")
        return redirect(self.success_url)


@login_required
def loan_detail(request, pk):
    loan = get_object_or_404(Loan, pk=pk, user=request.user)
    payments = list(loan.payments.select_related("transaction").order_by("-payment_date", "-id"))
    disbursements = loan.disbursements.order_by('-date')

    try:
        sim_payment = Decimal(str(request.GET.get('sim', '') or '0').replace(',', '.'))
    except Exception:
        sim_payment = Decimal("0")
    sim_payment = sim_payment if sim_payment > 0 else None

    schedule_min = build_schedule(loan)
    schedule_sim = build_schedule(loan, custom_payment=sim_payment) if sim_payment else schedule_min

    payoff_min = payoff_months(schedule_min)
    payoff_sim = payoff_months(schedule_sim)
    cet = calc_cet(loan, schedule_min)

    # Datas reais das próximas parcelas (as materializadas como transação)
    pending = list(pending_installments(loan).order_by("date")[:12])
    for i, row in enumerate(schedule_min[:12]):
        row["date"] = pending[i].date if i < len(pending) else None
        row["transaction"] = pending[i] if i < len(pending) else None

    chart_months = schedule_min[:36]
    total_future_interest = sum((m['interest'] for m in schedule_min), Decimal("0"))
    total_future_interest_sim = (
        sum((m['interest'] for m in schedule_sim), Decimal("0")) if sim_payment else None
    )
    context = {
        "loan": loan,
        "payments": payments,
        "latest_payment_id": payments[0].pk if payments else None,
        "disbursements": disbursements,
        "schedule": schedule_min[:12],
        "has_insurance": (loan.insurance_monthly or 0) > 0,
        "is_informal": not loan.num_installments,
        "payoff_months_min": payoff_min,
        "payoff_months_sim": payoff_sim,
        "sim_payment": sim_payment,
        "next_interest": (loan.current_balance * monthly_rate(loan)).quantize(Decimal("0.01")),
        "total_future_interest": total_future_interest,
        "total_future_interest_sim": total_future_interest_sim,
        "interest_savings": (
            total_future_interest - total_future_interest_sim
            if total_future_interest_sim is not None else None
        ),
        "total_future_insurance": sum((m['insurance'] for m in schedule_min), Decimal("0")),
        "cet": cet,
        "chart_labels": [f"Mês {m['month']}" for m in chart_months],
        "chart_balance": [float(m['balance']) for m in chart_months],
        "chart_interest": [float(m['interest']) for m in chart_months],
        "chart_principal": [float(m['principal']) for m in chart_months],
        "chart_sim_balance": [float(m['balance']) for m in schedule_sim[:36]] if sim_payment else None,
    }
    return render(request, "core/loan_detail.html", context)


@login_required
def loan_make_payment(request, pk):
    loan = get_object_or_404(Loan, pk=pk, user=request.user)
    next_tx = pending_installments(loan).order_by("date").first()
    suggested = next_tx.amount if next_tx else next_payment_amount(loan)

    if request.method == "POST":
        form = LoanPaymentForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount_paid']
            interest = (loan.current_balance * monthly_rate(loan)).quantize(Decimal("0.01"))
            with transaction.atomic():
                payment = register_payment(
                    loan, amount, form.cleaned_data['payment_date'], form.cleaned_data.get('notes', ''),
                )
                AuditLog.objects.create(
                    user=request.user, action="UPDATE", model_name="Loan",
                    object_id=loan.pk,
                    description=f"Pagamento R$ {amount:.2f} em {loan.name}. Saldo: R$ {payment.balance_after:.2f}"
                )
            if amount < interest:
                messages.warning(
                    request,
                    f"Atenção: o valor pago (R$ {amount:.2f}) é menor que os juros do mês "
                    f"(R$ {interest:.2f}). A dívida vai crescer!"
                )
            if payment.balance_after <= 0:
                messages.success(request, f"Parabéns! O empréstimo '{loan.name}' foi quitado!")
            else:
                messages.success(
                    request,
                    f"Pagamento de R$ {amount:.2f} registrado. "
                    f"Juros: R$ {payment.interest_paid:.2f} | Amortização: R$ {payment.principal_paid:.2f} | "
                    f"Novo saldo: R$ {payment.balance_after:.2f}"
                )
            return redirect("loan_detail", pk=loan.pk)
    else:
        form = LoanPaymentForm(initial={
            'payment_date': today(),
            'amount_paid': f"{suggested:.2f}".replace(".", ","),
        })

    context = {"loan": loan, "form": form, "suggested_min": suggested, "next_installment": next_tx}
    return render(request, "core/loan_payment.html", context)


@login_required
@require_POST
def loan_payment_revert(request, pk, payment_pk):
    loan = get_object_or_404(Loan, pk=pk, user=request.user)
    payment = get_object_or_404(LoanPayment, pk=payment_pk, loan=loan)
    try:
        with transaction.atomic():
            revert_payment(payment)
            AuditLog.objects.create(
                user=request.user, action="UPDATE", model_name="Loan", object_id=loan.pk,
                description=f"Pagamento de R$ {payment.amount_paid:.2f} desfeito em {loan.name}",
            )
        messages.success(request, "Pagamento desfeito. Saldo devedor e parcela prevista restaurados.")
    except ValueError as e:
        messages.error(request, str(e))
    return redirect("loan_detail", pk=loan.pk)


@login_required
def loan_add_funds(request, pk):
    """Add more money to an existing loan. Updates current_balance only — history is preserved."""
    loan = get_object_or_404(Loan, pk=pk, user=request.user)
    if not loan.is_active:
        messages.error(request, "Não é possível adicionar fundos a um empréstimo inativo.")
        return redirect('loan_detail', pk=pk)

    if request.method == 'POST':
        form = LoanAddFundsForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            with transaction.atomic():
                add_funds(loan, amount, form.cleaned_data['date'], form.cleaned_data.get('note', ''))
                AuditLog.objects.create(
                    user=request.user, action='UPDATE', model_name='Loan',
                    object_id=loan.pk,
                    description=f"Desembolso adicional R$ {amount:.2f} — {loan.name}. "
                                f"Novo saldo: R$ {loan.current_balance:.2f}"
                )
            messages.success(
                request,
                f"R$ {amount:.2f} adicionados ao saldo. Novo saldo devedor: R$ {loan.current_balance:.2f}. "
                f"Parcelas previstas recalculadas."
            )
            return redirect('loan_detail', pk=pk)
    else:
        form = LoanAddFundsForm(initial={'date': today()})

    context = {'loan': loan, 'form': form}
    return render(request, 'core/loan_add_funds.html', context)
