"""Backfill dos campos de fundação (origin, created_at, parcelas, natureza).

Heurística aplicada uma única vez sobre os dados existentes — os fluxos novos
passam a gravar esses campos diretamente.
"""
import datetime
import re
import uuid
from collections import defaultdict

from django.db import migrations
from django.utils import timezone

INSTALLMENT_RE = re.compile(r"^(?P<base>.*?)\s*\((?P<num>\d+)/(?P<total>\d+)\)\s*$")
RECURRING_SUFFIX = "(Recorrente)"


def forwards(apps, schema_editor):
    Transaction = apps.get_model("core", "Transaction")
    Category = apps.get_model("core", "Category")
    Loan = apps.get_model("core", "Loan")
    Investment = apps.get_model("core", "Investment")

    Category.objects.filter(name__iexact="Investimentos").update(nature="INVESTIMENTO")
    Category.objects.filter(name__in=["Pagamento de Empréstimo", "Empréstimos"]).update(nature="DIVIDA")

    # Empréstimos já cadastrados: o dinheiro recebido não é lançado retroativamente.
    Loan.objects.update(register_income=False)

    investment_tx_ids = set(
        Investment.objects.exclude(transaction_id=None).values_list("transaction_id", flat=True)
    )
    tz = timezone.get_current_timezone()
    groups = defaultdict(list)

    for tx in Transaction.objects.select_related("category").order_by("id").iterator():
        # created_at desconhecido para dados antigos: meio-dia da data de
        # competência; a ordem relativa fica garantida pelo desempate por id.
        tx.created_at = datetime.datetime.combine(tx.date, datetime.time(12, 0), tzinfo=tz)
        desc = (tx.description or "").strip()
        cat_name = tx.category.name if tx.category_id else ""

        if tx.id in investment_tx_ids:
            tx.origin = "INVESTIMENTO"
        elif desc.endswith(RECURRING_SUFFIX):
            tx.origin = "RECORRENTE"
            if not desc[: -len(RECURRING_SUFFIX)].strip():
                tx.description = f"{cat_name or 'Lançamento'} {RECURRING_SUFFIX}"
        elif cat_name in ("Pagamento de Empréstimo", "Empréstimos"):
            tx.origin = "EMPRESTIMO"
        else:
            m = INSTALLMENT_RE.match(desc)
            if m and tx.payment_method == "CREDITO":
                tx.origin = "PARCELA"
                tx.installment_number = int(m.group("num"))
                tx.installment_total = int(m.group("total"))
                key = (tx.user_id, m.group("base").strip(), tx.installment_total, tx.category_id)
                groups[key].append(tx)
            else:
                tx.origin = "MANUAL"
        tx.save(update_fields=[
            "created_at", "origin", "description", "installment_number", "installment_total",
        ])

    for txs in groups.values():
        # Mesma compra repetida (ex.: duas compras iguais em 3x) vira grupos
        # separados sempre que o número da parcela recomeça.
        txs.sort(key=lambda t: t.id)
        current = uuid.uuid4()
        seen = set()
        for tx in txs:
            if tx.installment_number in seen:
                current = uuid.uuid4()
                seen = set()
            seen.add(tx.installment_number)
            Transaction.objects.filter(pk=tx.pk).update(installment_group=current)

    # Um único empréstimo por usuário: dá para vincular os pagamentos antigos.
    for loan in Loan.objects.all():
        if Loan.objects.filter(user_id=loan.user_id).count() == 1:
            Transaction.objects.filter(user_id=loan.user_id, origin="EMPRESTIMO", loan=None).update(loan=loan)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0013_foundations_origin_created_nature"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
