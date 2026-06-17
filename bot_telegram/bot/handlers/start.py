from telegram import Update
from telegram.ext import ContextTypes
from loguru import logger


WELCOME_MESSAGE = """👋 Olá, {nome}! Bem-vindo ao seu *Assistente Pessoal*!

Sou um bot para te ajudar a controlar gastos, guardar notas e obter insights com IA.

📋 *Comandos disponíveis:*

💸 *Gastos*
• /gasto — Registrar um gasto
• /gastos — Ver gastos do mês atual
• /gastos\_mes — Ver gastos de um mês específico

📝 *Notas*
• /nota — Salvar uma nota
• /notas — Ver todas as notas
• /apagar\_nota — Apagar uma nota

🤖 *Inteligência Artificial*
• /perguntar — Fazer uma pergunta com contexto dos seus dados
• /resumo — Resumo de gastos com sugestões da IA

❓ Use /help para ver exemplos detalhados de cada comando."""

HELP_MESSAGE = """📖 *Ajuda Detalhada*

━━━━━━━━━━━━━━━━━━
💸 *GASTOS*
━━━━━━━━━━━━━━━━━━

`/gasto <valor> <descrição> [categoria]`
Registra um gasto. A categoria é opcional (padrão: outros).

*Exemplos:*
• `/gasto 25.50 almoço alimentação`
• `/gasto 150 conta de luz conta`
• `/gasto 9.90 netflix assinatura`

━━━━━━━━━━━━━━━━━━
`/gastos`
Lista todos os gastos do mês atual com total.

━━━━━━━━━━━━━━━━━━
`/gastos_mes <AAAA-MM>`
Lista gastos de um mês específico.

*Exemplo:*
• `/gastos_mes 2025-01`

━━━━━━━━━━━━━━━━━━
📝 *NOTAS*
━━━━━━━━━━━━━━━━━━

`/nota <texto>`
Salva uma nota.

*Exemplos:*
• `/nota Comprar leite amanhã`
• `/nota Ligar para o médico na segunda`

━━━━━━━━━━━━━━━━━━
`/notas`
Lista todas as suas notas com IDs.

━━━━━━━━━━━━━━━━━━
`/apagar_nota <id>`
Apaga uma nota pelo ID (use /notas para ver os IDs).

*Exemplo:*
• `/apagar_nota 3`

━━━━━━━━━━━━━━━━━━
🤖 *INTELIGÊNCIA ARTIFICIAL*
━━━━━━━━━━━━━━━━━━

`/perguntar <pergunta>`
Faz uma pergunta à IA com contexto dos seus gastos e notas.

*Exemplos:*
• `/perguntar Qual foi meu maior gasto esse mês?`
• `/perguntar Em que categoria gasto mais?`

━━━━━━━━━━━━━━━━━━
`/resumo`
A IA analisa seus gastos do mês e gera um resumo com sugestões de economia."""


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
