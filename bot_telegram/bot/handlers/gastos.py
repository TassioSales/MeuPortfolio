from datetime import datetime

from loguru import logger
from telegram import Update
from telegram.ext import ContextTypes

from bot.database.manager import DatabaseManager
from bot.services.formatters import (
    formatar_categorias,
    formatar_gastos,
    formatar_meta,
    nome_mes,
    parse_mes,
)
from bot.services.export_service import exportar_csv, exportar_xlsx


def _get_db(context: ContextTypes.DEFAULT_TYPE) -> DatabaseManager:
    return context.bot_data["db"]  # type: ignore[return-value]


async def registrar_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /gasto <valor> <descrição> [categoria]."""
    if update.message is None or update.effective_user is None:
        return

    user_id = update.effective_user.id
    args = context.args or []

    if len(args) < 2:
        await update.message.reply_text(
            "❌ Uso incorreto.\n\n"
            "Formato: `/gasto <valor> <descrição> [categoria]`\n\n"
            "*Exemplos:*\n"
            "• `/gasto 25.50 almoço alimentação`\n"
            "• `/gasto 150 conta de luz conta`\n"
            "• `/gasto 9.90 netflix assinatura`",
            parse_mode="Markdown",
        )
        return

    try:
        valor = float(args[0].replace(",", "."))
        if valor <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            f"❌ Valor inválido: `{args[0]}`\nUse um número positivo. Ex: `25.50`",
            parse_mode="Markdown",
        )
        return

    if len(args) >= 3:
        descricao = " ".join(args[1:-1])
        categoria = args[-1].lower()
    else:
        descricao = args[1]
        categoria = "outros"

    try:
        db = _get_db(context)
        novo_id = db.adicionar_gasto(user_id, descricao, valor, categoria)
        mes_atual = datetime.now().strftime("%Y-%m")
        total_mes = db.total_gastos(user_id, mes=mes_atual)
        meta = db.obter_meta(user_id)
        logger.info(f"Gasto: id={novo_id}, user={user_id}, valor={valor}")

        texto = (
            f"✅ *Gasto registrado!*\n\n"
            f"💰 R$ {valor:.2f}\n"
            f"📝 {descricao}\n"
            f"🏷️ {categoria}\n"
            f"🆔 #{novo_id}\n\n"
            f"📊 Total do mês: R$ {total_mes:.2f}"
        )

        if meta:
            pct = total_mes / meta * 100
            if pct >= 80:
                aviso = "⚠️" if pct < 100 else "🚨"
                texto += f"\n{aviso} Meta mensal: R$ {meta:.2f} ({pct:.0f}% utilizado)"

        await update.message.reply_text(texto, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Erro ao registrar gasto user={user_id}: {e}")
        await update.message.reply_text("❌ Erro ao registrar o gasto. Tente novamente.")


async def apagar_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /apagar_gasto <id>."""
    if update.message is None or update.effective_user is None:
        return

    user_id = update.effective_user.id
    args = context.args or []

    if not args:
        await update.message.reply_text(
            "❌ Informe o ID do gasto.\n"
            "Exemplo: `/apagar_gasto 5`\n\n"
            "Use /gastos para ver os IDs.",
            parse_mode="Markdown",
        )
        return

    try:
        gasto_id = int(args[0])
    except ValueError:
        await update.message.reply_text(
            f"❌ ID inválido: `{args[0]}`", parse_mode="Markdown"
        )
        return

    try:
        db = _get_db(context)
        apagado = db.apagar_gasto(user_id, gasto_id)
        if apagado:
            logger.info(f"Gasto {gasto_id} apagado para user={user_id}")
            await update.message.reply_text(f"🗑️ Gasto *#{gasto_id}* removido!", parse_mode="Markdown")
        else:
            await update.message.reply_text(
                f"❌ Gasto *#{gasto_id}* não encontrado.\nUse /gastos para ver seus gastos.",
                parse_mode="Markdown",
            )
    except Exception as e:
        logger.error(f"Erro ao apagar gasto {gasto_id} user={user_id}: {e}")
        await update.message.reply_text("❌ Erro ao apagar o gasto. Tente novamente.")


async def listar_gastos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /gastos — list current month's expenses."""
    if update.message is None or update.effective_user is None:
        return

    user_id = update.effective_user.id
    mes_atual = datetime.now().strftime("%Y-%m")

    try:
        db = _get_db(context)
        gastos = db.listar_gastos(user_id, mes=mes_atual)
        total = db.total_gastos(user_id, mes=mes_atual)
        texto = formatar_gastos(gastos, total, mes_atual)

        meta = db.obter_meta(user_id)
        if meta and gastos:
            texto += "\n\n" + formatar_meta(total, meta, mes_atual)

        await update.message.reply_text(texto, parse_mode="Markdown")
        logger.info(f"Gastos listados: user={user_id}, total={total}")
    except Exception as e:
        logger.error(f"Erro ao listar gastos user={user_id}: {e}")
        await update.message.reply_text("❌ Erro ao buscar os gastos.")


async def gastos_mes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /gastos_mes [mês] — list expenses for a given month (natural language or YYYY-MM)."""
    if update.message is None or update.effective_user is None:
        return

    user_id = update.effective_user.id
    args = context.args or []

    if not args:
        mes = datetime.now().strftime("%Y-%m")
    else:
        entrada = " ".join(args)
        mes = parse_mes(entrada)
        if not mes:
            await update.message.reply_text(
                f"❌ Mês inválido: `{entrada}`\n\n"
                "Use `AAAA-MM`, o nome do mês ou:\n"
                "• `mês passado` · `janeiro` · `2025-03`",
                parse_mode="Markdown",
            )
            return

    try:
        db = _get_db(context)
        gastos = db.listar_gastos(user_id, mes=mes)
        total = db.total_gastos(user_id, mes=mes)
        texto = formatar_gastos(gastos, total, mes)
        await update.message.reply_text(texto, parse_mode="Markdown")
        logger.info(f"Gastos mês {mes}: user={user_id}")
    except Exception as e:
        logger.error(f"Erro ao listar gastos mês {mes} user={user_id}: {e}")
        await update.message.reply_text("❌ Erro ao buscar os gastos.")


async def categorias(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /categorias [mês] — spending breakdown by category."""
    if update.message is None or update.effective_user is None:
        return

    user_id = update.effective_user.id
    args = context.args or []

    if args:
        entrada = " ".join(args)
        mes = parse_mes(entrada)
        if not mes:
            await update.message.reply_text(
                f"❌ Mês inválido: `{entrada}`", parse_mode="Markdown"
            )
            return
    else:
        mes = datetime.now().strftime("%Y-%m")

    try:
        db = _get_db(context)
        cats = db.gastos_por_categoria(user_id, mes=mes)
        total = db.total_gastos(user_id, mes=mes)
        texto = formatar_categorias(cats, total, mes)
        await update.message.reply_text(texto, parse_mode="Markdown")
        logger.info(f"Categorias: user={user_id}, mês={mes}")
    except Exception as e:
        logger.error(f"Erro ao listar categorias user={user_id}: {e}")
        await update.message.reply_text("❌ Erro ao buscar categorias.")


async def exportar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /exportar [mês] — send expenses as CSV and XLSX."""
    if update.message is None or update.effective_user is None:
        return

    user_id = update.effective_user.id
    args = context.args or []

    if args:
        entrada = " ".join(args)
        mes = parse_mes(entrada)
        if not mes:
            await update.message.reply_text(
                f"❌ Mês inválido: `{entrada}`", parse_mode="Markdown"
            )
            return
    else:
        mes = datetime.now().strftime("%Y-%m")

    try:
        db = _get_db(context)
        gastos = db.listar_gastos(user_id, mes=mes)

        if not gastos:
            await update.message.reply_text(
                f"📭 Nenhum gasto encontrado em *{nome_mes(mes)}*.",
                parse_mode="Markdown",
            )
            return

        await update.message.reply_text(
            f"📤 Gerando relatório de *{nome_mes(mes)}* ({len(gastos)} gastos)...",
            parse_mode="Markdown",
        )

        nome_base = f"gastos_{mes.replace('-', '_')}"

        # Send CSV
        csv_bytes = exportar_csv(gastos, mes)
        await update.message.reply_document(
            document=csv_bytes,
            filename=f"{nome_base}.csv",
            caption=f"📄 CSV — {nome_mes(mes)}",
        )

        # Send XLSX
        xlsx_bytes = exportar_xlsx(gastos, mes)
        await update.message.reply_document(
            document=xlsx_bytes,
            filename=f"{nome_base}.xlsx",
            caption=f"📊 Excel — {nome_mes(mes)}",
        )

        logger.info(f"Exportação concluída: user={user_id}, mês={mes}, gastos={len(gastos)}")
    except Exception as e:
        logger.error(f"Erro na exportação user={user_id}: {e}")
        await update.message.reply_text("❌ Erro ao gerar o relatório.")
