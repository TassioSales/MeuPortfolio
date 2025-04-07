from pydantic import BaseModel, ConfigDict, Field, validator
from datetime import datetime
from typing import Optional, List, Dict
from .models import ProductCategory

class StockHistoryBase(BaseModel):
    quantity_changed: int = Field(..., description="Quantidade alterada (positivo para entrada, negativo para saída)")
    change_type: str = Field(..., description="Tipo de alteração (entrada ou saída)")
    reason: str = Field(..., description="Motivo da alteração")

    @validator('change_type')
    def validate_change_type(cls, v):
        if v not in ['entrada', 'saída']:
            raise ValueError('change_type deve ser "entrada" ou "saída"')
        return v

class StockHistoryCreate(StockHistoryBase):
    pass

class StockHistory(StockHistoryBase):
    id: int
    product_id: int
    previous_quantity: int
    new_quantity: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    price: float = Field(..., ge=0)
    quantity: int = Field(0, ge=0)
    minimum_stock: int = Field(5, ge=0)
    category: ProductCategory = Field(ProductCategory.OTHERS)
    supplier: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=100)

class ProductCreate(ProductBase):
    pass

class Product(ProductBase):
    id: int
    sku: str
    barcode: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class StockAlert(BaseModel):
    product_id: int
    product_name: str
    current_quantity: int
    minimum_stock: int
    status: str

    model_config = ConfigDict(from_attributes=True)

class DashboardStats(BaseModel):
    total_products: int = Field(0, ge=0)
    total_value: float = Field(0.0, ge=0.0)
    average_price: float = Field(0.0, ge=0.0)
    low_stock_count: int = Field(0, ge=0)
    out_of_stock_count: int = Field(0, ge=0)
    products_by_category: Dict[str, int] = {}
    recent_movements: List[dict] = []

    model_config = ConfigDict(from_attributes=True)

class StockUpdate(BaseModel):
    quantity: int = Field(..., description="Quantidade a ser alterada (positivo para entrada, negativo para saída)")
    reason: str = Field(..., min_length=1, max_length=200, description="Motivo da alteração")

    @validator('quantity')
    def validate_quantity(cls, v):
        if v == 0:
            raise ValueError('A quantidade não pode ser zero')
        return v

class StockUpdateResponse(BaseModel):
    product: Product
    history: StockHistory

    model_config = ConfigDict(from_attributes=True)
