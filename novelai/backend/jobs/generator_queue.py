"""
Celery task para processar a fila de geração de conteúdo IA.
"""
from celery import Celery
from loguru import logger
import asyncio

from config import settings

celery_app = Celery(
    "novelai_generator",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)


@celery_app.task(name="jobs.generator_queue.processar_geracao_task")
def processar_geracao_task(geracao_id: str, params: dict):
    from services.generator import gerar_conteudo
    from models.database import db
    from datetime import datetime

    logger.info(f"Processando geração {geracao_id}")
    try:
        db.table("fila_geracao").update({
            "status": "processando",
            "iniciado_em": datetime.utcnow().isoformat(),
        }).eq("id", geracao_id).execute()

        video_url = asyncio.run(gerar_conteudo(params))

        db.table("fila_geracao").update({
            "status": "concluido",
            "video_url_resultado": video_url,
            "concluido_em": datetime.utcnow().isoformat(),
        }).eq("id", geracao_id).execute()

        logger.info(f"Geração {geracao_id} concluída: {video_url}")
        return {"status": "concluido", "video_url": video_url}
    except Exception as e:
        logger.error(f"processar_geracao_task {geracao_id} error: {e}")
        db.table("fila_geracao").update({
            "status": "erro",
            "erro_mensagem": str(e),
            "concluido_em": datetime.utcnow().isoformat(),
        }).eq("id", geracao_id).execute()
        raise
