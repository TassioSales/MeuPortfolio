from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
import logging
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.template.loader import get_template
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from datetime import timedelta
import calendar
import csv
import json
import os
import shutil
import tempfile
import certifi
from xhtml2pdf import pisa
import yfinance as yf
from .models import Transaction, Category, Budget, Investment
from django.db.models.functions import TruncMonth, TruncDay
from .forms import CategoryForm, TransactionForm, BudgetForm, InvestmentForm

logger = logging.getLogger('core')

# Fix for SSL error with spaces in path (curl 77)
def fix_ssl():
    ca_bundle = certifi.where()
    if ' ' in ca_bundle:
        # Create a temp copy if path has spaces
        temp_dir = tempfile.gettempdir()
        temp_cert = os.path.join(temp_dir, 'cacert.pem')
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
    if not ticker_symbol:
        return JsonResponse({'error': 'Ticker is required'}, status=400)
    
    # Auto-append .SA if it looks like B3
    if any(char.isdigit() for char in ticker_symbol) and '.' not in ticker_symbol and '-' not in ticker_symbol:
         ticker_symbol += '.SA'

    try:
        ticker = yf.Ticker(ticker_symbol)
        # Try fetching info (fastest check)
        info = ticker.info
        
        # Some tickers return empty info but are valid, try history
        if not info or 'regularMarketPrice' not in info:
             history = ticker.history(period='1d')
             if history.empty:
                 return JsonResponse({'error': f'Ticker {ticker_symbol} not found or delisted'}, status=404)
             price = history['Close'].iloc[-1]
             name = ticker_symbol # Fallback name
             currency = 'BRL' # Default assumption if info missing, but risky.
        else:
             price = info.get('currentPrice') or info.get('regularMarketPrice')
             name = info.get('longName') or info.get('shortName') or ticker_symbol
             currency = info.get('currency', 'BRL')

        # Currency Conversion Logic
        usd_brl_rate = 1.0
        if currency == 'USD':
            try:
                usd_brl_rate = yf.Ticker("BRL=X").history(period='1d')['Close'].iloc[-1]
                price = price * usd_brl_rate
                currency = 'BRL' # Converted
            except Exception as e:
                print(f"Error converting currency: {e}")
        
        # Extract additional data
        previous_close = info.get('previousClose')
        day_high = info.get('dayHigh')
        day_low = info.get('dayLow')
        year_high = info.get('fiftyTwoWeekHigh')
        year_low = info.get('fiftyTwoWeekLow')
        
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
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

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
        usd_brl_rate = yf.Ticker("BRL=X").history(period='1d')['Close'].iloc[-1]
    except:
        usd_brl_rate = 5.0 # Fallback

    # Aggregate investments by symbol
    aggregated_portfolio = {}
    for inv in investments:
        symbol = inv.symbol
        if symbol not in aggregated_portfolio:
            aggregated_portfolio[symbol] = {
                'symbol': symbol,
                'name': inv.name,
                'quantity': 0.0,
                'total_cost': 0.0,
            }
        
        aggregated_portfolio[symbol]['quantity'] += float(inv.quantity)
        aggregated_portfolio[symbol]['total_cost'] += float(inv.total_cost)
        # Update name if missing
        if not aggregated_portfolio[symbol]['name'] and inv.name:
            aggregated_portfolio[symbol]['name'] = inv.name

    for symbol, data in aggregated_portfolio.items():
        quantity = data['quantity']
        invested_value = data['total_cost']
        avg_price = invested_value / quantity if quantity > 0 else 0
        
        total_invested += invested_value
        
        # Fetch current price
        try:
            ticker = yf.Ticker(symbol)
            history = ticker.history(period='1d')
            if not history.empty:
                current_price = history['Close'].iloc[-1]
                
                # Check currency
                is_brl = symbol.endswith('.SA')
                if not is_brl:
                     current_price = current_price * usd_brl_rate
            else:
                current_price = avg_price # Fallback to avg price
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

@login_required
def dashboard(request):
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

    context = {
        'recent_transactions': recent_transactions,
        'monthly_income': monthly_income,
        'monthly_expense': monthly_expense,
        'net_balance': net_balance,
        'chart_labels': json.dumps(labels),
        'chart_income': json.dumps(data_income),
        'chart_expense': json.dumps(data_expense),
        'current_month_name': current_month_name,
        'previous_month': previous_month,
        'next_month': next_month,
        'selected_month': month,
        'selected_year': year,
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

class InvestmentCreateView(LoginRequiredMixin, CreateView):
    model = Investment
    form_class = InvestmentForm
    template_name = 'core/form.html'
    success_url = reverse_lazy('investment_dashboard')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class InvestmentUpdateView(LoginRequiredMixin, UpdateView):
    model = Investment
    form_class = InvestmentForm
    template_name = 'core/form.html'
    success_url = reverse_lazy('investment_dashboard')

    def get_queryset(self):
        return Investment.objects.filter(user=self.request.user)

class InvestmentDeleteView(LoginRequiredMixin, DeleteView):
    model = Investment
    template_name = 'core/confirm_delete.html'
    success_url = reverse_lazy('investment_dashboard')

    def get_queryset(self):
        return Investment.objects.filter(user=self.request.user)
