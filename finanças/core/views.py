from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
import logging
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
from django.http import HttpResponse, JsonResponse, Http404
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from datetime import timedelta
import datetime
import calendar
import csv
import json
import os
import shutil
import tempfile
import certifi
import requests
from xhtml2pdf import pisa
import yfinance as yf
from .market_data import get_real_time_currency, get_latest_indicator, calculate_cdi_correction, calculate_pre_fixado, SERIES_SELIC_META, SERIES_CDI_MENSAL

def get_price_manual(symbol):
    try:
        url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        result = data['chart']['result'][0]
        meta = result['meta']
        price = meta.get('regularMarketPrice') or meta.get('chartPreviousClose')
        currency = meta.get('currency')
        return price, currency
    except Exception as e:
        print(f"Manual fetch failed for {symbol}: {e}")
        return None, None

from .models import Transaction, Category, Budget, Investment, RecurringTransaction, Goal
from django.db.models.functions import TruncMonth, TruncDay
from .forms import CategoryForm, TransactionForm, BudgetForm, InvestmentForm, ImportFileForm, GoalForm

logger = logging.getLogger('core')

# Fix for SSL error with special characters or spaces in path (curl 77)
def fix_ssl():
    ca_bundle = certifi.where()
    # Check for spaces OR non-ascii characters (like 'ç' in 'finanças')
    is_path_problematic = any(ord(c) > 127 for c in ca_bundle) or ' ' in ca_bundle
    
    if is_path_problematic:
        # Create a temp copy in a clear ASCII path
        temp_dir = tempfile.gettempdir()
        temp_cert = os.path.join(temp_dir, 'cacert_finance.pem')
        try:
            shutil.copy(ca_bundle, temp_cert)
            os.environ['CURL_CA_BUNDLE'] = temp_cert
            os.environ['REQUESTS_CA_BUNDLE'] = temp_cert
        except Exception as e:
            print(f"Failed to copy cert: {e}")
    else:
        os.environ['CURL_CA_BUNDLE'] = ca_bundle
        os.environ['REQUESTS_CA_BUNDLE'] = ca_bundle

fix_ssl()

@login_required
def search_ticker(request):
    ticker_symbol = request.GET.get('ticker', '').upper().strip()
    print(f"DEBUG: Received ticker: '{ticker_symbol}'")
    if not ticker_symbol:
        return JsonResponse({'error': 'Ticker is required'}, status=400)
    
    # Auto-append .SA if it looks like B3
    if any(char.isdigit() for char in ticker_symbol) and '.' not in ticker_symbol and '-' not in ticker_symbol:
         ticker_symbol += '.SA'
    
    print(f"DEBUG: Using ticker: '{ticker_symbol}'")

    # Normalize aliases
    if ticker_symbol == 'EURO': ticker_symbol = 'EUR'
    if ticker_symbol == 'DOLAR': ticker_symbol = 'USD'
    if ticker_symbol == 'BITCOIN': ticker_symbol = 'BTC'

    price = None
    currency = 'BRL'
    name = ticker_symbol
    previous_close = None
    day_high = None
    day_low = None
    year_high = None
    year_low = None
    chart_labels = []
    chart_data = []

    # Direct handling for Currencies to avoid YF 404s/noise
    if ticker_symbol in ['USD', 'EUR']:
        price = get_real_time_currency(ticker_symbol)
        if price:
            return JsonResponse({
                'symbol': ticker_symbol,
                'name': 'Dólar Americano' if ticker_symbol == 'USD' else 'Euro',
                'price': price,
                'currency': 'BRL',
                'change_percent': 0,
                'day_high': price,
                'day_low': price,
                'year_high': price,
                'year_low': price,
                'chart_labels': [],
                'chart_data': [],
            })

    try:
        ticker = yf.Ticker(ticker_symbol)
        
        # Method 1: Try fast_info
        try:
             price = ticker.fast_info.last_price
             currency = ticker.fast_info.currency
        except:
             pass

        # Method 2: History fallback
        if price is None:
             history = ticker.history(period='1d')
             if not history.empty:
                 price = history['Close'].iloc[-1]
             else:
                 # Method 3: Info fallback
                 info = ticker.info
                 price = info.get('currentPrice') or info.get('regularMarketPrice')
                 currency = info.get('currency', 'BRL')
        
        # Get extra info
        try:
            info = ticker.info
            name = info.get('longName') or info.get('shortName') or ticker_symbol
            previous_close = info.get('previousClose')
            day_high = info.get('dayHigh')
            day_low = info.get('dayLow')
            year_high = info.get('fiftyTwoWeekHigh')
            year_low = info.get('fiftyTwoWeekLow')
        except:
            pass

        # Fetch History for Chart
        try:
            history_chart = ticker.history(period="6mo")
            for date, row in history_chart.iterrows():
                chart_labels.append(date.strftime('%d/%m/%Y'))
                chart_data.append(row['Close'])
        except Exception as e:
            print(f"Error fetching history for chart: {e}")

    except Exception as e:
        print(f"YFinance failed for {ticker_symbol}: {e}")
        # Fallthrough to manual

    # Method 4: Manual Fallback
    if price is None:
        price, currency_manual = get_price_manual(ticker_symbol)
        if price is not None:
            if currency_manual:
                currency = currency_manual

    # Currency Conversion Logic
    usd_brl_rate = 1.0
    if currency == 'USD':
        try:
            usd_brl_rate = get_real_time_currency('USD')
            price = price * usd_brl_rate
            currency = 'BRL' # Converted
        except Exception as e:
            print(f"Error converting currency: {e}")
    
    # Convert additional fields if USD
    if currency == 'BRL' and usd_brl_rate != 1.0:
        if previous_close: previous_close *= usd_brl_rate
        if day_high: day_high *= usd_brl_rate
        if day_low: day_low *= usd_brl_rate
        if year_high: year_high *= usd_brl_rate
        if year_low: year_low *= usd_brl_rate

    change_percent = 0
    if previous_close and price:
        change_percent = ((price - previous_close) / previous_close) * 100

    # Fetch History for Chart
    chart_labels = []
    chart_data = []
    try:
        # Get 6 months of history
        history_chart = ticker.history(period="6mo")
        for date, row in history_chart.iterrows():
            chart_labels.append(date.strftime('%d/%m/%Y'))
            chart_data.append(row['Close'])
    except Exception as e:
        print(f"Error fetching history for chart: {e}")

    return JsonResponse({
        'symbol': ticker_symbol,
        'name': name,
        'price': price,
        'currency': currency,
        'change_percent': change_percent,
        'day_high': day_high,
        'day_low': day_low,
        'year_high': year_high,
        'year_low': year_low,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
    })

@login_required
def investment_dashboard(request):
    investments = Investment.objects.filter(user=request.user)
    
    portfolio_data = []
    total_invested = 0
    total_current_value = 0
    
    labels = []
    data_values = []
    
    # Fetch USD rate once to optimize
    try:
        usd_brl_rate = get_real_time_currency('USD')
    except:
        usd_brl_rate = 5.0 # Fallback

    # Aggregate investments by symbol and CATEGORY
    aggregated_portfolio = {}
    for inv in investments:
        key = (inv.symbol, inv.category_type)
        if key not in aggregated_portfolio:
            aggregated_portfolio[key] = {
                'symbol': inv.symbol,
                'category': inv.category_type,
                'name': inv.name,
                'quantity': 0.0,
                'total_cost': 0.0,
            }
        
        aggregated_portfolio[key]['quantity'] += float(inv.quantity)
        aggregated_portfolio[key]['total_cost'] += float(inv.total_cost)
        if not aggregated_portfolio[key]['name'] and inv.name:
            aggregated_portfolio[key]['name'] = inv.name

    for key, data in aggregated_portfolio.items():
        symbol = data['symbol']
        category = data['category']
        quantity = data['quantity']
        invested_value = data['total_cost']
        avg_price = invested_value / quantity if quantity > 0 else 0
        
        total_invested += invested_value
        current_price = None

        # Logic per Category
        if category == 'CURRENCY':
            # Use our robust currency fetcher instead of yfinance directly
            current_price = get_real_time_currency(symbol)
            if current_price:
                # current_price is already in BRL from our service
                pass
            else:
                current_price = avg_price

        elif category == 'FIXED':
            # For fixed income in the general dashboard, we use a simple correction estimate
            # (Similar to safe_haven but simplified)
            current_price = avg_price # Base for simple view
            # Try to get a more refined value if possible (optional for this view)

        else: # VARIABLE (Stock/FII)
            try:
                ticker = yf.Ticker(symbol)
                # 1. fast_info
                try:
                    current_price = ticker.fast_info.last_price
                except: pass

                # 2. history
                if current_price is None:
                    history = ticker.history(period='1d')
                    if not history.empty:
                        current_price = history['Close'].iloc[-1]
                
                # 3. Manual Fallback
                if current_price is None:
                    p, _ = get_price_manual(symbol)
                    current_price = p

                if current_price is not None:
                    # Check if it needs conversion (non-BRL stocks)
                    # Simple heuristic: if no .SA and not CURRENCY, check metadata
                    try:
                        currency_code = ticker.fast_info.currency
                        if currency_code == 'USD':
                            current_price *= usd_brl_rate
                    except:
                        if not symbol.endswith('.SA'):
                            current_price *= usd_brl_rate
                else:
                    current_price = avg_price
            except Exception as e:
                print(f"Error fetching data for {symbol}: {e}")
                current_price = avg_price
            
        current_value = quantity * float(current_price)
        total_current_value += current_value
        
        profit_loss = current_value - invested_value
        profit_loss_pct = (profit_loss / invested_value) * 100 if invested_value > 0 else 0
        
        # Create a mock object for the template to consume (compatible with item.investment.field)
        investment_mock = {
            'symbol': symbol,
            'name': data['name'],
            'quantity': quantity,
            'purchase_price': avg_price,
        }
        
        portfolio_data.append({
            'investment': investment_mock,
            'current_price': current_price,
            'current_value': current_value,
            'invested_value': invested_value,
            'profit_loss': profit_loss,
            'profit_loss_pct': profit_loss_pct
        })
        
        labels.append(symbol)
        data_values.append(current_value)
        
    roi = total_current_value - float(total_invested)
    roi_pct = (roi / float(total_invested)) * 100 if total_invested > 0 else 0
    
    context = {
        'portfolio': portfolio_data,
        'total_invested': total_invested,
        'total_current_value': total_current_value,
        'roi': roi,
        'roi_pct': roi_pct,
        'chart_labels': json.dumps(labels),
        'chart_data': json.dumps(data_values),
    }
    return render(request, 'core/investment_dashboard.html', context)

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Conta criada para {username}!')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

from .services import process_recurring_transactions

@login_required
def dashboard(request):
    # Process recurring transactions automatically
    processed_count = process_recurring_transactions(request.user)
    if processed_count > 0:
        messages.info(request, f'{processed_count} transações recorrentes foram geradas automaticamente.')

    # Get month and year from request, default to current
    today = timezone.now().date()
    try:
        month = int(request.GET.get('month', today.month))
        year = int(request.GET.get('year', today.year))
    except ValueError:
        month = today.month
        year = today.year

    # Calculate start and end date of the selected month
    _, last_day = calendar.monthrange(year, month)
    start_date = today.replace(year=year, month=month, day=1)
    end_date = today.replace(year=year, month=month, day=last_day)

    # Recent transactions (filtered by selected month)
    recent_transactions = Transaction.objects.filter(
        user=request.user,
        date__range=[start_date, end_date]
    ).order_by('-date')[:5]
    
    # Monthly Totals (filtered by selected month)
    monthly_income = Transaction.objects.filter(
        user=request.user, 
        type='RECEITA', 
        date__range=[start_date, end_date]
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    monthly_expense = Transaction.objects.filter(
        user=request.user, 
        type='DESPESA', 
        date__range=[start_date, end_date]
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    # Previous month range
    prev_month_end = start_date - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)

    previous_income_for_change = Transaction.objects.filter(
        user=request.user,
        type='RECEITA',
        date__range=[prev_month_start, prev_month_end]
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    previous_expense_for_change = Transaction.objects.filter(
        user=request.user,
        type='DESPESA',
        date__range=[prev_month_start, prev_month_end]
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    # Percentage change calculations (avoid division by zero)
    if previous_income_for_change:
        monthly_income_change = ((monthly_income - previous_income_for_change) / previous_income_for_change) * 100
    else:
        monthly_income_change = 0

    if previous_expense_for_change:
        monthly_expense_change = ((monthly_expense - previous_expense_for_change) / previous_expense_for_change) * 100
    else:
        monthly_expense_change = 0

    # Accumulated Balance (Previous Months)
    previous_income = Transaction.objects.filter(
        user=request.user,
        type='RECEITA',
        date__lt=start_date
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    previous_expense = Transaction.objects.filter(
        user=request.user,
        type='DESPESA',
        date__lt=start_date
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    accumulated_balance = previous_income - previous_expense
    
    # Total Current Balance
    net_balance = monthly_income - monthly_expense
    total_balance = accumulated_balance + net_balance
    
    # Chart Data (Last 6 months from selected month)
    six_months_ago = start_date - timedelta(days=180)
    chart_qs = Transaction.objects.filter(
        user=request.user,
        date__gte=six_months_ago,
        date__lte=end_date
    ).annotate(
        month=TruncMonth('date')
    ).values('month', 'type').annotate(
        total=Sum('amount')
    ).order_by('month')
    
    # Process chart data
    chart_data = {}
    for entry in chart_qs:
        month_str = entry['month'].strftime('%Y-%m')
        if month_str not in chart_data:
            chart_data[month_str] = {'RECEITA': 0, 'DESPESA': 0}
        chart_data[month_str][entry['type']] = float(entry['total'])
        
    labels = sorted(chart_data.keys())
    data_income = [chart_data[m].get('RECEITA', 0) for m in labels]
    data_expense = [chart_data[m].get('DESPESA', 0) for m in labels]
    
    net_balance = monthly_income - monthly_expense

    # Navigation Logic
    previous_month_date = start_date - timedelta(days=1)
    next_month_date = end_date + timedelta(days=1)
    
    previous_month = {'month': previous_month_date.month, 'year': previous_month_date.year}
    next_month = {'month': next_month_date.month, 'year': next_month_date.year}
    
    # Month names in Portuguese
    month_names = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }
    current_month_name = f"{month_names[month]} {year}"

    # Budget Alerts
    alerts = []
    budgets = Budget.objects.filter(user=request.user, period='MENSAL')
    for budget in budgets:
        # Calculate total expenses for this category in the current month
        expense_sum = Transaction.objects.filter(
            user=request.user,
            category=budget.category,
            type='DESPESA',
            date__range=[start_date, end_date]
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        if budget.limit > 0:
            percent_used = (expense_sum / budget.limit) * 100
            if percent_used >= 90:
                alerts.append({
                    'category': budget.category.name,
                    'percent': int(percent_used),
                    'limit': budget.limit,
                    'used': expense_sum,
                    'limit': budget.limit,
                    'used': expense_sum,
                    'level': 'danger' if percent_used >= 100 else 'warning'
                })

    context = {
        'recent_transactions': recent_transactions,
        'monthly_income': monthly_income,
        'monthly_expense': monthly_expense,
        'monthly_income_change': monthly_income_change,
        'monthly_expense_change': monthly_expense_change,
        'net_balance': net_balance,
        'accumulated_balance': accumulated_balance,
        'total_balance': total_balance,
        'chart_labels': json.dumps(labels),
        'chart_income': json.dumps(data_income),
        'chart_expense': json.dumps(data_expense),
        'current_month_name': current_month_name,
        'previous_month': previous_month,
        'next_month': next_month,
        'selected_month': month,
        'selected_year': year,
        'alerts': alerts,
    }
    return render(request, 'core/dashboard.html', context)

# Category CRUD
class CategoryListView(LoginRequiredMixin, ListView):
    model = Category
    template_name = 'core/category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)

class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'core/form.html'
    success_url = reverse_lazy('category_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class CategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'core/form.html'
    success_url = reverse_lazy('category_list')

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)

class CategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = Category
    template_name = 'core/confirm_delete.html'
    success_url = reverse_lazy('category_list')

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)


@login_required
def calendar_view(request):
    # Get month and year
    today = timezone.now().date()
    try:
        month = int(request.GET.get('month', today.month))
        year = int(request.GET.get('year', today.year))
    except ValueError:
        month = today.month
        year = today.year

    # Navigation logic
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    # Get transactions for the month
    _, last_day = calendar.monthrange(year, month)
    start_date = datetime.date(year, month, 1)
    end_date = datetime.date(year, month, last_day)

    transactions = Transaction.objects.filter(
        user=request.user,
        date__range=[start_date, end_date]
    )

    # Group by day
    transactions_by_day = {}
    for tx in transactions:
        day = tx.date.day
        if day not in transactions_by_day:
            transactions_by_day[day] = []
        transactions_by_day[day].append(tx)

    # Build calendar grid
    cal = calendar.Calendar(firstweekday=6) # Sunday first
    month_days = cal.monthdayscalendar(year, month)

    context = {
        'month_days': month_days,
        'transactions_by_day': transactions_by_day,
        'current_month': month,
        'current_year': year,
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        'month_name': calendar.month_name[month],
    }
    return render(request, 'core/calendar.html', context)

@login_required
def import_transactions(request):
    if request.method == 'POST':
        form = ImportFileForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['file']
            try:
                decoded_file = csv_file.read().decode('utf-8').splitlines()
                reader = csv.reader(decoded_file)
                next(reader, None) # Skip header
                
                count = 0
                for row in reader:
                    if len(row) >= 3:
                        # Assume format: Date (YYYY-MM-DD), Description, Amount, Category (Optional)
                        date_str = row[0].strip()
                        description = row[1].strip()
                        amount = float(row[2].strip())
                        
                        category_name = row[3].strip() if len(row) > 3 else None
                        
                        type_ = 'RECEITA' if amount > 0 else 'DESPESA'
                        
                        category = None
                        if category_name:
                            category, _ = Category.objects.get_or_create(
                                user=request.user,
                                name=category_name,
                                defaults={'type': type_}
                            )
                        
                        Transaction.objects.create(
                            user=request.user,
                            date=date_str,
                            description=description,
                            amount=abs(amount),
                            type=type_,
                            category=category
                        )
                        count += 1
                messages.success(request, f'{count} transações importadas com sucesso!')
                return redirect('transaction_list')
            except Exception as e:
                messages.error(request, f'Erro ao importar arquivo: {e}')
    else:
        form = ImportFileForm()
    
    return render(request, 'core/import.html', {'form': form})

# Transaction CRUD
class TransactionListView(LoginRequiredMixin, ListView):
    model = Transaction
    template_name = 'core/transaction_list.html'
    context_object_name = 'transactions'

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user).order_by('-date')

class TransactionCreateView(LoginRequiredMixin, CreateView):
    model = Transaction
    form_class = TransactionForm
    template_name = 'core/form.html'
    success_url = reverse_lazy('transaction_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        
        # Check for Credit Card Logic
        payment_method = form.cleaned_data.get('payment_method')
        if payment_method == 'CREDITO':
            installments = form.cleaned_data.get('installments')
            first_due_date = form.cleaned_data.get('first_due_date')
            total_amount = form.cleaned_data.get('amount')
            description = form.cleaned_data.get('description')
            category = form.cleaned_data.get('category')
            
            installment_amount = total_amount / installments
            
            # Create transactions for each installment
            for i in range(installments):
                # Calculate date
                month = first_due_date.month - 1 + i
                year = first_due_date.year + month // 12
                month = month % 12 + 1
                day = min(first_due_date.day, calendar.monthrange(year, month)[1])
                due_date = datetime.date(year, month, day)
                
                Transaction.objects.create(
                    user=self.request.user,
                    category=category,
                    type='DESPESA',
                    amount=installment_amount,
                    date=due_date,
                    payment_method='CREDITO',
                    description=f"{description} ({i+1}/{installments})"
                )
            
            messages.success(self.request, f'{installments} parcelas criadas com sucesso!')
            return redirect(self.success_url)
        
        # Check for Recurring Logic
        recurring = form.cleaned_data.get('recurring')
        if recurring:
            frequency = form.cleaned_data.get('frequency')
            # Calculate next run date based on frequency
            # For simplicity, next run is today + frequency delta, OR just today if it's due today.
            # But usually, if I create a recurring transaction today, I want it to repeat starting NEXT period?
            # Or does it mean "This transaction repeats"?
            # If I create a transaction today (01/01) and say "Monthly", the next one should be 01/02.
            
            # First, save the current transaction
            response = super().form_valid(form)
            
            # Then create the recurring rule
            next_date = form.instance.date
            if frequency == 'DIARIO':
                next_date += datetime.timedelta(days=1)
            elif frequency == 'SEMANAL':
                next_date += datetime.timedelta(weeks=1)
            elif frequency == 'QUINZENAL':
                next_date += datetime.timedelta(days=15)
            elif frequency == 'MENSAL':
                month = next_date.month - 1 + 1
                year = next_date.year + month // 12
                month = month % 12 + 1
                day = min(next_date.day, calendar.monthrange(year, month)[1])
                next_date = datetime.date(year, month, day)
            elif frequency == 'ANUAL':
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
                active=True
            )
            messages.success(self.request, 'Transação recorrente criada com sucesso!')
            return response

        return super().form_valid(form)

class TransactionUpdateView(LoginRequiredMixin, UpdateView):
    model = Transaction
    form_class = TransactionForm
    template_name = 'core/form.html'
    success_url = reverse_lazy('transaction_list')

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

class TransactionDeleteView(LoginRequiredMixin, DeleteView):
    model = Transaction
    template_name = 'core/confirm_delete.html'
    success_url = reverse_lazy('transaction_list')

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

# Budget CRUD
class BudgetListView(LoginRequiredMixin, ListView):
    model = Budget
    template_name = 'core/budget_list.html'
    context_object_name = 'budgets'

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        budgets = context['budgets']
        today = timezone.now().date()
        
        for budget in budgets:
            if budget.period == 'MENSAL':
                transactions = Transaction.objects.filter(
                    user=self.request.user,
                    category=budget.category,
                    type='DESPESA',
                    date__year=today.year,
                    date__month=today.month
                )
            else: # ANUAL
                transactions = Transaction.objects.filter(
                    user=self.request.user,
                    category=budget.category,
                    type='DESPESA',
                    date__year=today.year
                )
            
            spent = transactions.aggregate(Sum('amount'))['amount__sum'] or 0
            budget.spent = spent
            budget.percentage = (spent / budget.limit) * 100 if budget.limit > 0 else 0
            
            if budget.percentage >= 100:
                budget.status_color = 'danger'
            elif budget.percentage >= 75:
                budget.status_color = 'warning'
            else:
                budget.status_color = 'success'
                
        return context

class BudgetCreateView(LoginRequiredMixin, CreateView):
    model = Budget
    form_class = BudgetForm
    template_name = 'core/form.html'
    success_url = reverse_lazy('budget_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class BudgetUpdateView(LoginRequiredMixin, UpdateView):
    model = Budget
    form_class = BudgetForm
    template_name = 'core/form.html'
    success_url = reverse_lazy('budget_list')

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)

class BudgetDeleteView(LoginRequiredMixin, DeleteView):
    model = Budget
    template_name = 'core/confirm_delete.html'
    success_url = reverse_lazy('budget_list')

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)

@login_required
def reports(request):
    logger.info(f"Generating reports for user {request.user.username}")
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    category_id = request.GET.get('category')
    
    transactions = Transaction.objects.filter(user=request.user).order_by('-date')
    
    if start_date:
        transactions = transactions.filter(date__gte=start_date)
    if end_date:
        transactions = transactions.filter(date__lte=end_date)
    if category_id:
        transactions = transactions.filter(category_id=category_id)
        
    # Totals
    total_income = transactions.filter(type='RECEITA').aggregate(Sum('amount'))['amount__sum'] or 0
    total_expense = transactions.filter(type='DESPESA').aggregate(Sum('amount'))['amount__sum'] or 0
    net_balance = total_income - total_expense
    
    # Savings Rate
    savings_rate = 0
    if total_income > 0:
        savings_rate = ((total_income - total_expense) / total_income) * 100
    
    categories = Category.objects.filter(user=request.user)
    
    # 1. Expenses by Category (Pie Chart)
    expense_by_category = transactions.filter(type='DESPESA').values('category__name').annotate(total=Sum('amount')).order_by('-total')
    
    # 2. Monthly Evolution (Bar/Line Chart)
    evolution_qs = Transaction.objects.filter(user=request.user)
    if start_date: evolution_qs = evolution_qs.filter(date__gte=start_date)
    if end_date: evolution_qs = evolution_qs.filter(date__lte=end_date)
    
    if not start_date and not end_date:
        last_year = timezone.now().date() - timedelta(days=365)
        evolution_qs = evolution_qs.filter(date__gte=last_year)

    monthly_data = evolution_qs.annotate(month=TruncMonth('date')).values('month').annotate(
        income=Sum('amount', filter=Q(type='RECEITA')),
        expense=Sum('amount', filter=Q(type='DESPESA'))
    ).order_by('month')
    
    evolution_labels = []
    evolution_income = []
    evolution_expense = []
    
    for entry in monthly_data:
        if entry['month']:
            evolution_labels.append(entry['month'].strftime('%b/%Y'))
            evolution_income.append(float(entry['income'] or 0))
            evolution_expense.append(float(entry['expense'] or 0))

    # 3. Daily Expenses (Line Chart)
    daily_data = transactions.filter(type='DESPESA').annotate(day=TruncDay('date')).values('day').annotate(
        total=Sum('amount')
    ).order_by('day')
    
    daily_labels = []
    daily_expenses = []
    for entry in daily_data:
        if entry['day']:
            daily_labels.append(entry['day'].strftime('%d/%m'))
            daily_expenses.append(float(entry['total'] or 0))

    # 4. Budget vs Actual (Bar Chart)
    budgets = Budget.objects.filter(user=request.user)
    budget_labels = []
    budget_limits = []
    budget_actuals = []
    
    for budget in budgets:
        # Calculate actual spending for this category in the current month (or selected period)
        # For simplicity, we'll use the filtered transactions if they match the category
        # But ideally, budget is monthly, so we should filter by current month if no date selected
        
        # Using the filtered 'transactions' queryset might be too restrictive if the user selected a custom range
        # that doesn't match the budget period. However, for a "Reports" page, showing budget status 
        # based on the *selected filter* is a reasonable approach for "Spending vs Limit in this period".
        
        actual = transactions.filter(category=budget.category, type='DESPESA').aggregate(Sum('amount'))['amount__sum'] or 0
        
        budget_labels.append(budget.category.name)
        budget_limits.append(float(budget.limit))
        budget_actuals.append(float(actual))

    # 5. Recent Transactions (Table)
    recent_transactions = transactions.order_by('-date', '-id')[:20]

    # 6. Top Expenses (Table) - Keep existing logic but maybe rename context variable if needed, 
    # but 'top_expenses' is fine.
    top_expenses = transactions.filter(type='DESPESA').order_by('-amount')[:5]

    context = {
        'categories': categories,
        'total_income': total_income,
        'total_expense': total_expense,
        'net_balance': net_balance,
        'savings_rate': savings_rate,
        'expense_by_category': expense_by_category,
        'top_expenses': top_expenses,
        'evolution_labels': json.dumps(evolution_labels),
        'evolution_income': json.dumps(evolution_income),
        'evolution_expense': json.dumps(evolution_expense),
        'daily_labels': json.dumps(daily_labels),
        'daily_expenses': json.dumps(daily_expenses),
        'budget_labels': json.dumps(budget_labels),
        'budget_limits': json.dumps(budget_limits),
        'budget_actuals': json.dumps(budget_actuals),
        'recent_transactions': recent_transactions,
    }
    return render(request, 'core/reports.html', context)

@login_required
def export_csv(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    category_id = request.GET.get('category')
    
    transactions = Transaction.objects.filter(user=request.user).order_by('-date')
    
    if start_date:
        transactions = transactions.filter(date__gte=start_date)
    if end_date:
        transactions = transactions.filter(date__lte=end_date)
    if category_id:
        transactions = transactions.filter(category_id=category_id)
        
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="transactions.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Date', 'Type', 'Category', 'Amount', 'Description'])
    
    for t in transactions:
        writer.writerow([t.date, t.get_type_display(), t.category.name if t.category else '-', t.amount, t.description])
        
    return response

@login_required
def export_pdf(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    category_id = request.GET.get('category')
    
    transactions = Transaction.objects.filter(user=request.user).order_by('-date')
    
    if start_date:
        transactions = transactions.filter(date__gte=start_date)
    if end_date:
        transactions = transactions.filter(date__lte=end_date)
    if category_id:
        transactions = transactions.filter(category_id=category_id)
    
    total_income = transactions.filter(type='RECEITA').aggregate(Sum('amount'))['amount__sum'] or 0
    total_expense = transactions.filter(type='DESPESA').aggregate(Sum('amount'))['amount__sum'] or 0
    net_balance = total_income - total_expense
    
    context = {
        'transactions': transactions,
        'total_income': total_income,
        'total_expense': total_expense,
        'net_balance': net_balance,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    template_path = 'core/reports_pdf.html'
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="relatorio_financeiro.pdf"'
    
    template = get_template(template_path)
    html = template.render(context)
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        return HttpResponse('We had some errors <pre>' + html + '</pre>')
    return response

# Investment CRUD
class InvestmentListView(LoginRequiredMixin, ListView):
    model = Investment
    template_name = 'core/investment_list.html'
    context_object_name = 'investments'

    def get_queryset(self):
        return Investment.objects.filter(user=self.request.user)

class InvestmentDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'core/investment_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        symbol = self.kwargs['symbol']
        
        investments = Investment.objects.filter(user=self.request.user, symbol=symbol)
        if not investments.exists():
            raise Http404("Investimento não encontrado")
            
        # Aggregate
        total_quantity = sum(inv.quantity for inv in investments)
        total_invested = sum(inv.total_cost for inv in investments)
        avg_price = total_invested / total_quantity if total_quantity > 0 else 0
        
        # Mock object for template
        investment_data = {
            'symbol': symbol,
            'name': investments.first().name,
            'quantity': total_quantity,
            'total_cost': total_invested,
            'purchase_price': avg_price,
            'pk': investments.first().pk # For edit link (maybe just link to list or first one)
        }
        context['investment'] = investment_data
        
        # Fetch historical data
        try:
            ticker = yf.Ticker(symbol)
            # Get 6 months of history
            history = ticker.history(period="6mo")
            
            dates = []
            prices = []
            
            for date, row in history.iterrows():
                dates.append(date.strftime('%d/%m/%Y'))
                prices.append(row['Close'])
                
            context['chart_labels'] = json.dumps(dates)
            context['chart_data'] = json.dumps(prices)
            
            # Current info
            try:
                current_price = ticker.fast_info.last_price
                previous_close = ticker.fast_info.previous_close
                day_change = ((current_price - previous_close) / previous_close) * 100
            except:
                # Fallback to history if fast_info fails
                current_price = history['Close'].iloc[-1] if not history.empty else 0
                day_change = 0

            context['current_price'] = current_price
            context['day_change'] = day_change
            
            # Calculate profit/loss
            current_value = float(total_quantity) * float(current_price)
            invested_value = float(total_invested)
            context['current_value'] = current_value
            context['profit_loss'] = current_value - invested_value
            context['profit_loss_pct'] = (context['profit_loss'] / invested_value) * 100 if invested_value > 0 else 0
            
        except Exception as e:
            print(f"Error fetching history: {e}")
            context['error'] = str(e)
            
        return context

class InvestmentCreateView(LoginRequiredMixin, CreateView):
    model = Investment
    form_class = InvestmentForm
    template_name = 'core/investment_form.html'
    success_url = reverse_lazy('investment_dashboard')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class InvestmentUpdateView(LoginRequiredMixin, UpdateView):
    model = Investment
    form_class = InvestmentForm
    template_name = 'core/investment_form.html'
    success_url = reverse_lazy('investment_dashboard')

    def form_valid(self, form):
        # Allow updating skip flag during edit too
        if not form.cleaned_data.get('create_transaction'):
            form.instance._skip_transaction = True
        return super().form_valid(form)

    def get_queryset(self):
        return Investment.objects.filter(user=self.request.user)

class InvestmentDeleteView(LoginRequiredMixin, DeleteView):
    model = Investment
    template_name = 'core/confirm_delete.html'
    success_url = reverse_lazy('investment_dashboard')

    def get_queryset(self):
        return Investment.objects.filter(user=self.request.user)

# Goal CRUD
class GoalListView(LoginRequiredMixin, ListView):
    model = Goal
    template_name = 'core/goal_list.html'
    context_object_name = 'goals'

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user)

class GoalCreateView(LoginRequiredMixin, CreateView):
    model = Goal
    form_class = GoalForm
    template_name = 'core/form.html'
    success_url = reverse_lazy('goal_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Meta criada com sucesso!')
        return super().form_valid(form)

class GoalUpdateView(LoginRequiredMixin, UpdateView):
    model = Goal
    form_class = GoalForm
    template_name = 'core/form.html'
    success_url = reverse_lazy('goal_list')

    def form_valid(self, form):
        messages.success(self.request, 'Meta atualizada com sucesso!')
        return super().form_valid(form)

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user)

class GoalDeleteView(LoginRequiredMixin, DeleteView):
    model = Goal
    template_name = 'core/confirm_delete.html'
    success_url = reverse_lazy('goal_list')

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user)

from .market_data import get_latest_indicator, calculate_cdi_correction, calculate_pre_fixado, get_real_time_currency, SERIES_SELIC_META, SERIES_CDI_MENSAL

@login_required
def safe_haven_dashboard(request):
    # 1. Fetch Key Indicators
    usd_rate = get_real_time_currency('USD') or 0.0
    eur_rate = get_real_time_currency('EUR') or 0.0
    selic_rate = get_latest_indicator(SERIES_SELIC_META)
    cdi_rate = selic_rate - 0.10 # Approximation if exact CDI series isn't returning specific 'annual' rate instantly, or use monthly * 12

    # 2. Process Assets
    safe_investments = Investment.objects.filter(
        user=request.user, 
        category_type__in=['FIXED', 'CURRENCY', 'POUPANCA']
    )

    fixed_assets = []
    my_currencies = []
    
    total_fixed_invested = 0
    total_fixed_current = 0

    for inv in safe_investments:
        current_val = float(inv.total_cost) # Default
        
        # Logic for Fixed Income
        if inv.category_type in ['FIXED', 'POUPANCA']:
            if inv.index_type == 'CDI':
                current_val = calculate_cdi_correction(inv.total_cost, inv.date, percentage_of_cdi=inv.fixed_rate or 100)
            elif inv.index_type == 'PRE':
                current_val = calculate_pre_fixado(inv.total_cost, inv.date, rate_yearly=inv.fixed_rate)
            elif inv.index_type == 'IPCA':
                 # Estimation
                 rate = 4.0 + float(inv.fixed_rate or 0)
                 current_val = calculate_pre_fixado(inv.total_cost, inv.date, rate_yearly=rate)
            
            gain = current_val - float(inv.total_cost)
            
            fixed_assets.append({
                'investment': inv,
                'rate_display': f"{inv.fixed_rate or 100}% {inv.get_index_type_display()}",
                'current_value': current_val,
                'gain': gain
            })
            
            total_fixed_invested += float(inv.total_cost)
            total_fixed_current += current_val

        # Logic for Currencies
        elif inv.category_type == 'CURRENCY':
            rate = 1.0
            if 'USD' in inv.symbol.upper(): rate = usd_rate
            elif 'EUR' in inv.symbol.upper(): rate = eur_rate
            
            current_val = float(inv.quantity) * rate
            
            my_currencies.append({
                'investment': inv,
                'current_price': rate,
                'current_value': current_val
            })

    context = {
        'usd_rate': usd_rate,
        'eur_rate': eur_rate,
        'selic_rate': selic_rate,
        'cdi_rate': cdi_rate,
        'fixed_assets': fixed_assets,
        'currencies': my_currencies, # Holdings
        'total_fixed_invested': total_fixed_invested,
        'total_fixed_current': total_fixed_current,
    }
    return render(request, 'core/safe_haven_dashboard.html', context)
