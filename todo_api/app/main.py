from fastapi import FastAPI
from contextlib import asynccontextmanager
from .routers import tasks
from .database import create_table

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    create_table()
    yield
    # Shutdown
    pass

app = FastAPI(title="API de Gerenciamento de Tarefas", lifespan=lifespan)

app.include_router(tasks.router)