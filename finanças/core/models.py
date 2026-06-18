from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal

class Category(models.Model):
    CATEGORY_TYPES = [
        ('RECEITA', 'Receita'),
        ('DESPESA', 'Despesa'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories', verbose_name='Usuário')
    name = models.CharField(max_length=100, verbose_name='Nome da Categoria')
    type = models.CharField(max_length=10, choices=CATEGORY_TYPES, default='DESPESA', verbose_name='Tipo')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories', verbose_name='Categoria Pai')

    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('RECEITA', 'Receita'),
        ('DESPESA', 'Despesa'),
    ]
    

    PAYMENT_METHODS = [
        ('DINHEIRO', 'Dinheiro'),
        ('PIX', 'Pix'),
        ('DEBITO', 'Débito'),
        ('CREDITO', 'Crédito'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions', verbose_name='Usuário')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions', verbose_name='Categoria')
    type = models.CharField(max_length=15, choices=TRANSACTION_TYPES, verbose_name='Tipo')
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Valor')
    date = models.DateField(default=timezone.now, verbose_name='Data')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='DINHEIRO', verbose_name='Método de Pagamento')
    description = models.CharField(max_length=255, blank=True, verbose_name='Descrição')
    account = models.ForeignKey('BankAccount', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions', verbose_name='Conta')

    class Meta:
        verbose_name = 'Transação'
        verbose_name_plural = 'Transações'

    def __str__(self):
        return f"{self.get_type_display()} - {self.amount} - {self.date}"

class RecurringTransaction(models.Model):
    FREQUENCY_CHOICES = [
        ('DIARIO', 'Diário'),
        ('SEMANAL', 'Semanal'),
        ('QUINZENAL', 'Quinzenal'),
        ('MENSAL', 'Mensal'),
        ('ANUAL', 'Anual'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recurring_transactions', verbose_name='Usuário')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Categoria')
    type = models.CharField(max_length=15, choices=Transaction.TRANSACTION_TYPES, verbose_name='Tipo')
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Valor')
    payment_method = models.CharField(max_length=20, choices=Transaction.PAYMENT_METHODS, default='DINHEIRO', verbose_name='Método de Pagamento')
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='MENSAL', verbose_name='Frequência')
    description = models.CharField(max_length=255, blank=True, verbose_name='Descrição')
    next_run_date = models.DateField(verbose_name='Próxima Execução')
    active = models.BooleanField(default=True, verbose_name='Ativo')

    class Meta:
        verbose_name = 'Transação Recorrente'
        verbose_name_plural = 'Transações Recorrentes'

    def __str__(self):
        return f"{self.description} ({self.get_frequency_display()})"

class Budget(models.Model):
    PERIOD_CHOICES = [
        ('MENSAL', 'Mensal'),
        ('ANUAL', 'Anual'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budgets', verbose_name='Usuário')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='budgets', verbose_name='Categoria')
    limit = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Limite')
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES, default='MENSAL', verbose_name='Período')
    start_date = models.DateField(default=timezone.now, verbose_name='Data de Início')
    rollover = models.BooleanField(default=False, verbose_name='Acumular saldo não gasto?')

    class Meta:
        verbose_name = 'Orçamento'
        verbose_name_plural = 'Orçamentos'

    def __str__(self):
        return f"Orçamento para {self.category.name}: {self.limit}"

class Investment(models.Model):
    CATEGORY_CHOICES = [
        ('VARIABLE', 'Renda Variável'),
        ('FIXED', 'Renda Fixa'),
        ('CURRENCY', 'Moedas'),
    ]

    INDEX_CHOICES = [
        ('CDI', 'CDI'),
        ('IPCA', 'IPCA'),
        ('PRE', 'Pré-fixado'),
        ('POUPANCA', 'Poupança'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='investments', verbose_name='Usuário')
    category_type = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default='VARIABLE', verbose_name='Tipo de Categoria')
    symbol = models.CharField(max_length=20, verbose_name='Símbolo (Ticker)')
    name = models.CharField(max_length=100, blank=True, verbose_name='Nome do Ativo')
    quantity = models.DecimalField(max_digits=15, decimal_places=4, verbose_name='Quantidade')
    purchase_price = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Preço de Compra')
    date = models.DateField(default=timezone.now, verbose_name='Data da Compra')
    
    # Fixed Income Specific
    fixed_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='Taxa (%)', help_text="Ex: 120 para 120% do CDI ou 10.5 para 10.5% a.a.")
    index_type = models.CharField(max_length=10, choices=INDEX_CHOICES, null=True, blank=True, verbose_name='Índice')
    due_date = models.DateField(null=True, blank=True, verbose_name='Data de Vencimento')
    tax_free = models.BooleanField(default=False, verbose_name='Isento de IR?')
    
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, null=True, blank=True, related_name='investment', verbose_name='Transação Associada')

    class Meta:
        verbose_name = 'Investimento'
        verbose_name_plural = 'Investimentos'

    def __str__(self):
        return f"{self.symbol} - {self.quantity} un."

    @property
    def total_cost(self):
        return self.quantity * self.purchase_price

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Check if we should skip transaction creation
        if getattr(self, '_skip_transaction', False):
            return

        # Create or update associated transaction
        if not self.transaction:
            # Find or create 'Investimentos' category
            category, _ = Category.objects.get_or_create(
                user=self.user, 
                name='Investimentos', 
                defaults={'type': 'DESPESA'}
            )
            
            transaction = Transaction.objects.create(
                user=self.user,
                category=category,
                type='DESPESA',
                amount=self.total_cost,
                date=self.date,
                description=f"Compra de {self.symbol} ({self.quantity} un.)"
            )
            self.transaction = transaction
            self.save()
        else:
            # Update existing transaction
            self.transaction.amount = self.total_cost
            self.transaction.date = self.date
            self.transaction.description = f"Compra de {self.symbol} ({self.quantity} un.)"
            self.transaction.save()

class Goal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='goals', verbose_name='Usuário')
    name = models.CharField(max_length=100, verbose_name='Nome da Meta')
    target_amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Valor Alvo')
    current_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Valor Atual')
    monthly_target = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, verbose_name='Aporte Mensal Planejado')
    deadline = models.DateField(verbose_name='Data Limite')
    description = models.TextField(blank=True, verbose_name='Descrição')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')

    class Meta:
        verbose_name = 'Meta Financeira'
        verbose_name_plural = 'Metas Financeiras'
        ordering = ['deadline']

    def __str__(self):
        return self.name

    @property
    def progress_percentage(self):
        if self.target_amount > 0:
            return min(int((self.current_amount / self.target_amount) * 100), 100)
        return 0

    @property
    def remaining_amount(self):
        return max(self.target_amount - self.current_amount, 0)

    @property
    def days_remaining(self):
        from django.utils import timezone
        delta = self.deadline - timezone.now().date()
        return delta.days

    @property
    def months_remaining(self):
        d = self.days_remaining
        return max(round(d / 30), 1) if d > 0 else 0

    @property
    def monthly_needed(self):
        """How much per month is needed to reach the goal by the deadline."""
        months = self.months_remaining
        if months > 0 and self.remaining_amount > 0:
            return self.remaining_amount / months
        return 0

    @property
    def status(self):
        """'done', 'on_track', 'warning', 'overdue'"""
        if self.progress_percentage >= 100:
            return 'done'
        if self.days_remaining < 0:
            return 'overdue'
        if self.days_remaining <= 30:
            return 'warning'
        return 'on_track'


class BankAccount(models.Model):
    ACCOUNT_TYPES = [
        ('CORRENTE', 'Conta Corrente'),
        ('POUPANCA', 'Poupança'),
        ('INVESTIMENTO', 'Investimento'),
        ('CARTEIRA', 'Carteira'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bank_accounts')
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default='CORRENTE')
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    bank_name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Conta Bancária'
        verbose_name_plural = 'Contas Bancárias'

    def __str__(self):
        return f"{self.name} ({self.get_account_type_display()})"


class Transfer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transfers')
    from_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='transfers_out')
    to_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='transfers_in')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    date = models.DateField(default=timezone.now)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Transferência'
        verbose_name_plural = 'Transferências'
        ordering = ['-date']

    def __str__(self):
        return f"{self.from_account} → {self.to_account}: R$ {self.amount}"


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Criação'),
        ('UPDATE', 'Atualização'),
        ('DELETE', 'Exclusão'),
        ('LOGIN', 'Login'),
        ('IMPORT', 'Importação'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=50, blank=True)
    object_id = models.IntegerField(null=True, blank=True)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Log de Auditoria'
        verbose_name_plural = 'Logs de Auditoria'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user} — {self.action} — {self.timestamp:%Y-%m-%d %H:%M}"


class Loan(models.Model):
    LOAN_TYPES = [
        ('REDUCAO_SALDO', 'Juros sobre Saldo Devedor'),
        ('PRICE', 'Tabela Price (Parcela Fixa)'),
        ('SAC', 'SAC (Amortização Constante)'),
        ('SIMPLES', 'Juros Simples (Pré-fixado)'),
    ]
    INTEREST_PERIOD = [
        ('MENSAL', 'Mensal (% a.m.)'),
        ('ANUAL', 'Anual (% a.a.)'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loans')
    name = models.CharField(max_length=150, verbose_name='Descrição')
    lender = models.CharField(max_length=100, verbose_name='Credor/Instituição')
    loan_type = models.CharField(max_length=20, choices=LOAN_TYPES, default='REDUCAO_SALDO', verbose_name='Modalidade')
    principal = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Valor Original')
    interest_rate = models.DecimalField(max_digits=7, decimal_places=4, verbose_name='Taxa de Juros (%)')
    interest_period = models.CharField(max_length=10, choices=INTEREST_PERIOD, default='MENSAL', verbose_name='Período da Taxa')
    start_date = models.DateField(verbose_name='Data do Empréstimo')
    due_day = models.IntegerField(default=10, verbose_name='Dia de Vencimento')
    num_installments = models.IntegerField(null=True, blank=True, verbose_name='Número de Parcelas', help_text='Obrigatório para Price e SAC. Deixe vazio para Saldo Devedor/Simples.')
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Saldo Devedor Atual')
    iof_rate = models.DecimalField(
        max_digits=7, decimal_places=4, default=0, blank=True,
        verbose_name='IOF (%)',
        help_text='Percentual do IOF sobre o principal. Ex: 3.0 para 3%. Deixe 0 para empréstimos sem IOF.'
    )
    insurance_monthly = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, blank=True,
        verbose_name='Seguro Mensal (R$)',
        help_text='Seguro prestamista mensal fixo. Deixe 0 se não houver.'
    )
    notes = models.TextField(blank=True, verbose_name='Observações')
    is_active = models.BooleanField(default=True, verbose_name='Ativo')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Empréstimo'
        verbose_name_plural = 'Empréstimos'
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.name} — R$ {self.current_balance:.2f}"

    @property
    def monthly_rate(self):
        rate = float(self.interest_rate) / 100
        if self.interest_period == 'ANUAL':
            rate = (1 + rate) ** (1 / 12) - 1
        return rate

    @property
    def next_interest(self):
        return round(float(self.current_balance) * self.monthly_rate, 2)

    @property
    def min_next_payment(self):
        """Minimum payment to at least cover interest (so debt doesn't grow)."""
        return self.next_interest

    def save(self, *args, **kwargs):
        if not self.pk:
            if not self.current_balance:
                self.current_balance = self.principal
        super().save(*args, **kwargs)


class LoanDisbursement(models.Model):
    """Tracks additional draws on an existing loan (e.g. borrowing more from same lender)."""
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='disbursements')
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Valor Adicional (R$)')
    date = models.DateField(default=timezone.now, verbose_name='Data')
    note = models.CharField(max_length=255, blank=True, verbose_name='Observação')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Desembolso Adicional'
        ordering = ['-date']

    def __str__(self):
        return f"+R$ {self.amount} em {self.date}"


class LoanPayment(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='payments')
    payment_date = models.DateField(default=timezone.now, verbose_name='Data do Pagamento')
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Valor Pago')
    interest_paid = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Juros')
    principal_paid = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Amortização')
    balance_after = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Saldo Após')
    notes = models.CharField(max_length=255, blank=True, verbose_name='Observações')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Pagamento de Empréstimo'
        verbose_name_plural = 'Pagamentos de Empréstimo'
        ordering = ['-payment_date']

    def __str__(self):
        return f"Pagamento R$ {self.amount_paid} em {self.payment_date}"
