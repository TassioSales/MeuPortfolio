from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal

class Account(models.Model):
    ACCOUNT_TYPES = [
        ('BANCARIA', 'Bancária'),
        ('POUPANCA', 'Poupança'),
        ('CREDITO', 'Crédito'),
        ('CASH', 'Dinheiro Vivo'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accounts')
    name = models.CharField(max_length=100)
    type_account = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default='BANCARIA')
    initial_balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    def __str__(self):
        return f"{self.name} ({self.get_type_account_display()})"

    @property
    def current_balance(self):
        # This will be calculated dynamically later based on transactions
        # For now, returning initial balance + transaction sum
        # We will implement the logic in the manager or a method
        return self.initial_balance

class Category(models.Model):
    CATEGORY_TYPES = [
        ('RECEITA', 'Receita'),
        ('DESPESA', 'Despesa'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=CATEGORY_TYPES, default='DESPESA')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')

    class Meta:
        verbose_name_plural = 'Categories'

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('RECEITA', 'Receita'),
        ('DESPESA', 'Despesa'),
        ('TRANSFERENCIA', 'Transferência'),
    ]
    
    FREQUENCY_CHOICES = [
        ('MENSAL', 'Mensal'),
        ('SEMANAL', 'Semanal'),
        ('ANUAL', 'Anual'),
        ('UNICA', 'Única'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    source_account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='outgoing_transactions')
    target_account = models.ForeignKey(Account, on_delete=models.CASCADE, null=True, blank=True, related_name='incoming_transactions')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    type = models.CharField(max_length=15, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    date = models.DateField(default=timezone.now)
    recurring = models.BooleanField(default=False)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='UNICA', blank=True)
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.get_type_display()} - {self.amount} - {self.date}"

class Budget(models.Model):
    PERIOD_CHOICES = [
        ('MENSAL', 'Mensal'),
        ('ANUAL', 'Anual'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budgets')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='budgets')
    limit = models.DecimalField(max_digits=15, decimal_places=2)
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES, default='MENSAL')
    start_date = models.DateField(default=timezone.now)

    def __str__(self):
        return f"Budget for {self.category.name}: {self.limit}"
