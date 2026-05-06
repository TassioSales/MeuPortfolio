from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.models import models
from app.schemas import schemas
from app.services import market_service
from app.core.logger import log

router = APIRouter()

@router.post("/", response_model=schemas.AssetOut)
def create_asset(asset: schemas.AssetCreate, db: Session = Depends(get_db)):
    log.info(f"Creating asset: {asset.ticker}")
    db_asset = db.query(models.Asset).filter(models.Asset.ticker == asset.ticker).first()
    if db_asset:
        log.warning(f"Asset already registered: {asset.ticker}")
        raise HTTPException(status_code=400, detail="Asset already registered")
    
    new_asset = models.Asset(**asset.dict())
    db.add(new_asset)
    db.commit()
    db.refresh(new_asset)
    log.info(f"Asset created successfully: {asset.ticker} (ID: {new_asset.id})")
    return new_asset

@router.get("/", response_model=List[schemas.AssetOut])
def read_assets(db: Session = Depends(get_db)):
    log.debug("Fetching all assets")
    return db.query(models.Asset).all()

@router.get("/search/")
async def search_assets(q: str = Query(..., min_length=1)):
    log.info(f"Asset search query: {q}")
    return await market_service.search_yahoo_assets(q)
