from django import forms
from .models import Category, Transaction, Budget, Investment

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'type', 'parent']

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['category', 'type', 'amount', 'date', 'recurring', 'frequency', 'description']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        type_ = cleaned_data.get('type')
        category = cleaned_data.get('category')

        if type_ in ['RECEITA', 'DESPESA'] and not category:
            self.add_error('category', 'Category is required for income/expense.')
        
        return cleaned_data

class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['category', 'limit', 'period', 'start_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
        }

class InvestmentForm(forms.ModelForm):
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
