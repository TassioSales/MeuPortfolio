import sys
from loguru import logger
from telegram.ext import Application, CommandHandler, filters

from bot.config import ALLOWED_USERS, DB_PATH, TELEGRAM_TOKEN
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


def _build_user_filter() -> filters.BaseFilter:
    """Return a filter that restricts commands to ALLOWED_USERS.

    If ALLOWED_USERS is empty the bot is open to everyone.
    Only numeric entries (Telegram user IDs) are accepted — non-numeric
    entries are logged and ignored.
    """
    if not ALLOWED_USERS:
        logger.warning(
            "ALLOWED_USERS não configurado — bot aberto para qualquer usuário Telegram."
        )
        return filters.ALL

    user_ids: list[int] = []
    for entry in ALLOWED_USERS:
        if entry.isdigit():
            user_ids.append(int(entry))
        else:
            logger.warning(f"ALLOWED_USERS: entrada ignorada (não é um ID numérico): {entry!r}")

    if not user_ids:
        logger.error("ALLOWED_USERS definido mas sem IDs válidos — bot ficará fechado para todos.")
        return filters.User(user_id=[])

    logger.info(f"Bot restrito a {len(user_ids)} usuário(s): {user_ids}")
    return filters.User(user_id=user_ids)


def main() -> None:
    """Entry point: set up the database and start the bot."""
    _configure_logging()

    db = DatabaseManager(db_path=DB_PATH)
    db.setup()

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Make DB available to all handlers via bot_data
    app.bot_data["db"] = db

    user_filter = _build_user_filter()

    # --- Register command handlers ---
    app.add_handler(CommandHandler("start", start.start_handler, filters=user_filter))
    app.add_handler(CommandHandler("help", start.help_handler, filters=user_filter))

    # Gastos
    app.add_handler(CommandHandler("gasto", gastos.registrar_gasto, filters=user_filter))
    app.add_handler(CommandHandler("gastos", gastos.listar_gastos, filters=user_filter))
    app.add_handler(CommandHandler("gastos_mes", gastos.gastos_mes, filters=user_filter))

    # Notas
    app.add_handler(CommandHandler("nota", notas.adicionar_nota, filters=user_filter))
    app.add_handler(CommandHandler("notas", notas.listar_notas, filters=user_filter))
    app.add_handler(CommandHandler("apagar_nota", notas.apagar_nota, filters=user_filter))

    # AI
    app.add_handler(CommandHandler("perguntar", ai.perguntar_ia, filters=user_filter))
    app.add_handler(CommandHandler("resumo", ai.resumo_ia, filters=user_filter))

    logger.info("Bot iniciado! Pressione Ctrl+C para parar.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
