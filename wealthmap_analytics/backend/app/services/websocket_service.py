from fastapi import WebSocket
import asyncio
import random
from app.core.logger import log

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        log.debug(f"WS Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            log.debug(f"WS Client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                log.debug(f"Error broadcasting to client: {e}")
                pass

manager = ConnectionManager()

async def market_ticker_generator():
    log.info("Starting market ticker background task...")
    symbols = ["IBOV", "S&P500", "BTC/USD", "USD/BRL", "PETR4", "AAPL"]
    base_prices = {"IBOV": 130000, "S&P500": 5100, "BTC/USD": 64000, "USD/BRL": 5.05, "PETR4": 38.50, "AAPL": 172.00}
    
    while True:
        try:
            await asyncio.sleep(2)
            updates = []
            for sym in symbols:
                change = random.uniform(-0.002, 0.002) 
                base_prices[sym] = base_prices[sym] * (1 + change)
                updates.append({
                    "symbol": sym,
                    "price": base_prices[sym],
                    "change_pct": change * 100
                })
            await manager.broadcast({"type": "ticker_update", "data": updates})
        except Exception as e:
            log.error(f"Error in market ticker generator: {e}")
            await asyncio.sleep(5)
