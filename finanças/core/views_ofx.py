"""OFX / QIF bank statement import view."""
import io
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .models import Category, Transaction


def _parse_ofx(file_bytes: bytes) -> list[dict]:
    """Parse OFX (SGML or XML) and return list of transaction dicts."""
    from ofxparse import OfxParser

    stream = io.BytesIO(file_bytes)
    ofx = OfxParser.parse(stream)
    results = []
    for acct in (ofx.accounts if hasattr(ofx, "accounts") else [ofx.account]):
        for t in acct.statement.transactions:
            amount = Decimal(str(t.amount))
            results.append({
                "date": t.date.date() if hasattr(t.date, "date") else t.date,
                "amount": abs(amount),
                "type": "RECEITA" if amount > 0 else "DESPESA",
                "description": (t.memo or t.payee or "").strip()[:255],
                "id": getattr(t, "id", ""),
            })
    return results


@login_required
def import_ofx(request):
    if request.method == "POST":
        uploaded = request.FILES.get("ofx_file")
        if not uploaded:
            messages.error(request, "Nenhum arquivo enviado.")
            return redirect("import_ofx")

        try:
            raw = uploaded.read()
            transactions_data = _parse_ofx(raw)
        except Exception as e:
            messages.error(request, f"Erro ao ler o arquivo OFX: {e}")
            return redirect("import_ofx")

        # Confirm step: show parsed transactions before saving
        if "confirm" not in request.POST:
            return render(request, "core/import_ofx.html", {
                "preview": transactions_data,
                "raw_name": uploaded.name,
                # Pass raw bytes as session for confirmation
            })

        # Save step
        default_cat, _ = Category.objects.get_or_create(
            user=request.user,
            name="Extrato Importado",
            defaults={"type": "DESPESA"},
        )

        count = 0
        skipped = 0
        for t in transactions_data:
            # Skip duplicates by description + date + amount
            exists = Transaction.objects.filter(
                user=request.user,
                date=t["date"],
                amount=t["amount"],
                description=t["description"],
                type=t["type"],
            ).exists()
            if exists:
                skipped += 1
                continue

            Transaction.objects.create(
                user=request.user,
                date=t["date"],
                amount=t["amount"],
                type=t["type"],
                description=t["description"],
                category=default_cat if t["type"] == "DESPESA" else None,
            )
            count += 1

        msg = f"{count} transação(ões) importada(s) do extrato OFX."
        if skipped:
            msg += f" {skipped} duplicada(s) ignorada(s)."
        messages.success(request, msg)
        return redirect("transaction_list")

    return render(request, "core/import_ofx.html", {"preview": None})
