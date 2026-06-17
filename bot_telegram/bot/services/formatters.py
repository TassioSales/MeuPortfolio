from datetime import datetime

# Emoji mapping per category
CATEGORIA_EMOJI: dict[str, str] = {
    "alimentação": "🍽️",
    "alimentacao": "🍽️",
    "transporte": "🚗",
    "saúde": "💊",
    "saude": "💊",
    "lazer": "🎮",
    "assinatura": "📺",
    "conta": "💡",
    "educação": "📚",
    "educacao": "📚",
    "vestuário": "👕",
    "vestuario": "👕",
    "moradia": "🏠",
    "outros": "📦",
}


def _emoji_categoria(categoria: str) -> str:
    return CATEGORIA_EMOJI.get(categoria.lower(), "📦")


def _nome_mes(mes: str) -> str:
    """Convert YYYY-MM to a human-readable Portuguese month name."""
    meses = {
        "01": "Janeiro", "02": "Fevereiro", "03": "Março",
        "04": "Abril", "05": "Maio", "06": "Junho",
        "07": "Julho", "08": "Agosto", "09": "Setembro",
        "10": "Outubro", "11": "Novembro", "12": "Dezembro",
    }
    try:
        ano, num = mes.split("-")
        return f"{meses.get(num, num)}/{ano}"
    except ValueError:
        return mes


def formatar_gastos(gastos: list[dict], total: float, mes: str) -> str:
    """Format an expense list with totals into a Telegram-friendly Markdown string."""
    nome_mes = _nome_mes(mes)

    if not gastos:
        return (
            f"💸 *Gastos de {nome_mes}*\n\n"
            "Nenhum gasto registrado neste mês.\n\n"
            "Use `/gasto <valor> <descrição>` para registrar um gasto."
        )

    linhas = [f"💸 *Gastos de {nome_mes}* ({len(gastos)} registro(s))\n"]

    for g in gastos:
        emoji = _emoji_categoria(g.get("categoria", "outros"))
        valor = g.get("valor", 0.0)
        descricao = g.get("descricao", "")
        categoria = g.get("categoria", "outros")
        data = g.get("data", "")
        gasto_id = g.get("id", "?")
        linhas.append(
            f"{emoji} *#{gasto_id}* `{data}` — R$ {valor:.2f}\n"
            f"    📝 {descricao} _(_{categoria}_)_"
        )

    linhas.append(f"\n💰 *Total: R$ {total:.2f}*")
    return "\n".join(linhas)


def formatar_notas(notas: list[dict]) -> str:
    """Format a notes list into a Telegram-friendly Markdown string."""
    if not notas:
        return (
            "📝 *Suas Notas*\n\n"
            "Nenhuma nota salva.\n\n"
            "Use `/nota <texto>` para criar uma nota."
        )

    linhas = [f"📝 *Suas Notas* ({len(notas)} nota(s))\n"]

    for n in notas:
        nota_id = n.get("id", "?")
        texto = n.get("texto", "")
        criado_em = n.get("criado_em", "")

        # Format datetime nicely if possible
        try:
            dt = datetime.fromisoformat(criado_em)
            data_fmt = dt.strftime("%d/%m/%Y %H:%M")
        except (ValueError, TypeError):
            data_fmt = criado_em

        linhas.append(f"📌 *#{nota_id}* `{data_fmt}`\n    {texto}")

    linhas.append("\n_Use /apagar\\_nota <id> para remover uma nota._")
    return "\n".join(linhas)
