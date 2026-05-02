from fastapi import WebSocket
import asyncio
import random
import yfinance as yf

# For the mock chatbot
def generate_ai_response(message: str, portfolio_data: list, risk_metrics: dict):
    msg = message.lower()
    
    total_val = sum([p['current_value'] for p in portfolio_data])
    ativos = [p['asset']['ticker'] for p in portfolio_data]
    
    if "risco" in msg or "seguro" in msg:
        vol = risk_metrics.get("portfolio_volatility", 0) * 100
        if vol > 25:
            return f"**Alerta de Risco Alto!** Sua volatilidade anualizada está em {vol:.1f}%. Eu recomendo diversificar para ativos mais seguros (como Renda Fixa ou ETFs como IVVB11) se você não tiver estômago para grandes quedas."
        else:
            return f"Sua carteira está com um perfil moderado/conservador. Volatilidade em {vol:.1f}%. Está bem balanceada."
            
    if "otimiza" in msg or "markowitz" in msg or "ideal" in msg or "melhorar" in msg:
        weights = risk_metrics.get("optimal_weights", {})
        if not weights:
            return "Adicione mais ativos na sua carteira para eu rodar o algoritmo de Markowitz."
        response = "Rodando o modelo da Fronteira Eficiente (Markowitz), a alocação matemática ideal para maximizar seus lucros e reduzir o risco seria:\n\n"
        for t, w in weights.items():
            if w > 0.01:
                response += f"- **{t}**: {w*100:.1f}%\n"
        return response

    if "carteira" in msg or "resumo" in msg:
        return f"Você tem R$ {total_val:.2f} investidos em {len(ativos)} ativos ({', '.join(ativos[:3])}...). Seu Índice de Sharpe é {risk_metrics.get('portfolio_sharpe', 0):.2f}. Se o Sharpe estiver abaixo de 0.5, você está assumindo risco demais para pouco lucro."

    # Default
    return ("Olá! Eu sou o DocuMind AI Analytics, integrado nativamente ao WealthMap. "
            "Posso analisar o **Risco**, **Otimizar** sua carteira via Markowitz, ou fazer um **Resumo** "
            "financeiro. O que você deseja?")

# WebSocket Manager for Real-time
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

async def market_ticker_generator():
    """Background task to simulate live market fluctuations for the websocket"""
    symbols = ["IBOV", "S&P500", "BTC/USD", "USD/BRL", "PETR4", "AAPL"]
    base_prices = {"IBOV": 130000, "S&P500": 5100, "BTC/USD": 64000, "USD/BRL": 5.05, "PETR4": 38.50, "AAPL": 172.00}
    
    while True:
        await asyncio.sleep(2)
        updates = []
        for sym in symbols:
            # Random walk
            change = random.uniform(-0.002, 0.002) 
            base_prices[sym] = base_prices[sym] * (1 + change)
            updates.append({
                "symbol": sym,
                "price": base_prices[sym],
                "change_pct": change * 100
            })
        await manager.broadcast({"type": "ticker_update", "data": updates})
