from datetime import datetime

from loguru import logger
from telegram import Update
from telegram.ext import ContextTypes

from bot.database.manager import DatabaseManager
from bot.services.formatters import formatar_gastos


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
            "❌ Uso incorreto. Exemplo:\n`/gasto 25.50 almoço alimentação`\n\n"
            "Formato: `/gasto <valor> <descrição> [categoria]`",
            parse_mode="Markdown",
        )
        return

    # Parse valor
    try:
        valor = float(args[0].replace(",", "."))
        if valor <= 0:
            raise ValueError("Valor deve ser positivo")
    except ValueError:
        await update.message.reply_text(
            f"❌ Valor inválido: `{args[0]}`\nUse um número positivo. Exemplo: `25.50`",
            parse_mode="Markdown",
        )
        return

    # Parse descrição e categoria
    if len(args) >= 3:
        descricao = " ".join(args[1:-1])
        categoria = args[-1].lower()
    else:
        descricao = args[1]
        categoria = "outros"

    try:
        db = _get_db(context)
        novo_id = db.adicionar_gasto(user_id, descricao, valor, categoria)
        logger.info(f"Gasto registrado: id={novo_id}, user={user_id}, valor={valor}, desc={descricao}")

        await update.message.reply_text(
            f"✅ *Gasto registrado!*\n\n"
            f"💰 Valor: R$ {valor:.2f}\n"
            f"📝 Descrição: {descricao}\n"
            f"🏷️ Categoria: {categoria}\n"
            f"🆔 ID: #{novo_id}",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Erro ao registrar gasto para user={user_id}: {e}")
        await update.message.reply_text(
            "❌ Erro ao registrar o gasto. Tente novamente mais tarde."
        )


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
        await update.message.reply_text(texto, parse_mode="Markdown")
        logger.info(f"Gastos listados para user={user_id}, mês={mes_atual}, total={total}")
    except Exception as e:
        logger.error(f"Erro ao listar gastos para user={user_id}: {e}")
        await update.message.reply_text(
            "❌ Erro ao buscar os gastos. Tente novamente mais tarde."
        )


async def gastos_mes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /gastos_mes <YYYY-MM> — list expenses for a specific month."""
    if update.message is None or update.effective_user is None:
        return

    user_id = update.effective_user.id
    args = context.args or []

    if not args:
        await update.message.reply_text(
            "❌ Informe o mês. Exemplo:\n`/gastos_mes 2025-01`",
            parse_mode="Markdown",
        )
        return

    mes = args[0].strip()

    # Validate format YYYY-MM
    try:
        datetime.strptime(mes, "%Y-%m")
    except ValueError:
        await update.message.reply_text(
            f"❌ Formato de mês inválido: `{mes}`\nUse o formato `AAAA-MM`. Exemplo: `2025-01`",
            parse_mode="Markdown",
        )
        return

    try:
        db = _get_db(context)
        gastos = db.listar_gastos(user_id, mes=mes)
        total = db.total_gastos(user_id, mes=mes)

        texto = formatar_gastos(gastos, total, mes)
        await update.message.reply_text(texto, parse_mode="Markdown")
        logger.info(f"Gastos do mês {mes} listados para user={user_id}")
    except Exception as e:
        logger.error(f"Erro ao listar gastos do mês {mes} para user={user_id}: {e}")
        await update.message.reply_text(
            "❌ Erro ao buscar os gastos. Tente novamente mais tarde."
        )
