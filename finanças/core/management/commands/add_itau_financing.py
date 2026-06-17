"""
Management command: adiciona o financiamento imobiliário Itaú (Júlia) no banco de dados.

Dados extraídos do PDF "SIMULAÇÃO ITAÚ JULIA" de 20/04/2026:
  - Valor do imóvel : R$ 255.000,00
  - Valor financiado: R$ 204.000,00
  - Tipo            : SAC (Amortização Constante)
  - Prazo           : 420 meses (35 anos)
  - Taxa efetiva    : 13,45% a.a.
  - Seguro MIP+DFI  : ~R$ 40,00/mês (média dos primeiros meses)
  - CET             : 13,80% a.a.
  - Parcela inicial : R$ 2.677,45 (juros + amort. R$ 485,71 + seguro)

Uso:
    python manage.py add_itau_financing --user <username>
    python manage.py add_itau_financing --user <username> --dry-run
"""
import datetime
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from core.models import Loan


class Command(BaseCommand):
    help = "Insere o financiamento imobiliário Itaú (simulação Julia) para o usuário indicado."

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            required=True,
            help="Username do proprietário do financiamento",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra o que seria criado sem salvar no banco",
        )

    def handle(self, *args, **options):
        username = options["user"]
        dry_run = options["dry_run"]

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"Usuário '{username}' não encontrado.")

        # ── Dados do financiamento ────────────────────────────────────────────
        data = {
            "user": user,
            "name": "Financiamento Imobiliário Itaú",
            "lender": "Itaú Imóveis",
            "loan_type": "SAC",             # Sistema de Amortização Constante
            "principal": 204_000.00,         # Valor financiado
            "current_balance": 204_000.00,   # Ainda não começou
            "interest_rate": 13.45,          # 13,45% a.a. efetiva
            "interest_period": "ANUAL",
            "num_installments": 420,         # 35 anos × 12
            "start_date": datetime.date(2026, 7, 1),   # começa mês que vem
            "due_day": 5,                    # ajuste se souber o dia exato
            "insurance_monthly": 40.00,      # MIP + DFI ≈ R$ 40/mês
            "iof_rate": 0,                   # financiamento imobiliário = sem IOF
            "is_active": True,
            "notes": (
                "Financiamento imobiliário residencial — simulação Itaú 20/04/2026. "
                "Valor do imóvel: R$ 255.000,00. "
                "Taxa fixa 13,45% a.a. — CET 13,80% a.a. "
                "Seguro habitacional (MIP+DFI) embutido na parcela."
            ),
        }

        # ── Sumário ───────────────────────────────────────────────────────────
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("  FINANCIAMENTO A SER CADASTRADO")
        self.stdout.write("=" * 60)
        self.stdout.write(f"  Usuário      : {user.username}")
        self.stdout.write(f"  Nome         : {data['name']}")
        self.stdout.write(f"  Credor       : {data['lender']}")
        self.stdout.write(f"  Modalidade   : {data['loan_type']}")
        self.stdout.write(f"  Principal    : R$ {data['principal']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        self.stdout.write(f"  Taxa         : {data['interest_rate']}% a.a. (efetiva)")
        self.stdout.write(f"  Parcelas     : {data['num_installments']} meses ({data['num_installments']//12} anos)")
        self.stdout.write(f"  Início       : {data['start_date'].strftime('%d/%m/%Y')}")
        self.stdout.write(f"  Seguro/mês   : R$ {data['insurance_monthly']:.2f}")
        self.stdout.write("=" * 60 + "\n")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — nenhum dado foi salvo."))
            return

        # Verifica duplicatas
        if Loan.objects.filter(user=user, name=data["name"]).exists():
            raise CommandError(
                "Já existe um financiamento com esse nome para este usuário. "
                "Use --dry-run para verificar ou renomeie antes de rodar novamente."
            )

        loan = Loan.objects.create(**data)
        self.stdout.write(
            self.style.SUCCESS(
                f"✔ Financiamento cadastrado com sucesso! ID = {loan.pk}\n"
                f"  Acesse em: /loans/{loan.pk}/\n"
            )
        )
