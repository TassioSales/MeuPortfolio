import datetime
from decimal import Decimal
from django.db.models import Sum
from .dates import add_months, today as local_today
from .models import Transaction, RecurringTransaction

def process_recurring_transactions(user, up_to_date=None):
    """
    Materializes recurring transactions whose next_run_date is on/before
    `up_to_date` (defaults to today) into real Transaction records, advancing
    each recurring transaction's next_run_date until it exceeds `up_to_date`
    (so a lapsed user catches up on every missed period, not just one).

    Passing a future `up_to_date` (e.g. the last day of a month the user is
    browsing ahead to) projects recurring debts forward immediately instead
    of waiting for real calendar time to pass — matching how credit-card
    installments are already pre-created in full.
    """
    today = local_today()
    if up_to_date is None:
        up_to_date = today

    # Safety cap: never materialize more than 24 months ahead of the real
    # date, even if a caller passes something further out.
    safety_cap = materialization_cap(today)
    if up_to_date > safety_cap:
        up_to_date = safety_cap

    # Find active recurring transactions due for processing
    recurring_txs = RecurringTransaction.objects.filter(
        user=user,
        active=True,
        next_run_date__lte=up_to_date
    )

    count = 0
    for recurring in recurring_txs:
        while recurring.next_run_date <= up_to_date:
            if recurring.end_date and recurring.next_run_date > recurring.end_date:
                recurring.active = False
                recurring.save()
                break

            # Create the actual transaction
            base = (recurring.description or '').strip() or (
                recurring.category.name if recurring.category_id else 'Lançamento'
            )
            Transaction.objects.create(
                user=user,
                category=recurring.category,
                type=recurring.type,
                amount=recurring.amount,
                date=recurring.next_run_date, # It happens on the scheduled date
                payment_method=recurring.payment_method,
                description=f"{base} (Recorrente)",
                origin=Transaction.ORIGIN_RECORRENTE,
                recurring_source=recurring,
            )
            count += 1

            next_date = next_occurrence(recurring.next_run_date, recurring.frequency)

            # Update the recurring transaction
            recurring.next_run_date = next_date
            if recurring.end_date and next_date > recurring.end_date:
                recurring.active = False
            recurring.save()

    return count


def materialization_cap(today=None):
    """Data-limite (24 meses à frente) até onde recorrências e parcelas de
    empréstimo são materializadas como Transaction."""
    return add_months(today or local_today(), 24)


def next_occurrence(current_date, frequency):
    """Próxima data de uma recorrência a partir de `current_date`."""
    if frequency == 'DIARIO':
        return current_date + datetime.timedelta(days=1)
    if frequency == 'SEMANAL':
        return current_date + datetime.timedelta(weeks=1)
    if frequency == 'QUINZENAL':
        return current_date + datetime.timedelta(days=15)
    if frequency == 'MENSAL':
        return add_months(current_date, 1)
    if frequency == 'ANUAL':
        return add_months(current_date, 12)  # 29/02 → 28/02
    return current_date + datetime.timedelta(days=30)


def budget_spent_map(user, budgets, year=None, month=None):
    """
    Given an iterable of Budget objects belonging to `user`, return
    {budget.id: spent_amount} computed with at most 2 grouped queries
    (one for MENSAL budgets, one for ANUAL) instead of one query per budget.
    """
    budgets = list(budgets)
    today = local_today()
    year = year or today.year
    month = month or today.month
    result = {b.id: Decimal('0') for b in budgets}

    mensal = [b for b in budgets if b.period == 'MENSAL']
    anual = [b for b in budgets if b.period == 'ANUAL']

    if mensal:
        totals = (
            Transaction.objects.filter(
                user=user, type='DESPESA',
                category_id__in=[b.category_id for b in mensal],
                date__year=year, date__month=month,
            )
            .values('category_id')
            .annotate(total=Sum('amount'))
        )
        by_category = {t['category_id']: t['total'] for t in totals}
        for b in mensal:
            result[b.id] = by_category.get(b.category_id) or Decimal('0')

    if anual:
        totals = (
            Transaction.objects.filter(
                user=user, type='DESPESA',
                category_id__in=[b.category_id for b in anual],
                date__year=year,
            )
            .values('category_id')
            .annotate(total=Sum('amount'))
        )
        by_category = {t['category_id']: t['total'] for t in totals}
        for b in anual:
            result[b.id] = by_category.get(b.category_id) or Decimal('0')

    return result
