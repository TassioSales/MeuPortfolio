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
