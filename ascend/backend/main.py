from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from core.database import create_tables
from core.exceptions import global_exception_handler, http_exception_handler
from core.middleware import RequestLoggingMiddleware
from routers import auth, career, coach, simulation, analytics, mentorship, courses


@asynccontextmanager
async def lifespan(app: FastAPI):
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
