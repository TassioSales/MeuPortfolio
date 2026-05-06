from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import models
from app.schemas import schemas
from app.core.logger import log

router = APIRouter()

@router.post("/", response_model=schemas.TransactionOut)
def create_transaction(transaction: schemas.TransactionCreate, db: Session = Depends(get_db)):
    log.info(f"Creating transaction for asset_id: {transaction.asset_id} ({transaction.transaction_type})")
    asset = db.query(models.Asset).filter(models.Asset.id == transaction.asset_id).first()
    if not asset:
        log.error(f"Asset not found for transaction: {transaction.asset_id}")
        raise HTTPException(status_code=404, detail="Asset not found")
    
    new_tx = models.Transaction(**transaction.dict())
    db.add(new_tx)
    db.commit()
    db.refresh(new_tx)
    log.info(f"Transaction created successfully: {new_tx.id}")
    return new_tx
