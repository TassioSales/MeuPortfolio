from loguru import logger
from telegram import Update
from telegram.ext import ContextTypes

from bot.database.manager import DatabaseManager
from bot.services.formatters import formatar_notas


def _get_db(context: ContextTypes.DEFAULT_TYPE) -> DatabaseManager:
    return context.bot_data["db"]  # type: ignore[return-value]


async def adicionar_nota(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /nota <texto> — save a note."""
    if update.message is None or update.effective_user is None:
        return

    user_id = update.effective_user.id
    args = context.args or []

    if not args:
        await update.message.reply_text(
            "❌ Informe o texto da nota. Exemplo:\n`/nota Comprar leite amanhã`",
            parse_mode="Markdown",
        )
        return

    texto = " ".join(args)

    try:
        db = _get_db(context)
        novo_id = db.adicionar_nota(user_id, texto)
        logger.info(f"Nota adicionada: id={novo_id}, user={user_id}")

        await update.message.reply_text(
            f"📝 *Nota salva!*\n\n"
            f"🆔 ID: #{novo_id}\n"
            f"📄 Texto: {texto}",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Erro ao adicionar nota para user={user_id}: {e}")
        await update.message.reply_text(
            "❌ Erro ao salvar a nota. Tente novamente mais tarde."
        )


async def listar_notas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /notas — list all notes."""
    if update.message is None or update.effective_user is None:
        return

    user_id = update.effective_user.id

    try:
        db = _get_db(context)
        notas = db.listar_notas(user_id)

        texto = formatar_notas(notas)
        await update.message.reply_text(texto, parse_mode="Markdown")
        logger.info(f"Notas listadas para user={user_id}, total={len(notas)}")
    except Exception as e:
        logger.error(f"Erro ao listar notas para user={user_id}: {e}")
        await update.message.reply_text(
            "❌ Erro ao buscar as notas. Tente novamente mais tarde."
        )


async def apagar_nota(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /apagar_nota <id> — delete a note by ID."""
    if update.message is None or update.effective_user is None:
        return

    user_id = update.effective_user.id
    args = context.args or []

    if not args:
        await update.message.reply_text(
            "❌ Informe o ID da nota. Exemplo:\n`/apagar_nota 3`\n\n"
            "Use /notas para ver os IDs.",
            parse_mode="Markdown",
        )
        return

    try:
        nota_id = int(args[0])
    except ValueError:
        await update.message.reply_text(
            f"❌ ID inválido: `{args[0]}`\nUse um número inteiro. Exemplo: `/apagar_nota 3`",
            parse_mode="Markdown",
        )
        return

    try:
        db = _get_db(context)
        apagada = db.apagar_nota(user_id, nota_id)

        if apagada:
            logger.info(f"Nota {nota_id} apagada para user={user_id}")
            await update.message.reply_text(
                f"🗑️ Nota *#{nota_id}* apagada com sucesso!",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                f"❌ Nota *#{nota_id}* não encontrada.\nUse /notas para ver suas notas.",
                parse_mode="Markdown",
            )
    except Exception as e:
        logger.error(f"Erro ao apagar nota {nota_id} para user={user_id}: {e}")
        await update.message.reply_text(
            "❌ Erro ao apagar a nota. Tente novamente mais tarde."
        )
