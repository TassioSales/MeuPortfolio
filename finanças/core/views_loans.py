"""Loan management views — create, track, and schedule loans with amortization."""
import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import LoanForm, LoanPaymentForm
from .models import AuditLog, Loan, LoanPayment, Transaction, Category


def _price_pmt(pv: float, r: float, n: int) -> float:
    """Fixed payment for Price (French amortization) table."""
    if r == 0:
        return pv / n
    return pv * r / (1 - (1 + r) ** -n)


def _build_schedule(loan: Loan, months: int = 36, custom_payment: float = None) -> list:
    """
    Build forward-looking amortization schedule starting from current_balance.
    Returns list of monthly dicts: {month, payment, interest, principal, balance}.
    """
    balance = float(loan.current_balance)
    r = loan.monthly_rate
    schedule = []

    if loan.loan_type == 'PRICE':
        n = loan.num_installments or 12
        pmt = _price_pmt(float(loan.principal), r, n)
        # Estimate remaining installments from paid count
        paid = loan.payments.count()
        remaining = max(n - paid, 1)
        for i in range(min(remaining, months)):
            interest = balance * r
            principal = pmt - interest
            if principal > balance:
                principal = balance
                pmt = interest + principal
            balance -= principal
            schedule.append({
                'month': i + 1,
                'payment': round(pmt, 2),
                'interest': round(interest, 2),
                'principal': round(principal, 2),
                'balance': round(max(balance, 0), 2),
            })
            if balance <= 0.01:
                break

    elif loan.loan_type == 'SAC':
        n = loan.num_installments or 12
        paid = loan.payments.count()
        remaining = max(n - paid, 1)
        fixed_principal = float(loan.principal) / n
        for i in range(min(remaining, months)):
            interest = balance * r
            principal = min(fixed_principal, balance)
            payment = interest + principal
            balance -= principal
            schedule.append({
                'month': i + 1,
                'payment': round(payment, 2),
                'interest': round(interest, 2),
                'principal': round(principal, 2),
                'balance': round(max(balance, 0), 2),
            })
            if balance <= 0.01:
                break

    elif loan.loan_type == 'SIMPLES':
        # Pay only interest each month; full principal at end
        interest = balance * r
        n = loan.num_installments or months
        paid = loan.payments.count()
        remaining = max(n - paid, 1)
        for i in range(min(remaining, months)):
            is_last = (i == remaining - 1)
            payment = interest + (balance if is_last else 0)
            principal = balance if is_last else 0
            new_balance = 0 if is_last else balance
            schedule.append({
                'month': i + 1,
                'payment': round(payment, 2),
                'interest': round(interest, 2),
                'principal': round(principal, 2),
                'balance': round(new_balance, 2),
            })
            if is_last:
                break

    else:  # REDUCAO_SALDO — the most flexible
        pmt = custom_payment if custom_payment else (balance * r)  # default: interest-only
        for i in range(months):
            interest = balance * r
            if pmt < interest:
                pmt = interest  # never let debt grow
            principal = pmt - interest
            if principal > balance:
                principal = balance
                pmt_actual = interest + principal
            else:
                pmt_actual = pmt
            balance -= principal
            schedule.append({
                'month': i + 1,
                'payment': round(pmt_actual, 2),
                'interest': round(interest, 2),
                'principal': round(principal, 2),
                'balance': round(max(balance, 0), 2),
            })
            if balance <= 0.01:
                break

    return schedule


def _payoff_months(loan: Loan, monthly_payment: float):
    """Estimate how many months until paid off with a fixed monthly_payment."""
    balance = float(loan.current_balance)
    r = loan.monthly_rate
    if monthly_payment <= balance * r and r > 0:
        return None  # Never pays off
    count = 0
    for _ in range(600):  # cap at 50 years
        interest = balance * r
        principal = monthly_payment - interest
        balance -= principal
        count += 1
        if balance <= 0.01:
            return count
    return None


class LoanListView(LoginRequiredMixin, ListView):
    model = Loan
    template_name = "core/loan_list.html"
    context_object_name = "loans"

    def get_queryset(self):
        return Loan.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        loans = context["loans"]
        active = [l for l in loans if l.is_active and float(l.current_balance) > 0]

        total_debt = sum(float(l.current_balance) for l in active)
        total_min_next = sum(l.min_next_payment for l in active)
        total_paid = sum(
            float(l.payments.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0)
            for l in loans
        )

        # Attach per-loan next payment info
        for loan in loans:
            loan.next_interest_display = loan.next_interest
            schedule = _build_schedule(loan, months=1)
            loan.min_payment_display = schedule[0]['payment'] if schedule else loan.next_interest
            loan.pct_paid = round(
                (1 - float(loan.current_balance) / float(loan.principal)) * 100, 1
            ) if float(loan.principal) > 0 else 100

        context["total_debt"] = round(total_debt, 2)
        context["total_min_next"] = round(total_min_next, 2)
        context["total_paid"] = round(total_paid, 2)
        context["active_count"] = len(active)
        return context


class LoanCreateView(LoginRequiredMixin, CreateView):
    model = Loan
    form_class = LoanForm
    template_name = "core/loan_form.html"
    success_url = reverse_lazy("loan_list")

    def form_valid(self, form):
        form.instance.user = self.request.user
        if not form.instance.current_balance:
            form.instance.current_balance = form.instance.principal
        response = super().form_valid(form)
        AuditLog.objects.create(
            user=self.request.user, action="CREATE", model_name="Loan",
            object_id=self.object.pk,
            description=f"Empréstimo criado: {self.object.name} R$ {self.object.principal}"
        )
        messages.success(self.request, "Empréstimo cadastrado com sucesso!")
        return response


class LoanUpdateView(LoginRequiredMixin, UpdateView):
    model = Loan
    form_class = LoanForm
    template_name = "core/loan_form.html"
    success_url = reverse_lazy("loan_list")

    def get_queryset(self):
        return Loan.objects.filter(user=self.request.user)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Empréstimo atualizado!")
        return response


class LoanDeleteView(LoginRequiredMixin, DeleteView):
    model = Loan
    template_name = "core/confirm_delete.html"
    success_url = reverse_lazy("loan_list")

    def get_queryset(self):
        return Loan.objects.filter(user=self.request.user)


@login_required
def loan_detail(request, pk):
    loan = get_object_or_404(Loan, pk=pk, user=request.user)
    payments = loan.payments.order_by('-payment_date')

    # Scenario simulations
    sim_payment = float(request.GET.get('sim', 0)) or None

    schedule_min = _build_schedule(loan, months=120)  # interest-only / minimum
    schedule_sim = _build_schedule(loan, months=120, custom_payment=sim_payment) if sim_payment and loan.loan_type == 'REDUCAO_SALDO' else schedule_min

    payoff_min = len(schedule_min) if schedule_min and schedule_min[-1]['balance'] <= 0.01 else None
    payoff_sim = len(schedule_sim) if schedule_sim and schedule_sim[-1]['balance'] <= 0.01 else None

    # Chart data (first 24 months or until payoff)
    chart_months = schedule_min[:24]
    chart_labels = [f"Mês {m['month']}" for m in chart_months]
    chart_balance = [m['balance'] for m in chart_months]
    chart_interest = [m['interest'] for m in chart_months]
    chart_principal = [m['principal'] for m in chart_months]

    # For REDUCAO_SALDO: if sim, show comparison
    chart_sim_balance = [m['balance'] for m in schedule_sim[:24]] if sim_payment else None

    # Total interest to pay (schedule_min)
    total_future_interest = sum(m['interest'] for m in schedule_min)
    total_future_interest_sim = sum(m['interest'] for m in schedule_sim) if sim_payment else None

    context = {
        "loan": loan,
        "payments": payments,
        "schedule": schedule_min[:12],  # Show next 12 months in table
        "payoff_months_min": payoff_min,
        "payoff_months_sim": payoff_sim,
        "sim_payment": sim_payment,
        "total_future_interest": round(total_future_interest, 2),
        "total_future_interest_sim": round(total_future_interest_sim, 2) if total_future_interest_sim else None,
        "chart_labels": json.dumps(chart_labels),
        "chart_balance": json.dumps(chart_balance),
        "chart_interest": json.dumps(chart_interest),
        "chart_principal": json.dumps(chart_principal),
        "chart_sim_balance": json.dumps(chart_sim_balance) if chart_sim_balance else "null",
    }
    return render(request, "core/loan_detail.html", context)


@login_required
def loan_make_payment(request, pk):
    loan = get_object_or_404(Loan, pk=pk, user=request.user)

    if request.method == "POST":
        form = LoanPaymentForm(request.POST)
        if form.is_valid():
            amount = float(form.cleaned_data['amount_paid'])
            interest = loan.next_interest  # interest at current balance

            if amount < interest:
                messages.warning(request, f"Atenção: o valor pago (R$ {amount:.2f}) é menor que os juros do mês (R$ {interest:.2f}). A dívida vai crescer!")
                principal_paid = 0
                # Apply partial payment to interest
                interest_paid = amount
                balance_after = float(loan.current_balance) + (interest - amount)
            else:
                interest_paid = interest
                principal_paid = amount - interest
                balance_after = max(float(loan.current_balance) - principal_paid, 0)

            payment = form.save(commit=False)
            payment.loan = loan
            payment.interest_paid = round(interest_paid, 2)
            payment.principal_paid = round(principal_paid, 2)
            payment.balance_after = round(balance_after, 2)
            payment.save()

            # Update loan balance
            loan.current_balance = Decimal(str(round(balance_after, 2)))
            if loan.current_balance <= 0:
                loan.is_active = False
            loan.save()

            # Create Transaction expense for the payment
            category, _ = Category.objects.get_or_create(
                user=request.user, name="Pagamento de Empréstimo",
                defaults={"type": "DESPESA"}
            )
            Transaction.objects.create(
                user=request.user,
                category=category,
                type="DESPESA",
                amount=Decimal(str(amount)),
                date=form.cleaned_data['payment_date'],
                description=f"Pagamento — {loan.name} (juros: R$ {interest_paid:.2f} / amort: R$ {principal_paid:.2f})",
            )

            AuditLog.objects.create(
                user=request.user, action="UPDATE", model_name="Loan",
                object_id=loan.pk,
                description=f"Pagamento R$ {amount:.2f} em {loan.name}. Saldo: R$ {balance_after:.2f}"
            )

            if balance_after <= 0:
                messages.success(request, f"Parabéns! O empréstimo '{loan.name}' foi quitado!")
            else:
                messages.success(request, f"Pagamento de R$ {amount:.2f} registrado. Juros: R$ {interest_paid:.2f} | Amortização: R$ {principal_paid:.2f} | Novo saldo: R$ {balance_after:.2f}")

            return redirect("loan_detail", pk=loan.pk)
    else:
        form = LoanPaymentForm(initial={'payment_date': timezone.now().date(), 'amount_paid': f"{loan.min_next_payment:.2f}"})

    context = {"loan": loan, "form": form, "suggested_min": loan.min_next_payment}
    return render(request, "core/loan_payment.html", context)
