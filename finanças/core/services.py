import datetime
import calendar
from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from .models import Transaction, RecurringTransaction

def process_recurring_transactions(user):
    """
    Checks for active recurring transactions that are due (next_run_date <= today)
    and creates the corresponding Transaction records.
    Updates the next_run_date for the recurring transaction.
    """
    today = timezone.now().date()
    
    # Find active recurring transactions due for processing
    recurring_txs = RecurringTransaction.objects.filter(
        user=user,
        active=True,
        next_run_date__lte=today
    )
    
    count = 0
    for recurring in recurring_txs:
        # Create the actual transaction
        Transaction.objects.create(
            user=user,
            category=recurring.category,
            type=recurring.type,
            amount=recurring.amount,
            date=recurring.next_run_date, # It happens on the scheduled date
            payment_method=recurring.payment_method,
            description=f"{recurring.description} (Recorrente)"
        )
        count += 1
        
        # Calculate next date
        current_date = recurring.next_run_date
        next_date = current_date
        
        if recurring.frequency == 'DIARIO':
            next_date += datetime.timedelta(days=1)
        elif recurring.frequency == 'SEMANAL':
            next_date += datetime.timedelta(weeks=1)
        elif recurring.frequency == 'QUINZENAL':
            next_date += datetime.timedelta(days=15)
        elif recurring.frequency == 'MENSAL':
            # Add 1 month, handling end of month logic
            month = current_date.month - 1 + 1
            year = current_date.year + month // 12
            month = month % 12 + 1
            day = min(current_date.day, calendar.monthrange(year, month)[1])
            next_date = datetime.date(year, month, day)
        elif recurring.frequency == 'ANUAL':
            # Add 1 year, handling leap years (Feb 29 -> Feb 28)
            try:
                next_date = current_date.replace(year=current_date.year + 1)
            except ValueError:
                next_date = current_date.replace(year=current_date.year + 1, day=28)
        
        # Update the recurring transaction
        recurring.next_run_date = next_date
        recurring.save()

    return count


def budget_spent_map(user, budgets):
    """
    Given an iterable of Budget objects belonging to `user`, return
    {budget.id: spent_amount} computed with at most 2 grouped queries
    (one for MENSAL budgets, one for ANUAL) instead of one query per budget.
    """
    budgets = list(budgets)
    today = timezone.now().date()
    result = {b.id: Decimal('0') for b in budgets}

    mensal = [b for b in budgets if b.period == 'MENSAL']
    anual = [b for b in budgets if b.period == 'ANUAL']

    if mensal:
        totals = (
            Transaction.objects.filter(
                user=user, type='DESPESA',
                category_id__in=[b.category_id for b in mensal],
                date__year=today.year, date__month=today.month,
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
                date__year=today.year,
            )
            .values('category_id')
            .annotate(total=Sum('amount'))
        )
        by_category = {t['category_id']: t['total'] for t in totals}
        for b in anual:
            result[b.id] = by_category.get(b.category_id) or Decimal('0')

    return result
