from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import yfinance as yf

import models, schemas, database, services, ml_services

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="WealthMap Analytics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/assets/", response_model=schemas.AssetOut)
def create_asset(asset: schemas.AssetCreate, db: Session = Depends(database.get_db)):
    db_asset = db.query(models.Asset).filter(models.Asset.ticker == asset.ticker).first()
    if db_asset:
        raise HTTPException(status_code=400, detail="Asset already registered")
    new_asset = models.Asset(**asset.dict())
    db.add(new_asset)
    db.commit()
    db.refresh(new_asset)
    return new_asset

@app.get("/assets/", response_model=List[schemas.AssetOut])
def read_assets(db: Session = Depends(database.get_db)):
    return db.query(models.Asset).all()

@app.post("/transactions/", response_model=schemas.TransactionOut)
def create_transaction(transaction: schemas.TransactionCreate, db: Session = Depends(database.get_db)):
    asset = db.query(models.Asset).filter(models.Asset.id == transaction.asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    new_tx = models.Transaction(**transaction.dict())
    db.add(new_tx)
    db.commit()
    db.refresh(new_tx)
    return new_tx

@app.get("/portfolio/", response_model=List[schemas.PortfolioPosition])
def get_portfolio(db: Session = Depends(database.get_db)):
    assets = db.query(models.Asset).all()
    portfolio = []
    
    for asset in assets:
        transactions = db.query(models.Transaction).filter(models.Transaction.asset_id == asset.id).all()
        
        total_quantity = 0.0
        total_invested = 0.0
        
        for tx in transactions:
            if tx.transaction_type == models.TransactionType.BUY:
                total_quantity += tx.quantity
                total_invested += (tx.quantity * tx.price_per_unit) + tx.fees
            elif tx.transaction_type == models.TransactionType.SELL:
                if total_quantity > 0:
                    # Calculate proportion to subtract from total_invested (Preço Médio concept)
                    average_price_before_sell = total_invested / total_quantity
                    total_quantity -= tx.quantity
                    total_invested -= (tx.quantity * average_price_before_sell)
        
        if total_quantity > 0:
            average_price = total_invested / total_quantity
            current_price = services.get_market_price(asset.ticker, asset.asset_type.value)
            current_value = current_price * total_quantity
            profit_loss = current_value - total_invested
            profit_loss_percentage = (profit_loss / total_invested) * 100 if total_invested > 0 else 0
            
            portfolio.append(schemas.PortfolioPosition(
                asset=schemas.AssetOut.from_orm(asset),
                total_quantity=total_quantity,
                average_price=average_price,
                current_price=current_price,
                current_value=current_value,
                total_invested=total_invested,
                profit_loss=profit_loss,
                profit_loss_percentage=profit_loss_percentage
            ))
            
    return portfolio

@app.get("/search/")
def search_assets(q: str = Query(..., min_length=2)):
    # Very simple search using yfinance. In a real app we'd use a better search API.
    # We will simulate returning a standard response.
    try:
        # yf.Ticker(q).info is too slow for real-time search without a DB cache, 
        # but for demonstration we just return the ticker if it exists.
        # Alternatively, we just return the query formatted.
        return [{"ticker": q.upper(), "name": f"Pesquisa: {q.upper()}", "asset_type": "STOCK"}]
    except:
        return []

@app.get("/analytics/risk")
def get_risk_analytics(db: Session = Depends(database.get_db)):
    assets = db.query(models.Asset).all()
    tickers = [a.ticker for a in assets]
    return ml_services.calculate_risk_metrics(tickers)

@app.get("/forecast/{ticker}")
def get_forecast(ticker: str, days: int = 30):
    return ml_services.forecast_price(ticker, days)

@app.get("/")
def read_root():
    return {"message": "Welcome to WealthMap Analytics API"}
