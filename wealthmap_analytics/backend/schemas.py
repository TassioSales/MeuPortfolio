from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from models import AssetType, TransactionType

class AssetBase(BaseModel):
    ticker: str
    name: str
    asset_type: AssetType
    currency: str = "BRL"

class AssetCreate(AssetBase):
    pass

class AssetOut(AssetBase):
    id: int
    class Config:
        orm_mode = True
        from_attributes = True

class TransactionBase(BaseModel):
    asset_id: int
    transaction_type: TransactionType
    quantity: float
    price_per_unit: float
    fees: float = 0.0
    date: Optional[datetime] = None

class TransactionCreate(TransactionBase):
    pass

class TransactionOut(TransactionBase):
    id: int
    date: datetime
    class Config:
        orm_mode = True
        from_attributes = True

class PortfolioPosition(BaseModel):
    asset: AssetOut
    total_quantity: float
    average_price: float
    current_price: float
    current_value: float
    total_invested: float
    profit_loss: float
    profit_loss_percentage: float
