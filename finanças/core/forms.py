from django import forms
from .models import Category, Transaction, Budget, Investment, RecurringTransaction, Goal, BankAccount, Transfer, Loan, LoanPayment, LoanDisbursement
from decimal import Decimal

def clean_currency_value(value):
    if isinstance(value, str):
        # Remove currency symbol and whitespace
        value = value.replace('R$', '').replace('$', '').strip()
        
        # Heuristic: If there's only one dot OR one comma, and it's near the end, 
        # it's likely a decimal separator, not a thousand separator.
        if value.count('.') == 1 and value.count(',') == 0:
            # Already in Python format (or US format), keep it
            pass
        elif value.count(',') == 1 and value.count('.') == 0:
            # Traditional Brazilian decimal (10,50), convert to (10.50)
            value = value.replace(',', '.')
        else:
            # Mixed format (1.000,50), remove thousand sep and convert decimal sep
            value = value.replace('.', '').replace(',', '.')
            
    try:
        if not value:
            return None
        return Decimal(value)
    except (ValueError, TypeError, Decimal.InvalidOperation):
        raise forms.ValidationError("Informe um número válido.")

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'type', 'parent']

class TransactionForm(forms.ModelForm):
    installments = forms.IntegerField(required=False, min_value=1, max_value=48, label="Parcelas", initial=1)
    first_due_date = forms.DateField(required=False, label="Data do 1º Vencimento", widget=forms.DateInput(attrs={'type': 'date'}))
    recurring = forms.BooleanField(required=False, label="Repetir?", widget=forms.CheckboxInput(attrs={'onclick': 'toggleRecurringFields(this)'}))
    frequency = forms.ChoiceField(required=False, choices=RecurringTransaction.FREQUENCY_CHOICES, label="Frequência")
    recurrence_end_date = forms.DateField(required=False, label="Repetir até...", widget=forms.DateInput(attrs={'type': 'date'}))
    amount = forms.CharField(label="Valor", widget=forms.TextInput(attrs={'class': 'money-mask', 'placeholder': 'R$ 0,00'}))

    class Meta:
        model = Transaction
        fields = ['category', 'type', 'amount', 'date', 'payment_method', 'description']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'payment_method': forms.Select(attrs={'onchange': 'toggleCreditCardFields(this)'}),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        # If the field is already a Decimal (Django might have tried its own cleaning), handle it
        if isinstance(amount, Decimal):
            return amount
        # Otherwise clean the string
        return clean_currency_value(self.data.get('amount'))

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
    limit = forms.CharField(label="Limite", widget=forms.TextInput(attrs={'class': 'money-mask', 'placeholder': 'R$ 0,00'}))

    class Meta:
        model = Budget
        fields = ['category', 'limit', 'period', 'start_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_limit(self):
        return clean_currency_value(self.data.get('limit'))

class InvestmentForm(forms.ModelForm):
    purchase_price = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'money-mask', 'placeholder': 'R$ 0,00'}),
        label='Preço de Compra'
    )
    create_transaction = forms.BooleanField(
        required=False,
        initial=True,
        label='Registrar como Transação de Saída?',
        help_text="Desmarque se este for um investimento antigo que você apenas deseja monitorar saldo."
    )

    class Meta:
        model = Investment
        fields = ['category_type', 'symbol', 'name', 'quantity', 'purchase_price', 'date', 'fixed_rate', 'index_type', 'due_date', 'tax_free']
        widgets = {
            'category_type': forms.Select(attrs={'onchange': 'toggleInvestmentFields(this)'}),
            'date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add classes for JS targeting
        self.fields['fixed_rate'].widget.attrs.update({'class': 'field-fixed'})
        self.fields['index_type'].widget.attrs.update({'class': 'field-fixed'})
        self.fields['due_date'].widget.attrs.update({'class': 'field-fixed'})
        self.fields['tax_free'].widget.attrs.update({'class': 'field-fixed'})
        
        # Add placeholders/hints
        self.fields['symbol'].widget.attrs.update({'placeholder': 'Ex: PETR4, USD, CDB-ITAU'})

    def clean(self):
        cleaned_data = super().clean()
        symbol = cleaned_data.get('symbol')
        category_type = cleaned_data.get('category_type')
        
        if not symbol:
            return cleaned_data

        symbol = symbol.upper().strip()
        cleaned_data['symbol'] = symbol

        # 1. Validation and logic based on type
        if category_type == 'FIXED':
            if not cleaned_data.get('index_type'):
                self.add_error('index_type', 'Índice é obrigatório para Renda Fixa.')
            if not cleaned_data.get('fixed_rate'):
                self.add_error('fixed_rate', 'Taxa é obrigatória para Renda Fixa.')
        
        elif category_type == 'VARIABLE':
            # Auto-append .SA for B3 stocks
            if any(char.isdigit() for char in symbol) and '.' not in symbol and '-' not in symbol:
                symbol += '.SA'
                cleaned_data['symbol'] = symbol
            
            # Name fetch logic (simplified here, but can be triggered by JS too)
            if not cleaned_data.get('name'):
                try:
                    import yfinance as yf
                    ticker = yf.Ticker(symbol)
                    info = ticker.info
                    cleaned_data['name'] = info.get('shortName') or info.get('longName') or symbol
                except:
                    pass
        
        elif category_type == 'CURRENCY':
            # Normalize common currency names to pairs if needed, 
            # but usually the user just types USD or EUR.
            pass

        # 2. Clear irrelevant fields based on type to avoid junk data
        if category_type != 'FIXED':
            cleaned_data['fixed_rate'] = None
            cleaned_data['index_type'] = None
            cleaned_data['due_date'] = None
            cleaned_data['tax_free'] = False
        
        return cleaned_data

    def clean_purchase_price(self):
        # Using self.data instead of cleaned_data because cleaned_data might fail
        # standard validation for non-numeric input before reaching here
        return clean_currency_value(self.data.get('purchase_price'))

class ImportFileForm(forms.Form):
    file = forms.FileField(label="Arquivo de Extrato (CSV)")

class GoalForm(forms.ModelForm):
    target_amount = forms.CharField(label="Valor Alvo", widget=forms.TextInput(attrs={'class': 'money-mask', 'placeholder': 'R$ 0,00'}))
    current_amount = forms.CharField(label="Valor Atual", widget=forms.TextInput(attrs={'class': 'money-mask', 'placeholder': 'R$ 0,00'}))

    class Meta:
        model = Goal
        fields = ['name', 'target_amount', 'current_amount', 'deadline', 'description']
        widgets = {
            'deadline': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_target_amount(self):
        return clean_currency_value(self.data.get('target_amount'))

    def clean_current_amount(self):
        return clean_currency_value(self.data.get('current_amount'))


class BankAccountForm(forms.ModelForm):
    balance = forms.CharField(label="Saldo Inicial", widget=forms.TextInput(attrs={'class': 'money-mask', 'placeholder': 'R$ 0,00'}))

    class Meta:
        model = BankAccount
        fields = ['name', 'account_type', 'balance', 'bank_name', 'is_active']

    def clean_balance(self):
        return clean_currency_value(self.data.get('balance'))


class TransferForm(forms.ModelForm):
    amount = forms.CharField(label="Valor", widget=forms.TextInput(attrs={'class': 'money-mask', 'placeholder': 'R$ 0,00'}))

    class Meta:
        model = Transfer
        fields = ['from_account', 'to_account', 'amount', 'date', 'description']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['from_account'].queryset = BankAccount.objects.filter(user=user, is_active=True)
        self.fields['to_account'].queryset = BankAccount.objects.filter(user=user, is_active=True)

    def clean_amount(self):
        return clean_currency_value(self.data.get('amount'))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('from_account') == cleaned.get('to_account'):
            raise forms.ValidationError("Conta de origem e destino não podem ser iguais.")
        return cleaned


class LoanForm(forms.ModelForm):
    principal = forms.CharField(label="Valor Original (R$)", widget=forms.TextInput(attrs={'class': 'money-mask', 'placeholder': 'R$ 0,00'}))
    current_balance = forms.CharField(label="Saldo Devedor Atual (R$)", widget=forms.TextInput(attrs={'class': 'money-mask', 'placeholder': 'R$ 0,00'}), required=False, help_text="Deixe vazio se for um novo empréstimo (usa o valor original)")
    interest_rate = forms.CharField(label="Taxa de Juros (%)", widget=forms.TextInput(attrs={'placeholder': 'Ex: 1.0 para 1%/mês'}))

    iof_rate = forms.CharField(
        label='IOF (%)', required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Ex: 3.0  (0 = sem IOF)'}),
        help_text='Percentual sobre o principal. Deixe vazio para empréstimos informais.'
    )
    insurance_monthly = forms.CharField(
        label='Seguro Mensal (R$)', required=False,
        widget=forms.TextInput(attrs={'class': 'money-mask', 'placeholder': 'R$ 0,00'}),
        help_text='Seguro prestamista fixo por mês. Deixe vazio se não houver.'
    )

    class Meta:
        model = Loan
        fields = [
            'name', 'lender', 'loan_type', 'principal', 'current_balance',
            'interest_rate', 'interest_period', 'iof_rate', 'insurance_monthly',
            'start_date', 'due_day', 'num_installments', 'notes', 'is_active',
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'loan_type': forms.Select(attrs={'onchange': 'toggleLoanFields(this)'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_principal(self):
        return clean_currency_value(self.data.get('principal'))

    def clean_current_balance(self):
        val = self.data.get('current_balance', '').strip()
        if not val:
            return None
        return clean_currency_value(val)

    def clean_interest_rate(self):
        val = self.data.get('interest_rate', '').strip().replace(',', '.')
        try:
            return Decimal(val)
        except Exception:
            raise forms.ValidationError("Informe uma taxa válida (ex: 1.0)")

    def clean_iof_rate(self):
        val = self.data.get('iof_rate', '').strip().replace(',', '.')
        if not val:
            return Decimal('0')
        try:
            return Decimal(val)
        except Exception:
            raise forms.ValidationError("Informe uma taxa válida (ex: 3.0)")

    def clean_insurance_monthly(self):
        val = self.data.get('insurance_monthly', '').strip()
        if not val:
            return Decimal('0')
        return clean_currency_value(val)

    def clean(self):
        cleaned = super().clean()
        loan_type = cleaned.get('loan_type')
        num_installments = cleaned.get('num_installments')
        if loan_type in ('PRICE', 'SAC') and not num_installments:
            self.add_error('num_installments', 'Número de parcelas obrigatório para esta modalidade.')
        current_balance = cleaned.get('current_balance')
        principal = cleaned.get('principal')
        if not current_balance and principal:
            cleaned['current_balance'] = principal
        return cleaned


class LoanPaymentForm(forms.ModelForm):
    amount_paid = forms.CharField(label="Valor Pago (R$)", widget=forms.TextInput(attrs={'class': 'money-mask', 'placeholder': 'R$ 0,00'}))

    class Meta:
        model = LoanPayment
        fields = ['payment_date', 'amount_paid', 'notes']
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_amount_paid(self):
        return clean_currency_value(self.data.get('amount_paid'))


class LoanAddFundsForm(forms.Form):
    """Form for adding more money to an existing loan (same lender, same terms)."""
    amount = forms.CharField(
        label='Valor Adicional (R$)',
        widget=forms.TextInput(attrs={'class': 'money-mask', 'placeholder': 'R$ 0,00'})
    )
    date = forms.DateField(
        label='Data do Novo Desembolso',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    note = forms.CharField(
        label='Motivo / Observação', max_length=255, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Ex: Necessidade extra, reforma...'})
    )

    def clean_amount(self):
        return clean_currency_value(self.data.get('amount'))
