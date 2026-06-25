import sys
from loguru import logger
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from bot.config import ALLOWED_USERS, DB_PATH, TELEGRAM_TOKEN
from bot.database.manager import DatabaseManager
from bot.handlers import ai, gastos, notas, start
from bot.handlers.meta import definir_meta


def _configure_logging() -> None:
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
    if not ALLOWED_USERS:
        logger.warning("ALLOWED_USERS não configurado — bot aberto para qualquer usuário Telegram.")
        return filters.ALL

    user_ids: list[int] = []
    for entry in ALLOWED_USERS:
        if entry.isdigit():
            user_ids.append(int(entry))
        else:
            logger.warning(f"ALLOWED_USERS: entrada ignorada (não numérica): {entry!r}")

    if not user_ids:
        logger.error("ALLOWED_USERS sem IDs válidos — bot fechado para todos.")
        return filters.User(user_id=[])

    logger.info(f"Bot restrito a {len(user_ids)} usuário(s): {user_ids}")
    return filters.User(user_id=user_ids)


def main() -> None:
    _configure_logging()

    db = DatabaseManager(db_path=DB_PATH)
    db.setup()

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.bot_data["db"] = db

    user_filter = _build_user_filter()

    # Sistema / ajuda
    app.add_handler(CommandHandler("start", start.start_handler, filters=user_filter))
    app.add_handler(CommandHandler("help", start.help_handler, filters=user_filter))

    # Gastos
    app.add_handler(CommandHandler("gasto", gastos.registrar_gasto, filters=user_filter))
    app.add_handler(CommandHandler("gastos", gastos.listar_gastos, filters=user_filter))
    app.add_handler(CommandHandler("gastos_mes", gastos.gastos_mes, filters=user_filter))
    app.add_handler(CommandHandler("apagar_gasto", gastos.apagar_gasto, filters=user_filter))
    app.add_handler(CommandHandler("categorias", gastos.categorias, filters=user_filter))
    app.add_handler(CommandHandler("exportar", gastos.exportar, filters=user_filter))

    # Notas
    app.add_handler(CommandHandler("nota", notas.adicionar_nota, filters=user_filter))
    app.add_handler(CommandHandler("notas", notas.listar_notas, filters=user_filter))
    app.add_handler(CommandHandler("apagar_nota", notas.apagar_nota, filters=user_filter))

    # Confirmação inline (notas)
    app.add_handler(CallbackQueryHandler(notas.confirmar_apagar_nota, pattern=r"^apagar_nota:"))

    # Meta mensal
    app.add_handler(CommandHandler("meta", definir_meta, filters=user_filter))

    # IA
    app.add_handler(CommandHandler("perguntar", ai.perguntar_ia, filters=user_filter))
    app.add_handler(CommandHandler("resumo", ai.resumo_ia, filters=user_filter))

    # Chat livre (texto sem comando → IA) — deve ser o último handler de mensagens
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & user_filter,
            ai.chat_livre,
        )
    )

    logger.info("Bot iniciado! Pressione Ctrl+C para parar.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
