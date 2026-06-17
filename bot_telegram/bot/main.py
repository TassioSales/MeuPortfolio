import sys
from loguru import logger
from telegram.ext import Application, CommandHandler

from bot.config import DB_PATH, TELEGRAM_TOKEN
from bot.database.manager import DatabaseManager
from bot.handlers import ai, gastos, notas, start


def _configure_logging() -> None:
    """Configure loguru to log to stderr and a rotating file."""
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}")
    logger.add(
        "data/bot.log",
        rotation="10 MB",
        retention="30 days",
        level="DEBUG",
        encoding="utf-8",
    )


def main() -> None:
    """Entry point: set up the database and start the bot."""
    _configure_logging()

    db = DatabaseManager(db_path=DB_PATH)
    db.setup()

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Make DB available to all handlers via bot_data
    app.bot_data["db"] = db

    # --- Register command handlers ---
    app.add_handler(CommandHandler("start", start.start_handler))
    app.add_handler(CommandHandler("help", start.help_handler))

    # Gastos
    app.add_handler(CommandHandler("gasto", gastos.registrar_gasto))
    app.add_handler(CommandHandler("gastos", gastos.listar_gastos))
    app.add_handler(CommandHandler("gastos_mes", gastos.gastos_mes))

    # Notas
    app.add_handler(CommandHandler("nota", notas.adicionar_nota))
    app.add_handler(CommandHandler("notas", notas.listar_notas))
    app.add_handler(CommandHandler("apagar_nota", notas.apagar_nota))

    # AI
    app.add_handler(CommandHandler("perguntar", ai.perguntar_ia))
    app.add_handler(CommandHandler("resumo", ai.resumo_ia))

    logger.info("Bot iniciado! Pressione Ctrl+C para parar.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
