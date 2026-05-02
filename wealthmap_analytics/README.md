# WealthMap Analytics PRO

Sistema de Gestão de Ativos Financeiros com previsão baseada em Machine Learning (Forecast) e Análise de Risco (Índice Sharpe e Volatilidade).

## Rodar

```bat
start_wealthmap.bat
```

Abra:

```txt
http://localhost:3000
```

Para parar os servidores:

```bat
stop_wealthmap.bat
```

## O que faz

- Integração com `yfinance` para buscar dados oficiais da bolsa (B3/EUA).
- Integração com `CoinGecko` para buscar criptomoedas.
- Modelo preditivo usando `scikit-learn` para projetar o preço dos próximos 30 dias.
- Matriz de Correlação cruzada em tempo real para controle de diversificação.
- Frontend em **Next.js** com **Recharts** e TailwindCSS.
- Backend em **Python (FastAPI)** com banco de dados em **SQLite**.

## Estrutura

- `backend/`: API FastAPI, Modelos de ML e Scripts de Banco de Dados.
- `frontend/`: Dashboard Next.js e UI Elements.
