"""Pipeline entry point — coleta dados e agenda atualizações periódicas."""

from __future__ import annotations

import os
import signal
import time
from datetime import datetime, timezone

from loguru import logger

from . import db
from .collector import collect_bcb, collect_market, collect_regional
from .processor import get_summary_stats, process_and_store

INTERVAL_MINUTES: int = int(os.getenv("COLLECT_INTERVAL_MINUTES", "30"))

_shutdown = False


def _handle_sigterm(signum: int, frame: object) -> None:
    global _shutdown
    logger.info("SIGTERM recebido. Encerrando pipeline graciosamente...")
    _shutdown = True


def _run_pipeline() -> None:
    """Executa um ciclo completo de coleta e armazenamento."""
    start = time.monotonic()
    conn = db.get_conn()
    status = "success"
    message = ""

    try:
        logger.info("Iniciando coleta BCB...")
        bcb_data = collect_bcb()

        logger.info("Iniciando coleta de mercado...")
        market_data = collect_market()

        logger.info("Carregando dados regionais...")
        regional_data = collect_regional()

        logger.info("Processando e armazenando dados...")
        process_and_store(bcb_data, market_data, regional_data)

        summary = get_summary_stats(conn)
        message = str(summary)
        logger.info(f"Pipeline concluído. Resumo: {summary}")

    except Exception as exc:
        status = "error"
        message = str(exc)
        logger.error(f"Erro no pipeline: {exc}")

    finally:
        duration_s = time.monotonic() - start
        try:
            db.log_run(conn, status, message, round(duration_s, 3))
        except Exception as log_exc:
            logger.error(f"Falha ao registrar log de execução: {log_exc}")
        conn.close()
        logger.info(f"Ciclo encerrado em {duration_s:.2f}s com status={status}.")


def main() -> None:
    signal.signal(signal.SIGTERM, _handle_sigterm)

    logger.info(f"Pipeline iniciado. Intervalo: {INTERVAL_MINUTES}min")

    # Primeira execução imediata
    _run_pipeline()

    last_run = datetime.now(timezone.utc)

    while not _shutdown:
        time.sleep(60)
        if _shutdown:
            break
        now = datetime.now(timezone.utc)
        elapsed_minutes = (now - last_run).total_seconds() / 60
        if elapsed_minutes >= INTERVAL_MINUTES:
            logger.info(f"{elapsed_minutes:.1f}min desde última coleta. Executando ciclo...")
            _run_pipeline()
            last_run = datetime.now(timezone.utc)

    logger.info("Pipeline encerrado.")


if __name__ == "__main__":
    main()
