from datetime import datetime

from loguru import logger
from telegram import Update
from telegram.ext import ContextTypes

from bot.services.formatters import formatar_meta


async def definir_meta(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /meta <valor> — set monthly budget goal."""
    if update.message is None or update.effective_user is None:
        return

    user_id = update.effective_user.id
    args = context.args or []

    if not args:
        db = context.bot_data["db"]
        meta_atual = db.obter_meta(user_id)
        if meta_atual:
            mes = datetime.now().strftime("%Y-%m")
            total = db.total_gastos(user_id, mes=mes)
            await update.message.reply_text(
                formatar_meta(total, meta_atual, mes) +
                "\n\n_Use /meta <valor> para atualizar._",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                "🎯 *Meta Mensal*\n\n"
                "Nenhuma meta definida.\n\n"
                "Defina com: `/meta 2000` para R$ 2.000/mês",
                parse_mode="Markdown",
            )
        return

    try:
        valor = float(args[0].replace(",", ".").replace("R$", "").replace(".", "").replace(",", ".").strip())
        # Handle values like 2.000 (Brazilian number format for 2000)
        if valor < 1:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            f"❌ Valor inválido: `{args[0]}`\n\nExemplo: `/meta 2000` ou `/meta 1500.50`",
            parse_mode="Markdown",
        )
        return

    try:
        db = context.bot_data["db"]
        db.definir_meta(user_id, valor)
        mes = datetime.now().strftime("%Y-%m")
        total = db.total_gastos(user_id, mes=mes)
        logger.info(f"Meta definida: user={user_id}, valor={valor}")

        await update.message.reply_text(
            f"✅ *Meta mensal definida: R$ {valor:.2f}*\n\n" +
            formatar_meta(total, valor, mes),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Erro ao definir meta user={user_id}: {e}")
        await update.message.reply_text("❌ Erro ao definir a meta.")
