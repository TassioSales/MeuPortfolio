from fastapi import FastAPI, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import yfinance as yf
import asyncio
from contextlib import asynccontextmanager

import models, schemas, database, services, ml_services, sentiment_service, ai_ws_services

models.Base.metadata.create_all(bind=database.engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(ai_ws_services.market_ticker_generator())
    yield
    task.cancel()

app = FastAPI(title="WealthMap Analytics PRO API", lifespan=lifespan)

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

import requests

@app.get("/search/")
def search_assets(q: str = Query(..., min_length=1)):
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={q}"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=5).json()
        results = []
        for quote in res.get('quotes', []):
            q_type = quote.get('quoteType', '')
            if q_type in ['EQUITY', 'ETF', 'MUTUALFUND', 'CRYPTOCURRENCY', 'INDEX']:
                # Heuristica de tipo
                asset_type = "CRYPTO" if q_type == 'CRYPTOCURRENCY' else ("FII" if "FII" in quote.get('shortname', '') else "STOCK")
                results.append({
                    "ticker": quote.get('symbol'),
                    "name": quote.get('shortname', quote.get('longname', 'Desconhecido')),
                    "asset_type": asset_type
                })
        return results[:8]
    except Exception as e:
        print("Search error:", e)
        return []

@app.get("/assets/search/")
def search_assets_compat(q: str = Query(..., min_length=1)):
    return search_assets(q)

@app.get("/analytics/risk")
def get_risk_analytics(db: Session = Depends(database.get_db)):
    assets = db.query(models.Asset).all()
    tickers = [a.ticker for a in assets]
    return ml_services.calculate_risk_metrics(tickers)

@app.get("/forecast/{ticker}")
def get_forecast(ticker: str, days: int = 15):
    return ml_services.forecast_price(ticker, days)

@app.get("/analytics/forecast/{ticker}")
def get_forecast_compat(ticker: str, days: int = 15):
    return get_forecast(ticker, days)

@app.get("/sentiment/{ticker}")
def get_sentiment(ticker: str):
    return sentiment_service.get_asset_sentiment(ticker)

@app.get("/ai/sentiment/{ticker}")
def get_sentiment_compat(ticker: str):
    return get_sentiment(ticker)

@app.get("/analytics/macro")
def get_macro_data():
    try:
        # Mocking or fetching simple macro data for the dashboard
        return {
            "selic_target": 10.75,
            "ipca_12m": 4.50,
            "us_fed_rate": 5.50,
            "status": "Atenção (Juros Altos)"
        }
    except:
        return {}

from pydantic import BaseModel
class ChatRequest(BaseModel):
    message: str

@app.post("/ai/chat")
def chat_with_ai(req: ChatRequest, db: Session = Depends(database.get_db)):
    portfolio = get_portfolio(db)
    tickers = [p.asset.ticker for p in portfolio]
    risk_metrics = ml_services.calculate_risk_metrics(tickers)
    
    reply = ai_ws_services.generate_ai_response(req.message, [p.dict() for p in portfolio], risk_metrics)
    return {"reply": reply}

@app.websocket("/ws/ticker")
async def websocket_ticker(websocket: WebSocket):
    await ai_ws_services.manager.connect(websocket)
    try:
        while True:
            # We keep the connection alive, ping/pong. The actual data is sent by the background task.
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ai_ws_services.manager.disconnect(websocket)

@app.websocket("/ai/ws/ticker")
async def websocket_ticker_compat(websocket: WebSocket):
    await websocket_ticker(websocket)

@app.get("/health")
def health():
    return {"status": "ok", "service": "wealthmap-api"}

@app.get("/")
def read_root():
    return {"message": "Welcome to WealthMap Analytics PRO API"}
