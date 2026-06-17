from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_loan_loanpayment'),
    ]

    operations = [
        migrations.AddField(
            model_name='loan',
            name='iof_rate',
            field=models.DecimalField(
                blank=True, decimal_places=4, default=0, max_digits=7,
                verbose_name='IOF (%)',
                help_text='Percentual do IOF sobre o principal. Ex: 3.0 para 3%.'
            ),
        ),
        migrations.AddField(
            model_name='loan',
            name='insurance_monthly',
            field=models.DecimalField(
                blank=True, decimal_places=2, default=0, max_digits=10,
                verbose_name='Seguro Mensal (R$)',
                help_text='Seguro prestamista mensal fixo.'
            ),
        ),
        migrations.CreateModel(
            name='LoanDisbursement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Valor Adicional (R$)')),
                ('date', models.DateField(default=django.utils.timezone.now, verbose_name='Data')),
                ('note', models.CharField(blank=True, max_length=255, verbose_name='Observação')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('loan', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='disbursements',
                    to='core.loan'
                )),
            ],
            options={
                'verbose_name': 'Desembolso Adicional',
                'ordering': ['-date'],
            },
        ),
    ]
