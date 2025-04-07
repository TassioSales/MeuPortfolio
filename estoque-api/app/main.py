from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import products
from . import models
from .database import engine, init_db

# Cria a aplicação FastAPI
app = FastAPI(
    title="Sistema de Estoque API",
    description="API para gerenciamento de estoque",
    version="1.0.0"
)

# Configura o CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializa o banco de dados
init_db()

# Inclui os routers
app.include_router(products.router)

@app.get("/")
async def root():
    """Rota raiz da API"""
    return {
        "message": "Sistema de Estoque API",
        "version": "1.0.0",
        "status": "online"
    }
