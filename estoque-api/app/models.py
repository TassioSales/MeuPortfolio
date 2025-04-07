from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, CheckConstraint, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum
from .database import Base

class ProductCategory(str, Enum):
    ELECTRONICS = "ELECTRONICS"
    CLOTHING = "CLOTHING"
    FOOD = "FOOD"
    BOOKS = "BOOKS"
    OTHERS = "OTHERS"

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(String(500), nullable=True)
    price = Column(Float, CheckConstraint('price >= 0'), nullable=False, default=0.0)
    quantity = Column(Integer, CheckConstraint('quantity >= 0'), default=0, nullable=False)
    minimum_stock = Column(Integer, CheckConstraint('minimum_stock >= 0'), default=5, nullable=False)
    category = Column(SQLEnum(ProductCategory), nullable=False, default=ProductCategory.OTHERS)
    supplier = Column(String(100), nullable=True)
    location = Column(String(100), nullable=True)
    sku = Column(String(20), unique=True, nullable=False, index=True)
    barcode = Column(String(13), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    history = relationship("StockHistory", back_populates="product", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Product {self.name}>"

class StockHistory(Base):
    __tablename__ = "stock_history"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    quantity_changed = Column(Integer, nullable=False)
    previous_quantity = Column(Integer, CheckConstraint('previous_quantity >= 0'), nullable=False)
    new_quantity = Column(Integer, CheckConstraint('new_quantity >= 0'), nullable=False)
    change_type = Column(String(10), CheckConstraint("change_type IN ('entrada', 'saída')"), nullable=False)
    reason = Column(String(200), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    product = relationship("Product", back_populates="history")

    def __repr__(self):
        return f"<StockHistory {self.product_id} {self.change_type} {self.quantity_changed}>"
