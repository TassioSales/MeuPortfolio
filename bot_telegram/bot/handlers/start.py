from telegram import Update
from telegram.ext import ContextTypes
from loguru import logger


WELCOME_MESSAGE = (
    "👋 Olá, {nome}! Bem-vindo ao *SistemaFinancasProBot*!\n\n"
    "Controle gastos, guarde notas e obtenha insights com IA.\n"
    "Pode mandar qualquer mensagem — a IA responde! 💬\n\n"
    "📋 *Comandos principais:*\n\n"
    "💸 *Gastos*\n"
    "• /gasto — Registrar um gasto\n"
    "• /gastos — Ver gastos do mês atual\n"
    "• /categorias — Gastos por categoria\n"
    "• /exportar — Baixar CSV e Excel\n\n"
    "🎯 *Meta* — /meta\n\n"
    "📝 *Notas* — /nota, /notas\n\n"
    "🤖 *IA* — /perguntar, /resumo\n\n"
    "❓ Use /help para ver todos os comandos e exemplos."
)

HELP_MESSAGE = (
    "📖 *Ajuda Detalhada*\n\n"
    "━━━━━━━━━━━━━━━━━━\n"
    "💸 *GASTOS*\n"
    "━━━━━━━━━━━━━━━━━━\n\n"
    "`/gasto <valor> <descrição> [categoria]`\n"
    "• `/gasto 25.50 almoço alimentação`\n"
    "• `/gasto 150 conta de luz conta`\n"
    "• `/gasto 9.90 netflix assinatura`\n\n"
    "`/gastos` — gastos do mês atual\n"
    "`/gastos_mes janeiro` — ou: mês passado, 2025-03\n"
    "`/apagar_gasto 5` — remove o gasto \\#5\n"
    "`/categorias` — breakdown por categoria\n"
    "`/exportar` — envia CSV + Excel no chat\n\n"
    "━━━━━━━━━━━━━━━━━━\n"
    "🎯 *META MENSAL*\n"
    "━━━━━━━━━━━━━━━━━━\n\n"
    "`/meta 2000` — define orçamento de R$ 2.000/mês\n"
    "`/meta` — ver status atual vs meta\n\n"
    "━━━━━━━━━━━━━━━━━━\n"
    "📝 *NOTAS*\n"
    "━━━━━━━━━━━━━━━━━━\n\n"
    "`/nota Comprar leite amanhã`\n"
    "`/notas` — lista com IDs\n"
    "`/apagar_nota 3` — pede confirmação antes de apagar\n\n"
    "━━━━━━━━━━━━━━━━━━\n"
    "🤖 *INTELIGÊNCIA ARTIFICIAL*\n"
    "━━━━━━━━━━━━━━━━━━\n\n"
    "`/perguntar Qual foi meu maior gasto?`\n"
    "`/resumo` — análise completa com meta e sugestões\n"
    "Texto livre — qualquer mensagem sem / vai para a IA"
)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    if update.effective_user is None or update.message is None:
        return

    nome = update.effective_user.first_name or "usuário"
    logger.info(f"Usuário {update.effective_user.id} ({nome}) iniciou o bot")

    try:
        await update.message.reply_text(
            WELCOME_MESSAGE.format(nome=nome),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Erro no /start: {e}")
        await update.message.reply_text(
            f"Olá, {nome}! Bot iniciado com sucesso! Use /help para ver os comandos."
        )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    if update.message is None:
        return

    logger.info(f"Usuário {update.effective_user.id if update.effective_user else '?'} usou /help")

    try:
        await update.message.reply_text(HELP_MESSAGE, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Erro no /help: {e}")
        await update.message.reply_text(
            "Erro ao exibir a ajuda. Tente novamente mais tarde."
        )
