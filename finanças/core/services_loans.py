"""Empréstimos: matemática de amortização (Decimal) e integração com as
transações — parcelas previstas materializadas como despesa, pagamentos que
reconciliam a parcela prevista em vez de duplicá-la, e entrada do valor
recebido como receita.

Regras (ver docs/superpowers/specs/2026-09-27-...-design.md §4):
- Parcela prevista = Transaction(DESPESA, origin=EMPRESTIMO, loan=loan) sem
  LoanPayment vinculado. Parcela paga = a mesma Transaction com LoanPayment.
- `sync_loan_installments` recria só as previstas; nunca toca nas pagas.
- `planned_payment` (parcela combinada) tem prioridade sobre o cálculo
  automático; empréstimo informal = sem nº de parcelas.
"""
from __future__ import annotations

import datetime
from decimal import Decimal

from django.db import transaction as db_transaction
from django.db.models import Q

from .dates import add_months, today
from .models import Category, Loan, LoanDisbursement, LoanPayment, Transaction
from .money import q2

ZERO = Decimal("0")
ONE_CENT = Decimal("0.01")
MAX_MONTHS = 360

EXPENSE_CATEGORY = "Empréstimos"
INCOME_CATEGORY = "Empréstimos recebidos"


# ── matemática ────────────────────────────────────────────────────────────

def monthly_rate(loan: Loan) -> Decimal:
    rate = Decimal(loan.interest_rate or 0) / 100
    if loan.interest_period == "ANUAL" and rate:
        # (1 + a)^(1/12) - 1 — sem expoente fracionário em Decimal, via float
        rate = Decimal(str((1 + float(rate)) ** (1 / 12) - 1))
    return rate


def is_informal(loan: Loan) -> bool:
    return not loan.num_installments


def _price_pmt(pv: Decimal, r: Decimal, n: int) -> Decimal:
    if r == 0:
        return pv / n
    return pv * r / (1 - (1 + r) ** -n)


def _row(i, payment, interest, principal, balance, ins):
    payment, interest, principal = q2(payment), q2(interest), q2(principal)
    return {
        "month": i,
        "payment": payment,
        "interest": interest,
        "principal": principal,
        "balance": q2(max(balance, ZERO)),
        "insurance": q2(ins),
        "total": q2(payment + ins),
    }


def build_schedule(loan: Loan, months: int = MAX_MONTHS, custom_payment=None,
                   paid_count: int | None = None) -> list[dict]:
    """Cronograma futuro a partir de `current_balance`.

    Linha: {month, payment, interest, principal, balance, insurance, total}.
    `custom_payment` (simulação) e `loan.planned_payment` (parcela combinada)
    substituem a parcela calculada, em qualquer modalidade.
    """
    balance = Decimal(loan.current_balance or 0)
    r = monthly_rate(loan)
    ins = Decimal(loan.insurance_monthly or 0)
    fixed = custom_payment if custom_payment else loan.planned_payment
    fixed = Decimal(str(fixed)) if fixed else None
    if paid_count is None:
        paid_count = loan.payments.count() if loan.pk else 0
    schedule = []
    if balance <= 0:
        return schedule

    if fixed:
        # Parcela combinada: paga `fixed` por mês até quitar. Se for menor que
        # os juros, a dívida cresce (e o cronograma para no limite de meses).
        for i in range(1, months + 1):
            interest = balance * r
            payment = min(fixed, balance + interest)
            principal = payment - interest
            balance -= principal
            schedule.append(_row(i, payment, interest, principal, balance, ins))
            if balance <= ONE_CENT:
                break
        return schedule

    n = loan.num_installments or 0
    remaining = max(n - paid_count, 1) if n else None

    if loan.loan_type == "PRICE" and n:
        pmt = _price_pmt(Decimal(loan.principal), r, n)
        for i in range(1, min(remaining, months) + 1):
            interest = balance * r
            principal = pmt - interest
            if principal > balance or i == remaining:
                principal = balance
            payment = interest + principal
            balance -= principal
            schedule.append(_row(i, payment, interest, principal, balance, ins))
            if balance <= ONE_CENT:
                break

    elif loan.loan_type == "SAC" and n:
        fixed_principal = Decimal(loan.principal) / n
        for i in range(1, min(remaining, months) + 1):
            interest = balance * r
            principal = balance if i == remaining else min(fixed_principal, balance)
            payment = interest + principal
            balance -= principal
            schedule.append(_row(i, payment, interest, principal, balance, ins))
            if balance <= ONE_CENT:
                break

    elif loan.loan_type == "SIMPLES" and n:
        interest = balance * r
        for i in range(1, min(remaining, months) + 1):
            is_last = i == remaining
            principal = balance if is_last else ZERO
            schedule.append(_row(i, interest + principal, interest, principal,
                                 ZERO if is_last else balance, ins))
            if is_last:
                break

    else:
        # Saldo devedor / informal sem prazo: mínimo = juros do mês. Sem juros
        # e sem parcela combinada não há parcela prevista — o usuário lança
        # os pagamentos manualmente, no valor que quiser.
        for i in range(1, months + 1):
            interest = balance * r
            if interest + ins <= 0:
                break
            schedule.append(_row(i, interest, interest, ZERO, balance, ins))

    return schedule


def payoff_months(schedule: list[dict]) -> int | None:
    if schedule and schedule[-1]["balance"] <= ONE_CENT:
        return len(schedule)
    return None


def calc_cet(loan: Loan, schedule: list[dict]) -> dict:
    """CET — taxa mensal r tal que principal − IOF = Σ total_t / (1+r)^t."""
    iof_value = Decimal(loan.principal) * Decimal(loan.iof_rate or 0) / 100
    net_received = float(Decimal(loan.principal) - iof_value)
    base = float(monthly_rate(loan))
    if not schedule or net_received <= 0:
        return {"monthly": round(base * 100, 4), "annual": 0.0, "iof_value": q2(iof_value)}

    cf = [-net_received] + [float(row["total"]) for row in schedule]
    r = base or 0.01
    for _ in range(300):
        npv = sum(cf[t] / (1 + r) ** t for t in range(len(cf)))
        dnpv = sum(-t * cf[t] / (1 + r) ** (t + 1) for t in range(1, len(cf)))
        if abs(dnpv) < 1e-12:
            break
        r_new = r - npv / dnpv
        if abs(r_new - r) < 1e-10:
            r = r_new
            break
        r = max(r_new, 0.00001)
    return {
        "monthly": round(r * 100, 4),
        "annual": round(((1 + r) ** 12 - 1) * 100, 2),
        "iof_value": q2(iof_value),
    }


def next_payment_amount(loan: Loan) -> Decimal:
    schedule = build_schedule(loan, months=1)
    return schedule[0]["total"] if schedule else ZERO


# ── datas ─────────────────────────────────────────────────────────────────

def due_date_in(month_first: datetime.date, due_day: int) -> datetime.date:
    return add_months(month_first, 0, day=max(1, min(due_day or 10, 31)))


def default_first_due_date(loan: Loan) -> datetime.date:
    if loan.first_due_date:
        return loan.first_due_date
    return due_date_in(add_months(loan.start_date.replace(day=1), 1, day=1), loan.due_day)


def first_pending_due_date(loan: Loan) -> datetime.date:
    """Vencimento da próxima parcela em aberto.

    Começa em `first_due_date` (ou, se vazio, no mês seguinte ao empréstimo);
    nunca antes do mês atual (parcelas antigas não pagas não são recriadas no
    passado). Se já houver pagamento registrado no mês, a próxima vai para o
    mês seguinte.
    """
    t = today()
    first = default_first_due_date(loan)
    current = due_date_in(t.replace(day=1), loan.due_day)
    candidate = max(first, current)
    last_payment = loan.payments.order_by("-payment_date", "-id").first() if loan.pk else None
    if last_payment and last_payment.payment_date >= candidate.replace(day=1):
        candidate = due_date_in(add_months(last_payment.payment_date.replace(day=1), 1, day=1), loan.due_day)
    return candidate


# ── categorias ────────────────────────────────────────────────────────────

def _category(user, name, type_):
    cat, created = Category.objects.get_or_create(
        user=user, name=name, parent=None,
        defaults={"type": type_, "nature": Category.NATURE_DIVIDA},
    )
    if not created and cat.nature != Category.NATURE_DIVIDA:
        cat.nature = Category.NATURE_DIVIDA
        cat.save(update_fields=["nature"])
    return cat


def expense_category(user):
    return _category(user, EXPENSE_CATEGORY, "DESPESA")


def income_category(user):
    return _category(user, INCOME_CATEGORY, "RECEITA")


# ── sincronização de parcelas previstas ───────────────────────────────────

def pending_installments(loan: Loan):
    return loan.transactions.filter(
        type="DESPESA", origin=Transaction.ORIGIN_EMPRESTIMO, loan_payment__isnull=True,
    )


def sync_loan_installments(loan: Loan) -> int:
    """Recria as parcelas previstas do empréstimo a partir do cronograma
    atual, até o teto de materialização (24 meses). Idempotente."""
    from .services import materialization_cap

    with db_transaction.atomic():
        # Só do mês atual em diante: previstas de meses passados (não pagas)
        # ficam como estão, para não reescrever o histórico daqueles meses.
        pending_installments(loan).filter(date__gte=today().replace(day=1)).delete()
        loan.synced_at = today()
        Loan.objects.filter(pk=loan.pk).update(synced_at=loan.synced_at)
        if not loan.is_active or loan.current_balance <= 0:
            return 0

        paid_count = loan.payments.count()
        schedule = build_schedule(loan, paid_count=paid_count)
        # Previstas de meses passados continuam existindo: começar depois delas.
        last_old = pending_installments(loan).order_by("-date").first()
        cap = materialization_cap()
        category = expense_category(loan.user)
        first_due = first_pending_due_date(loan)
        if last_old and last_old.date >= first_due:
            first_due = due_date_in(add_months(last_old.date.replace(day=1), 1, day=1), loan.due_day)
        total_n = (paid_count + len(schedule)) if payoff_months(schedule) else None
        created = 0
        for i, row in enumerate(schedule):
            due = due_date_in(add_months(first_due.replace(day=1), i, day=1), loan.due_day)
            if due > cap:
                break
            if row["total"] <= 0:
                continue
            number = paid_count + i + 1
            label = f"parcela {number}/{total_n}" if total_n else f"parcela {number}"
            if not loan.planned_payment and is_informal(loan):
                label += " (mínimo: juros)"
            Transaction.objects.create(
                user=loan.user, category=category, type="DESPESA", amount=row["total"],
                date=due, payment_method="PIX",
                description=f"{loan.name} — {label}",
                origin=Transaction.ORIGIN_EMPRESTIMO, loan=loan,
                installment_number=number, installment_total=total_n,
            )
            created += 1
        return created


def refresh_user_loans(user, max_age_days: int = 28) -> None:
    """Chamado ao abrir o dashboard: re-sincroniza empréstimos ativos que
    nunca foram sincronizados ou cuja janela de 24 meses já andou."""
    limit = today() - datetime.timedelta(days=max_age_days)
    for loan in Loan.objects.filter(user=user, is_active=True).filter(
        Q(synced_at__isnull=True) | Q(synced_at__lt=limit)
    ):
        sync_loan_installments(loan)


# ── receita do valor recebido ─────────────────────────────────────────────

def sync_loan_income(loan: Loan) -> None:
    """Mantém (ou remove) a receita do valor recebido do empréstimo."""
    existing = loan.transactions.filter(type="RECEITA", loan_disbursement__isnull=True).first()
    if not loan.register_income:
        if existing:
            existing.delete()
        return
    iof_value = Decimal(loan.principal) * Decimal(loan.iof_rate or 0) / 100
    net = q2(Decimal(loan.principal) - iof_value)
    fields = dict(
        user=loan.user, category=income_category(loan.user), type="RECEITA", amount=net,
        date=loan.start_date, payment_method="PIX",
        description=f"{loan.name} — valor recebido", origin=Transaction.ORIGIN_EMPRESTIMO, loan=loan,
    )
    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
        existing.save()
    else:
        Transaction.objects.create(**fields)


def on_loan_saved(loan: Loan) -> None:
    with db_transaction.atomic():
        sync_loan_income(loan)
        sync_loan_installments(loan)


def delete_loan(loan: Loan) -> None:
    """Exclui o empréstimo e as parcelas previstas; o histórico pago fica
    (com loan=NULL) porque aquele dinheiro saiu de fato."""
    with db_transaction.atomic():
        pending_installments(loan).delete()
        loan.transactions.filter(type="RECEITA").delete()
        loan.delete()


# ── pagamentos ────────────────────────────────────────────────────────────

def register_payment(loan: Loan, amount: Decimal, payment_date: datetime.date, notes: str = "") -> LoanPayment:
    """Registra um pagamento: divide juros/amortização, atualiza o saldo,
    converte a parcela prevista do mês em realizada (ou cria uma, se for um
    pagamento extra) e recalcula as próximas parcelas."""
    amount = q2(amount)
    balance_before = Decimal(loan.current_balance)
    interest = q2(balance_before * monthly_rate(loan))
    if amount < interest:
        interest_paid, principal_paid = amount, ZERO
        balance_after = balance_before + (interest - amount)
    else:
        interest_paid = interest
        principal_paid = amount - interest
        balance_after = max(balance_before - principal_paid, ZERO)

    with db_transaction.atomic():
        month_start = payment_date.replace(day=1)
        month_end = add_months(month_start, 1, day=1) - datetime.timedelta(days=1)
        tx = (
            pending_installments(loan).filter(date__gte=month_start, date__lte=month_end).order_by("date").first()
            or pending_installments(loan).filter(date__lte=payment_date).order_by("date").first()
        )
        description = (f"Pagamento — {loan.name} (juros: R$ {interest_paid:.2f} / "
                       f"amort.: R$ {principal_paid:.2f})")
        if tx:
            tx.amount = amount
            tx.date = payment_date
            tx.description = description
            tx.save()
        else:
            tx = Transaction.objects.create(
                user=loan.user, category=expense_category(loan.user), type="DESPESA",
                amount=amount, date=payment_date, payment_method="PIX", description=description,
                origin=Transaction.ORIGIN_EMPRESTIMO, loan=loan,
            )
        payment = LoanPayment.objects.create(
            loan=loan, payment_date=payment_date, amount_paid=amount,
            interest_paid=q2(interest_paid), principal_paid=q2(principal_paid),
            balance_before=q2(balance_before), balance_after=q2(balance_after),
            notes=notes, transaction=tx,
        )
        loan.current_balance = q2(balance_after)
        if loan.current_balance <= 0:
            loan.is_active = False
        loan.save()
        sync_loan_installments(loan)
    return payment


def revert_payment(payment: LoanPayment) -> None:
    """Desfaz o pagamento mais recente: restaura o saldo e a parcela prevista."""
    loan = payment.loan
    if not is_latest_payment(payment):
        raise ValueError(
            "Só é possível alterar ou excluir o pagamento mais recente deste empréstimo — "
            "cada pagamento é calculado sobre o saldo deixado pelo anterior. "
            "Exclua os mais recentes primeiro."
        )
    with db_transaction.atomic():
        restored = payment.balance_before
        if restored is None:
            restored = payment.balance_after + payment.principal_paid
        loan.current_balance = q2(restored)
        loan.is_active = True
        loan.save()
        tx = payment.transaction
        payment.delete()
        if tx:
            tx.delete()
        sync_loan_installments(loan)


def is_latest_payment(payment: LoanPayment) -> bool:
    latest = payment.loan.payments.order_by("-payment_date", "-id").first()
    return latest is not None and latest.pk == payment.pk


def edit_payment(payment: LoanPayment, amount: Decimal, payment_date: datetime.date, notes: str = "") -> LoanPayment:
    """Corrige o pagamento mais recente: desfaz e registra de novo com os
    valores novos (juros/amortização/saldo recalculados a partir do saldo
    que havia antes dele)."""
    loan = payment.loan
    with db_transaction.atomic():
        revert_payment(payment)
        loan.refresh_from_db()
        return register_payment(loan, amount, payment_date, notes)


def add_funds(loan: Loan, amount: Decimal, date: datetime.date, note: str = "") -> LoanDisbursement:
    amount = q2(amount)
    with db_transaction.atomic():
        tx = None
        if loan.register_income:
            tx = Transaction.objects.create(
                user=loan.user, category=income_category(loan.user), type="RECEITA", amount=amount,
                date=date, payment_method="PIX", description=f"{loan.name} — desembolso adicional",
                origin=Transaction.ORIGIN_EMPRESTIMO, loan=loan,
            )
        disb = LoanDisbursement.objects.create(loan=loan, amount=amount, date=date, note=note, transaction=tx)
        loan.current_balance = q2(Decimal(loan.current_balance) + amount)
        loan.save()
        sync_loan_installments(loan)
    return disb


# ── resumo por usuário ────────────────────────────────────────────────────

def loans_summary(user) -> dict:
    t = today()
    loans = list(Loan.objects.filter(user=user, is_active=True, current_balance__gt=0))
    next_txs = {}
    for tx in Transaction.objects.filter(
        user=user, origin=Transaction.ORIGIN_EMPRESTIMO, type="DESPESA",
        loan__in=loans, loan_payment__isnull=True,
    ).order_by("date"):
        next_txs.setdefault(tx.loan_id, tx)
    upcoming = [next_txs[l.pk] for l in loans if l.pk in next_txs]
    month_total = sum(
        (tx.amount for tx in upcoming if tx.date.year == t.year and tx.date.month == t.month), ZERO
    )
    return {
        "count": len(loans),
        "debt": sum((l.current_balance for l in loans), ZERO),
        "next": sorted(upcoming, key=lambda x: x.date),
        "month_total": month_total,
    }
