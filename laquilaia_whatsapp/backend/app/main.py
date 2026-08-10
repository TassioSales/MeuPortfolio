from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger
import sys
import os

from app.config import settings
from app.db.database import init_db, close_db
from app.routers import auth, agents, chat, webhook

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

    yield

    logger.info("🛑 Shutting down L'Aquila AI Backend")
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
    allow_origins=[settings.frontend_url, "localhost", "127.0.0.1"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== HEALTH CHECK ==========

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "laquilaia-backend",
        "version": "0.1.0",
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "L'Aquila AI - WhatsApp Clone Backend",
        "docs": "/docs",
        "health": "/health",
    }


# ========== WEBSOCKET CONNECTION MANAGER ==========

class ConnectionManager:
    """Manage WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, connection_id: str, websocket: WebSocket):
        """Register a new WebSocket connection."""
        await websocket.accept()
        if connection_id not in self.active_connections:
            self.active_connections[connection_id] = []
        self.active_connections[connection_id].append(websocket)
        logger.info(f"✅ WebSocket connected: {connection_id}")

    def disconnect(self, connection_id: str, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if connection_id in self.active_connections:
            self.active_connections[connection_id].remove(websocket)
            if not self.active_connections[connection_id]:
                del self.active_connections[connection_id]
        logger.info(f"❌ WebSocket disconnected: {connection_id}")

    async def broadcast(self, connection_id: str, message: dict):
        """Send message to all connections for a given ID."""
        if connection_id in self.active_connections:
            for connection in self.active_connections[connection_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"❌ Error sending WebSocket message: {e}")

    async def broadcast_all(self, message: dict):
        """Send message to all active connections."""
        for connection_id in self.active_connections:
            await self.broadcast(connection_id, message)


connection_manager = ConnectionManager()


# ========== INCLUDE ROUTERS ==========

app.include_router(auth.router)
app.include_router(agents.router)
app.include_router(chat.router)
app.include_router(webhook.router)


# ========== WEBSOCKET ENDPOINTS ==========

@app.websocket("/ws/{conversation_id}")
async def websocket_endpoint(websocket: WebSocket, conversation_id: str):
    """WebSocket endpoint for real-time conversation updates."""
    await connection_manager.connect(conversation_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back for now; will be enhanced with real data flow
            await connection_manager.broadcast(
                conversation_id,
                {"type": "message", "content": data, "conversation_id": conversation_id}
            )
    except WebSocketDisconnect:
        connection_manager.disconnect(conversation_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        connection_manager.disconnect(conversation_id, websocket)




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
