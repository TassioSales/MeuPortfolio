# WealthMap Analytics PRO

Sistema de Gestão de Ativos Financeiros com previsão baseada em Machine Learning (Forecast) e Análise de Risco (Índice Sharpe e Volatilidade).

## Rodar

```bat
start_wealthmap.bat
```

O script instala/atualiza as dependências Python do backend via `backend/requirements.txt`, sobe a API FastAPI em `localhost:8000` e depois inicia o Next.js em `localhost:3000`.

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
- Assistente WealthMap AI com Mistral para analisar risco, concentracao, diversificacao e rebalanceamento.
- Frontend em **Next.js** com **Recharts** e TailwindCSS.
- Backend em **Python (FastAPI)** com banco de dados em **SQLite**.

## IA com Mistral

O backend procura `MISTRAL_API_KEY` nesta ordem:

1. variavel de ambiente do sistema;
2. `.env` na raiz de `wealthmap_analytics`;
3. `.env` do projeto `documind_local`, caso exista.

Exemplo de `.env` local:

```env
MISTRAL_API_KEY=sua_chave_aqui
MISTRAL_MODEL=mistral-small-latest
```

Se a chave nao estiver disponivel ou a API falhar, o WealthMap AI usa um fallback local baseado nas metricas da carteira.

## Estrutura

- `backend/`: API FastAPI, Modelos de ML e Scripts de Banco de Dados.
- `frontend/`: Dashboard Next.js e UI Elements.
