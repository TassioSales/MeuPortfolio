from datetime import datetime

from loguru import logger
from telegram import Update
from telegram.ext import ContextTypes

from bot.config import MISTRAL_API_KEY
from bot.database.manager import DatabaseManager
from bot.services.ai_service import perguntar


def _get_db(context: ContextTypes.DEFAULT_TYPE) -> DatabaseManager:
    return context.bot_data["db"]  # type: ignore[return-value]


def _construir_contexto_gastos(gastos: list[dict], total: float, mes: str) -> str:
    """Build a text context string from the user's expense data."""
    if not gastos:
        return f"O usuário não tem gastos registrados para o mês {mes}."

    linhas = [f"Gastos do mês {mes} (Total: R$ {total:.2f}):"]
    for g in gastos:
        linhas.append(
            f"- #{g['id']} | {g['data']} | R$ {g['valor']:.2f} | {g['descricao']} | categoria: {g['categoria']}"
        )
    return "\n".join(linhas)


def _construir_contexto_notas(notas: list[dict]) -> str:
    """Build a text context string from the user's notes."""
    if not notas:
        return "O usuário não tem notas salvas."

    linhas = ["Notas do usuário:"]
    for n in notas:
        linhas.append(f"- #{n['id']} | {n['criado_em']} | {n['texto']}")
    return "\n".join(linhas)


async def perguntar_ia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /perguntar <pergunta> — ask AI with user data as context."""
    if update.message is None or update.effective_user is None:
        return

    user_id = update.effective_user.id
    args = context.args or []

    if not args:
        await update.message.reply_text(
            "❌ Informe sua pergunta. Exemplo:\n`/perguntar Qual foi meu maior gasto esse mês?`",
            parse_mode="Markdown",
        )
        return

    pergunta = " ".join(args)
    mes_atual = datetime.now().strftime("%Y-%m")

    # Send a "typing" indicator
    await update.message.reply_text("🤔 Consultando a IA, aguarde...")

    try:
        db = _get_db(context)
        gastos = db.listar_gastos(user_id, mes=mes_atual)
        total = db.total_gastos(user_id, mes=mes_atual)
        notas = db.listar_notas(user_id)

        contexto = (
            _construir_contexto_gastos(gastos, total, mes_atual)
            + "\n\n"
            + _construir_contexto_notas(notas)
        )

        logger.info(f"Pergunta para IA de user={user_id}: {pergunta[:60]}...")
        resposta = await perguntar(pergunta, contexto=contexto, api_key=MISTRAL_API_KEY)

        await update.message.reply_text(
            f"🤖 *Resposta da IA:*\n\n{resposta}",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Erro no /perguntar para user={user_id}: {e}")
        await update.message.reply_text(
            "❌ Erro ao consultar a IA. Tente novamente mais tarde."
        )


async def resumo_ia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /resumo — AI generates a spending summary with suggestions."""
    if update.message is None or update.effective_user is None:
        return

    user_id = update.effective_user.id
    mes_atual = datetime.now().strftime("%Y-%m")

    await update.message.reply_text("📊 Gerando seu resumo, aguarde...")

    try:
        db = _get_db(context)
        gastos = db.listar_gastos(user_id, mes=mes_atual)
        total = db.total_gastos(user_id, mes=mes_atual)
        notas = db.listar_notas(user_id)

        contexto = (
            _construir_contexto_gastos(gastos, total, mes_atual)
            + "\n\n"
            + _construir_contexto_notas(notas)
        )

        pergunta = (
            f"Com base nos meus dados financeiros do mês {mes_atual}, "
            "gere um resumo detalhado dos meus gastos, identifique padrões de consumo, "
            "aponte as categorias onde gasto mais, e dê sugestões práticas de como economizar. "
            "Seja objetivo e use bullet points quando apropriado."
        )

        logger.info(f"Resumo IA solicitado por user={user_id}, mês={mes_atual}")
        resposta = await perguntar(pergunta, contexto=contexto, api_key=MISTRAL_API_KEY)

        await update.message.reply_text(
            f"📊 *Resumo do mês {mes_atual}:*\n\n{resposta}",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Erro no /resumo para user={user_id}: {e}")
        await update.message.reply_text(
            "❌ Erro ao gerar o resumo. Tente novamente mais tarde."
        )
