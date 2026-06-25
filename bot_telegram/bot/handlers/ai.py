from datetime import datetime

from loguru import logger
from telegram import Update
from telegram.ext import ContextTypes

from bot.config import MISTRAL_API_KEY
from bot.database.manager import DatabaseManager
from bot.services.ai_service import perguntar
from bot.services.formatters import formatar_meta, nome_mes


def _get_db(context: ContextTypes.DEFAULT_TYPE) -> DatabaseManager:
    return context.bot_data["db"]  # type: ignore[return-value]


def _construir_contexto_gastos(gastos: list[dict], total: float, mes: str) -> str:
    if not gastos:
        return f"O usuário não tem gastos registrados para o mês {mes}."
    linhas = [f"Gastos do mês {mes} (Total: R$ {total:.2f}):"]
    for g in gastos:
        linhas.append(
            f"- #{g['id']} | {g['data']} | R$ {g['valor']:.2f} | {g['descricao']} | categoria: {g['categoria']}"
        )
    return "\n".join(linhas)


def _construir_contexto_notas(notas: list[dict]) -> str:
    if not notas:
        return "O usuário não tem notas salvas."
    linhas = ["Notas do usuário:"]
    for n in notas:
        linhas.append(f"- #{n['id']} | {n['criado_em']} | {n['texto']}")
    return "\n".join(linhas)


async def perguntar_ia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /perguntar <pergunta>."""
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

    await _responder_com_ia(update, context, " ".join(args))


async def chat_livre(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle free-text messages — respond with AI using user data as context."""
    if update.message is None or update.effective_user is None:
        return
    texto = update.message.text or ""
    if not texto.strip():
        return
    await _responder_com_ia(update, context, texto, indicador="💬")


async def _responder_com_ia(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    pergunta: str,
    indicador: str = "🤔",
) -> None:
    user_id = update.effective_user.id  # type: ignore[union-attr]
    mes_atual = datetime.now().strftime("%Y-%m")

    aguarde = await update.message.reply_text(f"{indicador} Consultando a IA...")  # type: ignore[union-attr]

    try:
        db = _get_db(context)
        gastos = db.listar_gastos(user_id, mes=mes_atual)
        total = db.total_gastos(user_id, mes=mes_atual)
        notas = db.listar_notas(user_id)
        meta = db.obter_meta(user_id)

        contexto_meta = (
            f"Meta mensal do usuário: R$ {meta:.2f}" if meta else "Sem meta mensal definida."
        )

        contexto = "\n\n".join([
            _construir_contexto_gastos(gastos, total, mes_atual),
            _construir_contexto_notas(notas),
            contexto_meta,
        ])

        logger.info(f"IA para user={user_id}: {pergunta[:60]}...")
        resposta = await perguntar(pergunta, contexto=contexto, api_key=MISTRAL_API_KEY)

        await aguarde.delete()
        await update.message.reply_text(  # type: ignore[union-attr]
            f"🤖 {resposta}",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Erro IA user={user_id}: {e}")
        await aguarde.delete()
        await update.message.reply_text("❌ Erro ao consultar a IA. Tente novamente.")  # type: ignore[union-attr]


async def resumo_ia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /resumo — AI spending summary with meta awareness."""
    if update.message is None or update.effective_user is None:
        return

    user_id = update.effective_user.id
    mes_atual = datetime.now().strftime("%Y-%m")

    aguarde = await update.message.reply_text("📊 Gerando seu resumo, aguarde...")

    try:
        db = _get_db(context)
        gastos = db.listar_gastos(user_id, mes=mes_atual)
        total = db.total_gastos(user_id, mes=mes_atual)
        notas = db.listar_notas(user_id)
        meta = db.obter_meta(user_id)

        contexto_meta = (
            f"Meta mensal do usuário: R$ {meta:.2f} — gasto atual: R$ {total:.2f} ({total/meta*100:.0f}%)"
            if meta else "Sem meta mensal definida."
        )

        contexto = "\n\n".join([
            _construir_contexto_gastos(gastos, total, mes_atual),
            _construir_contexto_notas(notas),
            contexto_meta,
        ])

        pergunta = (
            f"Com base nos meus dados financeiros do mês {mes_atual}, "
            "gere um resumo detalhado dos meus gastos, identifique padrões de consumo, "
            "aponte as categorias onde gasto mais"
            + (f", compare com minha meta de R$ {meta:.2f}" if meta else "")
            + " e dê sugestões práticas de como economizar. "
            "Seja objetivo e use bullet points quando apropriado."
        )

        logger.info(f"Resumo IA: user={user_id}, mês={mes_atual}")
        resposta = await perguntar(pergunta, contexto=contexto, api_key=MISTRAL_API_KEY)

        await aguarde.delete()

        header = f"📊 *Resumo de {nome_mes(mes_atual)}*"
        if meta:
            header += "\n" + formatar_meta(total, meta, mes_atual)

        await update.message.reply_text(
            f"{header}\n\n{resposta}",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Erro /resumo user={user_id}: {e}")
        await aguarde.delete()
        await update.message.reply_text("❌ Erro ao gerar o resumo. Tente novamente.")
