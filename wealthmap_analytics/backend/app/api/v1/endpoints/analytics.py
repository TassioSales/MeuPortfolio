from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import models
from app.services import ml_service

router = APIRouter()

@router.get("/risk")
def get_risk_analytics(db: Session = Depends(get_db)):
    assets = db.query(models.Asset).all()
    tickers = [a.ticker for a in assets]
    return ml_service.calculate_risk_metrics(tickers)

@router.get("/forecast/{ticker}")
def get_forecast(ticker: str, days: int = 15):
    return ml_service.forecast_price(ticker, days)

@router.get("/macro")
def get_macro_data():
    return {
        "selic_target": 10.75,
        "ipca_12m": 4.50,
        "us_fed_rate": 5.50,
        "status": "Atenção (Juros Altos)"
    }
