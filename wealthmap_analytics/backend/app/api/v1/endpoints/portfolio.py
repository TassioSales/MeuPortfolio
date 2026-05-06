from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.schemas import schemas
from app.services import portfolio_service
from app.core.logger import log

router = APIRouter()

@router.get("/", response_model=List[schemas.PortfolioPosition])
async def get_portfolio_endpoint(db: Session = Depends(get_db)):
    try:
        return await portfolio_service.calculate_portfolio(db)
    except Exception as e:
        log.error(f"Failed to fetch portfolio: {e}")
        raise HTTPException(status_code=500, detail="Error calculating portfolio")
