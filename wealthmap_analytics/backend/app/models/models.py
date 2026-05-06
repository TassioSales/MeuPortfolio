from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base
import enum
from datetime import datetime

class AssetType(str, enum.Enum):
    STOCK = "STOCK"
    FII = "FII"
    CRYPTO = "CRYPTO"
    ETF = "ETF"

class TransactionType(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"

class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, unique=True, index=True)
    name = Column(String)
    asset_type = Column(Enum(AssetType))
    currency = Column(String, default="BRL")
    
    transactions = relationship("Transaction", back_populates="asset", cascade="all, delete-orphan")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"))
    transaction_type = Column(Enum(TransactionType))
    quantity = Column(Float)
    price_per_unit = Column(Float)
    fees = Column(Float, default=0.0)
    date = Column(DateTime, default=datetime.utcnow)
    
    asset = relationship("Asset", back_populates="transactions")
