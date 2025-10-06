"""
Modelos de Dados para PriceTrack AI
Usando SQLAlchemy ORM com validação Pydantic
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional
from datetime import datetime
import json


# Base SQLAlchemy
Base = declarative_base()


class Product(Base):
    """Modelo de Produto no banco de dados"""
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String(255), unique=True, nullable=False, index=True)
    tags = Column(String(500), nullable=True)  # Tags separadas por vírgula
    price_history = Column(JSON, nullable=True)  # Lista de dicts {date: str, price: float}
    alert_threshold = Column(Float, nullable=True, default=0.0)
    user_rating = Column(Integer, nullable=True)  # Rating manual 1-5
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.product_name}')>"


class Alert(Base):
    """Modelo de Alerta para notificações"""
    __tablename__ = 'alerts'
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, nullable=False, index=True)
    threshold_price = Column(Float, nullable=False)
    is_active = Column(Integer, default=1)  # 1 = ativo, 0 = inativo
    created_at = Column(DateTime, default=datetime.utcnow)
    triggered_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<Alert(id={self.id}, product_id={self.product_id}, threshold={self.threshold_price})>"


# Modelos Pydantic para validação
class ProductCreate(BaseModel):
    """Modelo para criação de produto"""
    product_name: str = Field(..., min_length=1, max_length=255)
    tags: Optional[str] = Field(None, max_length=500)
    alert_threshold: Optional[float] = Field(0.0, ge=0)
    user_rating: Optional[int] = Field(None, ge=1, le=5)
    
    @field_validator('product_name')
    @classmethod
    def validate_product_name(cls, v):
        if not v.strip():
            raise ValueError('Nome do produto não pode estar vazio')
        return v.strip()
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        if v:
            # Limitar número de tags
            tags_list = [tag.strip() for tag in v.split(',') if tag.strip()]
            if len(tags_list) > 10:
                raise ValueError('Máximo de 10 tags permitidas')
            return ', '.join(tags_list)
        return v


class ProductUpdate(BaseModel):
    """Modelo para atualização de produto"""
    product_name: Optional[str] = Field(None, min_length=1, max_length=255)
    tags: Optional[str] = Field(None, max_length=500)
    alert_threshold: Optional[float] = Field(None, ge=0)
    user_rating: Optional[int] = Field(None, ge=1, le=5)
    
    @field_validator('product_name')
    @classmethod
    def validate_product_name(cls, v):
        if v and not v.strip():
            raise ValueError('Nome do produto não pode estar vazio')
        return v.strip() if v else v


class PriceHistoryEntry(BaseModel):
    """Modelo para entrada de histórico de preços"""
    date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$')
    price: float = Field(..., gt=0)
    
    @field_validator('date')
    @classmethod
    def validate_date(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Data deve estar no formato YYYY-MM-DD')


class ProductResponse(BaseModel):
    """Modelo para resposta de produto"""
    id: int
    product_name: str
    tags: Optional[str]
    price_history: Optional[List[Dict]]
    alert_threshold: Optional[float]
    user_rating: Optional[int]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AlertCreate(BaseModel):
    """Modelo para criação de alerta"""
    product_id: int = Field(..., gt=0)
    threshold_price: float = Field(..., gt=0)
    
    @field_validator('threshold_price')
    @classmethod
    def validate_threshold(cls, v):
        if v <= 0:
            raise ValueError('Preço de alerta deve ser maior que zero')
        return v


class AlertResponse(BaseModel):
    """Modelo para resposta de alerta"""
    id: int
    product_id: int
    threshold_price: float
    is_active: int
    created_at: datetime
    triggered_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Configuração do banco de dados
DATABASE_URL = "sqlite:///./pricetrack_ai.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Necessário para SQLite
    echo=False  # Mude para True para debug SQL
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    """Cria todas as tabelas no banco de dados"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency para obter sessão do banco de dados"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Inicialização do banco
if __name__ == "__main__":
    create_tables()
    print("Tabelas criadas com sucesso!")
