from django.core.management.base import BaseCommand
from core.models import Transaction, RecurringTransaction, Budget, Investment, Goal, Category
from django.db import transaction

class Command(BaseCommand):
    help = 'Limpa todos os dados da aplicação exceto Categorias e Usuários.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Iniciando limpeza de dados...'))

        with transaction.atomic():
            # Apagar na ordem correta para evitar erros de Integridade (embora CASCADE ajude)
            
            # 1. Investimentos (tem link com Transação)
            count_investments = Investment.objects.count()
            Investment.objects.all().delete()
            self.stdout.write(f'Investimentos removidos: {count_investments}')

            # 2. Transações e Recorrentes
            count_trans = Transaction.objects.count()
            Transaction.objects.all().delete()
            self.stdout.write(f'Transações removidas: {count_trans}')

            count_recur = RecurringTransaction.objects.count()
            RecurringTransaction.objects.all().delete()
            self.stdout.write(f'Transações Recorrentes removidas: {count_recur}')

            # 3. Orçamentos e Metas
            count_budgets = Budget.objects.count()
            Budget.objects.all().delete()
            self.stdout.write(f'Orçamentos removidos: {count_budgets}')

            count_goals = Goal.objects.count()
            Goal.objects.all().delete()
            self.stdout.write(f'Metas removidas: {count_goals}')

            # Conferir Categorias
            count_cats = Category.objects.count()
            self.stdout.write(self.style.SUCCESS(f'Concluído! Categorias preservadas: {count_cats}'))
