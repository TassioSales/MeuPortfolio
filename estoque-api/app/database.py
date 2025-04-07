from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Obtém o diretório atual do arquivo
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Define o caminho do banco de dados
DATABASE_URL = os.path.join(BASE_DIR, "sql_app.db")
# URL do SQLAlchemy
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DATABASE_URL}"

# Cria o engine do SQLAlchemy
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Cria a sessão
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Cria a classe base para os modelos
Base = declarative_base()

def init_db():
    """Inicializa o banco de dados criando todas as tabelas"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Retorna uma sessão do banco de dados"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
