# Generated manually

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_bankaccount_transfer_auditlog_transaction_account_budget_rollover'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Loan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, verbose_name='Descrição')),
                ('lender', models.CharField(max_length=100, verbose_name='Credor/Instituição')),
                ('loan_type', models.CharField(
                    choices=[
                        ('REDUCAO_SALDO', 'Juros sobre Saldo Devedor'),
                        ('PRICE', 'Tabela Price (Parcela Fixa)'),
                        ('SAC', 'SAC (Amortização Constante)'),
                        ('SIMPLES', 'Juros Simples (Pré-fixado)'),
                    ],
                    default='REDUCAO_SALDO',
                    max_length=20,
                    verbose_name='Modalidade',
                )),
                ('principal', models.DecimalField(decimal_places=2, max_digits=15, verbose_name='Valor Original')),
                ('interest_rate', models.DecimalField(decimal_places=4, max_digits=7, verbose_name='Taxa de Juros (%)')),
                ('interest_period', models.CharField(
                    choices=[
                        ('MENSAL', 'Mensal (% a.m.)'),
                        ('ANUAL', 'Anual (% a.a.)'),
                    ],
                    default='MENSAL',
                    max_length=10,
                    verbose_name='Período da Taxa',
                )),
                ('start_date', models.DateField(verbose_name='Data do Empréstimo')),
                ('due_day', models.IntegerField(default=10, verbose_name='Dia de Vencimento')),
                ('num_installments', models.IntegerField(
                    blank=True,
                    help_text='Obrigatório para Price e SAC. Deixe vazio para Saldo Devedor/Simples.',
                    null=True,
                    verbose_name='Número de Parcelas',
                )),
                ('current_balance', models.DecimalField(decimal_places=2, max_digits=15, verbose_name='Saldo Devedor Atual')),
                ('notes', models.TextField(blank=True, verbose_name='Observações')),
                ('is_active', models.BooleanField(default=True, verbose_name='Ativo')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='loans', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Empréstimo',
                'verbose_name_plural': 'Empréstimos',
                'ordering': ['-start_date'],
            },
        ),
        migrations.CreateModel(
            name='LoanPayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payment_date', models.DateField(default=django.utils.timezone.now, verbose_name='Data do Pagamento')),
                ('amount_paid', models.DecimalField(decimal_places=2, max_digits=15, verbose_name='Valor Pago')),
                ('interest_paid', models.DecimalField(decimal_places=2, max_digits=15, verbose_name='Juros')),
                ('principal_paid', models.DecimalField(decimal_places=2, max_digits=15, verbose_name='Amortização')),
                ('balance_after', models.DecimalField(decimal_places=2, max_digits=15, verbose_name='Saldo Após')),
                ('notes', models.CharField(blank=True, max_length=255, verbose_name='Observações')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('loan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='core.loan')),
            ],
            options={
                'verbose_name': 'Pagamento de Empréstimo',
                'verbose_name_plural': 'Pagamentos de Empréstimo',
                'ordering': ['-payment_date'],
            },
        ),
    ]
