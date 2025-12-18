from django import forms
from .models import Category, Transaction, Budget, Investment, RecurringTransaction, Goal
from decimal import Decimal

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'type', 'parent']

class TransactionForm(forms.ModelForm):
    installments = forms.IntegerField(required=False, min_value=1, max_value=48, label="Parcelas", initial=1)
    first_due_date = forms.DateField(required=False, label="Data do 1º Vencimento", widget=forms.DateInput(attrs={'type': 'date'}))
    recurring = forms.BooleanField(required=False, label="Repetir?", widget=forms.CheckboxInput(attrs={'onclick': 'toggleRecurringFields(this)'}))
    frequency = forms.ChoiceField(required=False, choices=RecurringTransaction.FREQUENCY_CHOICES, label="Frequência")

    class Meta:
        model = Transaction
        fields = ['category', 'type', 'amount', 'date', 'payment_method', 'description']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'payment_method': forms.Select(attrs={'onchange': 'toggleCreditCardFields(this)'}),
            'amount': forms.TextInput(attrs={'class': 'money-mask', 'placeholder': 'R$ 0,00'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        type_ = cleaned_data.get('type')
        category = cleaned_data.get('category')
        payment_method = cleaned_data.get('payment_method')
        installments = cleaned_data.get('installments')
        first_due_date = cleaned_data.get('first_due_date')

        if type_ in ['RECEITA', 'DESPESA'] and not category:
            self.add_error('category', 'Category is required for income/expense.')
        
        if payment_method == 'CREDITO':
            if not installments:
                self.add_error('installments', 'Informe o número de parcelas.')
            if not first_due_date:
                self.add_error('first_due_date', 'Informe a data do primeiro vencimento.')
        
        recurring = cleaned_data.get('recurring')
        frequency = cleaned_data.get('frequency')
        if recurring and not frequency:
            self.add_error('frequency', 'Informe a frequência da repetição.')

        return cleaned_data

class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['category', 'limit', 'period', 'start_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'limit': forms.TextInput(attrs={'class': 'money-mask', 'placeholder': 'R$ 0,00'}),
        }

class InvestmentForm(forms.ModelForm):
    purchase_price = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'money-mask', 'placeholder': 'R$ 0,00'}),
        label='Preço de Compra'
    )

    class Meta:
        model = Investment
        fields = ['symbol', 'quantity', 'purchase_price', 'date']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        symbol = cleaned_data.get('symbol')
        
        if symbol:
            symbol = symbol.upper().strip()
            # Heuristic: If it ends in a digit (e.g. PETR4, MXRF11) and has no dot/hyphen, assume B3
            if any(char.isdigit() for char in symbol) and '.' not in symbol and '-' not in symbol:
                symbol += '.SA'
            
            cleaned_data['symbol'] = symbol
            
            # Fetch name from yfinance
            try:
                import yfinance as yf
                ticker = yf.Ticker(symbol)
                info = ticker.info
                # Try to get shortName, longName, or fallback to symbol
                name = info.get('shortName') or info.get('longName') or symbol
                self.instance.name = name
            except Exception:
                # If fetching fails, just use the symbol or leave empty
                pass
                
        return cleaned_data

    def clean_purchase_price(self):
        price = self.cleaned_data.get('purchase_price')
        if isinstance(price, str):
            price = price.replace('R$', '').replace('.', '').replace(',', '.').strip()
        try:
            return Decimal(price)
        except (ValueError, TypeError):
            raise forms.ValidationError("Informe um número válido.")

class ImportFileForm(forms.Form):
    file = forms.FileField(label="Arquivo de Extrato (CSV)")

class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ['name', 'target_amount', 'current_amount', 'deadline', 'description']
        widgets = {
            'deadline': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'target_amount': forms.TextInput(attrs={'class': 'money-mask', 'placeholder': 'R$ 0,00'}),
            'current_amount': forms.TextInput(attrs={'class': 'money-mask', 'placeholder': 'R$ 0,00'}),
        }
