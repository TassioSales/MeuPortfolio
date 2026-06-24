from datetime import datetime, timedelta

CATEGORIA_EMOJI: dict[str, str] = {
    "alimentação": "🍽️", "alimentacao": "🍽️",
    "transporte": "🚗",
    "saúde": "💊", "saude": "💊",
    "lazer": "🎮",
    "assinatura": "📺",
    "conta": "💡",
    "educação": "📚", "educacao": "📚",
    "vestuário": "👕", "vestuario": "👕",
    "moradia": "🏠",
    "outros": "📦",
}

MESES_NOME: dict[str, str] = {
    "01": "Janeiro", "02": "Fevereiro", "03": "Março",
    "04": "Abril", "05": "Maio", "06": "Junho",
    "07": "Julho", "08": "Agosto", "09": "Setembro",
    "10": "Outubro", "11": "Novembro", "12": "Dezembro",
}

MESES_PARSE: dict[str, str] = {
    "janeiro": "01", "fevereiro": "02", "março": "03", "marco": "03",
    "abril": "04", "maio": "05", "junho": "06",
    "julho": "07", "agosto": "08", "setembro": "09",
    "outubro": "10", "novembro": "11", "dezembro": "12",
    "jan": "01", "fev": "02", "mar": "03", "abr": "04",
    "mai": "05", "jun": "06", "jul": "07", "ago": "08",
    "set": "09", "out": "10", "nov": "11", "dez": "12",
}


def emoji_categoria(categoria: str) -> str:
    return CATEGORIA_EMOJI.get(categoria.lower(), "📦")


def nome_mes(mes: str) -> str:
    try:
        ano, num = mes.split("-")
        return f"{MESES_NOME.get(num, num)}/{ano}"
    except ValueError:
        return mes


def parse_mes(texto: str) -> str | None:
    """Parse natural language or YYYY-MM to YYYY-MM. Returns None if unparseable."""
    now = datetime.now()
    t = texto.lower().strip()

    if t in ("atual", "esse", "este", "mês atual", "mes atual", "agora"):
        return now.strftime("%Y-%m")

    if t in ("passado", "anterior", "mês passado", "mes passado", "último", "ultimo"):
        primeiro = now.replace(day=1)
        anterior = primeiro - timedelta(days=1)
        return anterior.strftime("%Y-%m")

    if t in MESES_PARSE:
        return f"{now.year}-{MESES_PARSE[t]}"

    try:
        datetime.strptime(t, "%Y-%m")
        return t
    except ValueError:
        pass

    return None


def barra_progresso(pct: float, tamanho: int = 10) -> str:
    preenchido = round(pct / 100 * tamanho)
    preenchido = max(0, min(tamanho, preenchido))
    return "█" * preenchido + "░" * (tamanho - preenchido)


def formatar_gastos(gastos: list[dict], total: float, mes: str) -> str:
    label = nome_mes(mes)
    if not gastos:
        return (
            f"💸 *Gastos de {label}*\n\n"
            "Nenhum gasto registrado neste mês.\n\n"
            "Use `/gasto <valor> <descrição>` para registrar um gasto."
        )

    linhas = [f"💸 *Gastos de {label}* ({len(gastos)} registro(s))\n"]
    for g in gastos:
        em = emoji_categoria(g.get("categoria", "outros"))
        linhas.append(
            f"{em} *#{g['id']}* `{g.get('data','')}` — R$ {g.get('valor',0):.2f}\n"
            f"    📝 {g.get('descricao','')} _({g.get('categoria','outros')})_"
        )
    linhas.append(f"\n💰 *Total: R$ {total:.2f}*")
    linhas.append("_Use /apagar\\_gasto <id> para remover um gasto._")
    return "\n".join(linhas)


def formatar_categorias(cats: list[dict], total: float, mes: str) -> str:
    label = nome_mes(mes)
    if not cats:
        return f"📊 *Categorias de {label}*\n\nNenhum gasto registrado."

    linhas = [f"📊 *Gastos por Categoria — {label}*\n"]
    for c in cats:
        em = emoji_categoria(c["categoria"])
        pct = (c["total"] / total * 100) if total > 0 else 0
        barra = barra_progresso(pct)
        linhas.append(
            f"{em} *{c['categoria'].capitalize()}*\n"
            f"    `{barra}` {pct:.1f}%\n"
            f"    {c['qtd']}x · R$ {c['total']:.2f}"
        )
    linhas.append(f"\n💰 *Total: R$ {total:.2f}*")
    return "\n".join(linhas)


def formatar_meta(total: float, meta: float, mes: str) -> str:
    label = nome_mes(mes)
    pct = min(total / meta * 100, 100) if meta > 0 else 0
    restante = max(meta - total, 0)
    barra = barra_progresso(pct)

    if pct >= 100:
        status = f"🚨 *Limite estourado!* Excedido em R$ {total - meta:.2f}"
    elif pct >= 80:
        status = f"⚠️ Atenção: restam apenas R$ {restante:.2f}"
    else:
        status = f"✅ Dentro do orçamento — restam R$ {restante:.2f}"

    return (
        f"🎯 *Meta de {label}:* R$ {meta:.2f}\n"
        f"💸 *Gasto:* R$ {total:.2f}\n\n"
        f"`{barra}` {pct:.1f}%\n\n"
        f"{status}"
    )


def formatar_notas(notas: list[dict]) -> str:
    if not notas:
        return (
            "📝 *Suas Notas*\n\n"
            "Nenhuma nota salva.\n\n"
            "Use `/nota <texto>` para criar uma nota."
        )

    linhas = [f"📝 *Suas Notas* ({len(notas)} nota(s))\n"]
    for n in notas:
        try:
            dt = datetime.fromisoformat(n.get("criado_em", ""))
            data_fmt = dt.strftime("%d/%m/%Y %H:%M")
        except (ValueError, TypeError):
            data_fmt = n.get("criado_em", "")

        linhas.append(f"📌 *#{n['id']}* `{data_fmt}`\n    {n.get('texto','')}")

    linhas.append("\n_Use /apagar\\_nota <id> para remover uma nota._")
    return "\n".join(linhas)
