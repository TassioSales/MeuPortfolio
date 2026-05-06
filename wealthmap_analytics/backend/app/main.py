from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from contextlib import asynccontextmanager

from app.db.session import engine
from app.models import models
from app.api.v1.endpoints import assets, transactions, portfolio, analytics, ai
from app.services import websocket_service
from app.core.exceptions import global_exception_handler, http_exception_handler
from app.core.logger import setup_logging
from fastapi import HTTPException

# Initialize logging
setup_logging()

# Create tables
models.Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background tasks
    ticker_task = asyncio.create_task(websocket_service.market_ticker_generator())
    yield
    # Cleanup
    ticker_task.cancel()

app = FastAPI(
    title="WealthMap Analytics Enterprise API",
    description="Professional-grade investment analytics platform",
    version="2.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(assets.router, prefix="/assets", tags=["Assets"])
app.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
app.include_router(portfolio.router, prefix="/portfolio", tags=["Portfolio"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
app.include_router(ai.router, prefix="/ai", tags=["AI & Real-time"])

# Exception Handlers
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)

@app.get("/")
def read_root():
    return {
        "message": "Welcome to WealthMap Analytics Enterprise API",
        "status": "online",
        "version": "2.0.0"
    }
