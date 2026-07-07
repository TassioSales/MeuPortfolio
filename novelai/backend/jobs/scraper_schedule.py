"""
Celery task para scraping agendado (1x por dia).
"""
from celery import Celery
from loguru import logger
import asyncio

from config import settings

celery_app = Celery(
    "novelai_scraper",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.beat_schedule = {
    "scrape-daily": {
        "task": "jobs.scraper_schedule.scrape_all",
        "schedule": 86400.0,  # 24 horas
    },
}


@celery_app.task(name="jobs.scraper_schedule.scrape_all")
def scrape_all():
    from services.scraper import scrape_canal
    logger.info("Iniciando scraping diário...")
    try:
        asyncio.run(scrape_canal("default"))
        logger.info("Scraping diário concluído")
    except Exception as e:
        logger.error(f"scrape_all error: {e}")
