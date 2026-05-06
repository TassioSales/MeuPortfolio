from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.session import get_db
from app.services import ai_service, sentiment_service, websocket_service, ml_service, portfolio_service
from app.core.logger import log

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

@router.get("/status")
def get_ai_status():
    return ai_service.get_ai_status()

@router.post("/chat")
async def chat_with_ai(req: ChatRequest, db: Session = Depends(get_db)):
    try:
        log.info(f"AI Chat request: {req.message}")
        portfolio = await portfolio_service.calculate_portfolio(db)
        tickers = [p.asset.ticker for p in portfolio]
        
        log.debug(f"Calculating risk metrics for tickers: {tickers}")
        risk_metrics = ml_service.calculate_risk_metrics(tickers)
        
        log.debug("Generating AI response...")
        reply = ai_service.generate_ai_response(req.message, [p.dict() for p in portfolio], risk_metrics)
        
        log.info("AI response generated successfully")
        return {"reply": reply}
    except Exception as e:
        log.error(f"AI Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error in AI service")

@router.get("/sentiment/{ticker}")
def get_sentiment(ticker: str):
    try:
        log.info(f"Sentiment request for {ticker}")
        return sentiment_service.get_asset_sentiment(ticker)
    except Exception as e:
        log.error(f"Sentiment error for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Error fetching sentiment")

@router.websocket("/ws/ticker")
async def websocket_ticker(websocket: WebSocket):
    await websocket_service.manager.connect(websocket)
    log.info("WebSocket connected to /ws/ticker")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_service.manager.disconnect(websocket)
        log.info("WebSocket disconnected from /ws/ticker")
