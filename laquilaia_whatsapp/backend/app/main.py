from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger
import sys
import os

from app.config import settings
from sqlalchemy import select
from app.db.database import init_db, close_db, AsyncSessionLocal
from app.db.redis_client import redis_client
from app.db.models import Agent, User
from app.services.auth_service import auth_service
from app.ws.manager import connection_manager
from app.routers import (
    agents, alertas, auth, chat, clientes, escritorio, finalizados, funil,
    historico, kanban, metrics, webhook, whatsapp,
)
from app.jobs.metrics_aggregator import MetricsAggregator
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Configure logger
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level=settings.log_level,
)
logger.add(
    "logs/app.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
    level=settings.log_level,
    rotation="500 MB",
    retention="7 days",
)

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle events."""
    logger.info("🚀 Starting L'Aquila AI Backend (FastAPI)")
    logger.info(f"📊 Environment: {'DEBUG' if settings.debug else 'PRODUCTION'}")
    logger.info(f"🤖 LLM Model: {settings.claude_model}")
    logger.info(f"💾 Database: {settings.database_url.split('@')[-1]}")

    try:
        await init_db()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

    # Sem esta chamada o cliente ficava em None e toda operação de cache
    # estourava AttributeError, engolido pelo `except` de cada método: o
    # Redis estava configurado, aparecia no compose e nunca era usado.
    await redis_client.connect()

    # Initialize metrics scheduler
    scheduler = AsyncIOScheduler()
    aggregator = MetricsAggregator()

    try:
        scheduler.add_job(
            aggregator.aggregate_hourly_metrics,
            "interval",
            hours=1,
            id="metrics_hourly",
            misfire_grace_time=600,  # Tolerate up to 10 min delay
        )
        scheduler.add_job(
            aggregator.aggregate_daily_stats,
            "cron",
            hour=0,
            minute=0,  # 00:00 UTC
            id="metrics_daily",
        )
        scheduler.add_job(
            aggregator.cleanup_old_cache,
            "cron",
            hour=2,
            minute=0,  # 02:00 UTC nightly
            id="metrics_cleanup",
        )
        scheduler.start()
        logger.info("✅ Metrics scheduler started (hourly, daily, cleanup jobs)")
    except Exception as e:
        logger.error(f"❌ Failed to start metrics scheduler: {e}")
        raise

    yield

    try:
        scheduler.shutdown()
        logger.info("🛑 Metrics scheduler stopped")
    except Exception as e:
        logger.error(f"⚠️ Error stopping scheduler: {e}")

    logger.info("🛑 Shutting down L'Aquila AI Backend")
    await redis_client.disconnect()
    await close_db()


# Initialize FastAPI app
app = FastAPI(
    title="L'Aquila AI - WhatsApp Clone",
    description="SaaS Platform for AI Agents on WhatsApp",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origens_permitidas,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== HEALTH CHECK ==========

@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    O estado do Redis aparece aqui porque a falta dele não derruba o boot: sem
    este campo, um deploy sem cache — e com o limite de uso valendo por
    processo — passaria por saudável sem nenhum sinal.
    """
    return {
        "status": "ok",
        "service": "laquilaia-backend",
        "version": "0.1.0",
        "redis": "ok" if await redis_client.health_check() else "unavailable",
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "L'Aquila AI - WhatsApp Clone Backend",
        "docs": "/docs",
        "health": "/health",
    }


# ========== INCLUDE ROUTERS ==========

app.include_router(auth.router)
app.include_router(agents.router)
app.include_router(chat.router)
app.include_router(chat.conversations_router)
app.include_router(webhook.router)
app.include_router(kanban.router)
app.include_router(metrics.router)
app.include_router(whatsapp.router)
app.include_router(alertas.router)
app.include_router(clientes.router)
app.include_router(funil.router)
app.include_router(escritorio.router)
app.include_router(historico.router)
app.include_router(finalizados.router)


# ========== WEBSOCKET ENDPOINTS ==========

@app.websocket("/ws/agents/{agent_id}")
async def agent_events(websocket: WebSocket, agent_id: str, token: str = Query(None)):
    """
    Live updates for one agent: lead movements and incoming messages.

    O token vem na query porque o navegador não permite definir cabeçalhos ao
    abrir um WebSocket. A conexão é recusada antes do `accept()` se o token
    faltar, for inválido, se a conta não estiver ativa ou se o agente não
    existir — do contrário o socket seria um caminho paralelo para receber
    dados sem passar pelas checagens que os endpoints REST fazem.

    A conta **desativada** é conferida aqui de propósito: o REST passou a
    conferir isso a cada requisição, e um socket que ficasse aberto depois da
    desativação faria a revogação imediata valer só metade — quem saiu do
    escritório continuaria vendo lead novo chegando em tempo real.
    """
    user_id = auth_service.verify_token(token) if token else None
    if not user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized")
        return

    async with AsyncSessionLocal() as db:
        usuario = (
            await db.execute(select(User).where(User.id == user_id))
        ).scalars().first()
        if usuario is None or usuario.status != "ativo":
            logger.warning(f"⚠️ WebSocket recusado: conta inativa ou removida ({user_id})")
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized"
            )
            return

        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        if result.scalars().first() is None:
            logger.warning(f"⚠️ WebSocket recusado: agente {agent_id} não existe")
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION, reason="Agent not found"
            )
            return

    await connection_manager.connect(agent_id, websocket)
    try:
        while True:
            # O canal é só de saída. Ficamos lendo apenas para detectar a
            # desconexão; o que o cliente mandar é descartado, e não
            # retransmitido como na versão anterior.
            await websocket.receive_text()
    except WebSocketDisconnect:
        connection_manager.disconnect(agent_id, websocket)
    except Exception as e:
        logger.error(f"❌ Erro no WebSocket: {e}")
        connection_manager.disconnect(agent_id, websocket)


# ========== ERROR HANDLING ==========

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"❌ Unhandled exception: {exc}")
    return {
        "detail": "Internal server error",
        "error": str(exc) if settings.debug else "An error occurred",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
