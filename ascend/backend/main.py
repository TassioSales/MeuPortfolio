from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from core.config import settings
from core.database import create_tables
from core.exceptions import global_exception_handler, http_exception_handler
from core.limiter import limiter
from core.middleware import RequestLoggingMiddleware
from routers import auth, career, coach, simulation, analytics, mentorship, courses


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.SECRET_KEY == "dev-secret-key-change-in-production":
        logger.critical(
            "SECRET_KEY é o valor padrão inseguro. "
            "Defina uma chave forte no .env antes de ir a produção."
        )
        raise RuntimeError("SECRET_KEY não configurado — startup abortado.")
    await create_tables()
    logger.info("Trilha API iniciada — http://localhost:8000/docs")
    yield
    logger.info("Trilha API encerrada.")


app = FastAPI(
    title="Trilha API",
    description="AI-Powered Career Coach",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)

for router in [auth, career, coach, simulation, analytics, mentorship, courses]:
    app.include_router(router.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"status": "ok", "app": "Trilha API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
