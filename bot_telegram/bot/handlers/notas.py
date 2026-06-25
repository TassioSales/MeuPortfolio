from datetime import datetime

from loguru import logger
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.database.manager import DatabaseManager
from bot.services.formatters import formatar_notas


def _get_db(context: ContextTypes.DEFAULT_TYPE) -> DatabaseManager:
    return context.bot_data["db"]  # type: ignore[return-value]


async def adicionar_nota(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /nota <texto>."""
    if update.message is None or update.effective_user is None:
        return

    user_id = update.effective_user.id
    args = context.args or []

    if not args:
        await update.message.reply_text(
            "❌ Informe o texto da nota.\n\nExemplo: `/nota Comprar leite amanhã`",
            parse_mode="Markdown",
        )
        return

    texto = " ".join(args)
    try:
        db = _get_db(context)
        novo_id = db.adicionar_nota(user_id, texto)
        logger.info(f"Nota adicionada: id={novo_id}, user={user_id}")
        await update.message.reply_text(
            f"📝 *Nota salva!*\n\n🆔 #{novo_id}\n📄 {texto}",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Erro ao adicionar nota user={user_id}: {e}")
        await update.message.reply_text("❌ Erro ao salvar a nota.")


async def listar_notas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /notas."""
    if update.message is None or update.effective_user is None:
        return

    user_id = update.effective_user.id
    try:
        db = _get_db(context)
        notas = db.listar_notas(user_id)
        texto = formatar_notas(notas)
        await update.message.reply_text(texto, parse_mode="Markdown")
        logger.info(f"Notas listadas: user={user_id}, total={len(notas)}")
    except Exception as e:
        logger.error(f"Erro ao listar notas user={user_id}: {e}")
        await update.message.reply_text("❌ Erro ao buscar as notas.")


async def apagar_nota(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /apagar_nota <id> — shows confirmation keyboard."""
    if update.message is None or update.effective_user is None:
        return

    user_id = update.effective_user.id
    args = context.args or []

    if not args:
        await update.message.reply_text(
            "❌ Informe o ID da nota.\nExemplo: `/apagar_nota 3`\n\nUse /notas para ver os IDs.",
            parse_mode="Markdown",
        )
        return

    try:
        nota_id = int(args[0])
    except ValueError:
        await update.message.reply_text(
            f"❌ ID inválido: `{args[0]}`", parse_mode="Markdown"
        )
        return

    try:
        db = _get_db(context)
        nota = db.obter_nota(user_id, nota_id)
        if not nota:
            await update.message.reply_text(
                f"❌ Nota *#{nota_id}* não encontrada.", parse_mode="Markdown"
            )
            return

        texto = nota.get("texto", "")
        preview = texto[:80] + "..." if len(texto) > 80 else texto

        teclado = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🗑️ Sim, apagar", callback_data=f"apagar_nota:{nota_id}"),
                InlineKeyboardButton("❌ Cancelar", callback_data="apagar_nota:cancelar"),
            ]
        ])
        await update.message.reply_text(
            f"⚠️ Deseja apagar a nota *#{nota_id}*?\n\n_{preview}_",
            reply_markup=teclado,
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Erro ao buscar nota {nota_id} user={user_id}: {e}")
        await update.message.reply_text("❌ Erro ao buscar a nota.")


async def confirmar_apagar_nota(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline keyboard callback for note deletion confirmation."""
    query = update.callback_query
    if query is None or query.from_user is None:
        return

    await query.answer()
    user_id = query.from_user.id
    data = query.data or ""

    if data == "apagar_nota:cancelar":
        await query.edit_message_text("❌ Operação cancelada.")
        return

    try:
        _, nota_id_str = data.split(":", 1)
        nota_id = int(nota_id_str)
    except (ValueError, AttributeError):
        await query.edit_message_text("❌ Erro ao processar a operação.")
        return

    try:
        db = context.bot_data["db"]
        apagada = db.apagar_nota(user_id, nota_id)
        if apagada:
            logger.info(f"Nota {nota_id} confirmada e apagada: user={user_id}")
            await query.edit_message_text(f"🗑️ Nota *#{nota_id}* apagada com sucesso!", parse_mode="Markdown")
        else:
            await query.edit_message_text(f"❌ Nota *#{nota_id}* não encontrada.", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Erro ao apagar nota {nota_id} user={user_id}: {e}")
        await query.edit_message_text("❌ Erro ao apagar a nota.")
