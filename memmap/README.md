# MemMap — Second Brain com Grafo de Conhecimento

Editor de notas que extrai entidades automaticamente com NLP (spaCy), liga conceitos e exibe um **grafo interativo force-directed** com D3.js via WebSocket em tempo real.

## Stack

| Camada | Tecnologia |
|--------|-----------|
| NLP | Python + FastAPI + spaCy |
| API | Go + chi + gorilla/websocket + SQLite (modernc) |
| Frontend | Next.js 14 + TypeScript + Tailwind + D3.js |
| Infra | Docker Compose |

## Funcionalidades

- **Extração de entidades** com spaCy (pessoas, organizações, locais, datas…)
- **Detecção de relações** por co-ocorrência em sentenças
- **Grafo force-directed** interativo com D3.js
  - Nós coloridos por tipo de entidade
  - Tamanho proporcional ao número de aparições
  - Tooltip ao hover
  - Drag & zoom
  - Atualizações em tempo real via WebSocket
- **Editor de notas** com preview de entidades antes de salvar
- **Painel de detalhes** do nó: tipo, contagem, notas relacionadas

## Como Executar

### Com Docker (recomendado)

```bash
# Linux/macOS
./run.sh

# Windows
run.bat
```

Acesse: **http://localhost:3000**

### Desenvolvimento local

**NLP Service (porta 8001):**
```bash
cd nlp
pip install -r requirements.txt
python -m spacy download en_core_web_sm
uvicorn main:app --port 8001 --reload
```

**Go API (porta 8080):**
```bash
cd api
go run ./cmd/api/main.go
```

**Frontend (porta 3000):**
```bash
cd frontend
npm install
npm run dev
```

## Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `API_PORT` | `8080` | Porta da API Go |
| `DB_PATH` | `./data/memmap.db` | Caminho do banco SQLite |
| `NLP_URL` | `http://localhost:8001` | URL do serviço NLP |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8080` | URL da API Go (cliente) |
| `NEXT_PUBLIC_WS_URL` | `ws://localhost:8080/ws` | URL do WebSocket |

## Endpoints da API

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/notes` | Lista todas as notas |
| `POST` | `/notes` | Cria nota com entidades e relações |
| `GET` | `/notes/:id` | Busca nota por ID |
| `DELETE` | `/notes/:id` | Deleta nota e suas entidades |
| `GET` | `/graph` | Retorna GraphData agregado |
| `GET` | `/ws` | WebSocket — broadcast do grafo |

## Endpoints do NLP

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/extract` | Extrai entidades e relações |
| `GET` | `/health` | Status do serviço e modelo carregado |

## Arquitetura

```
Nota criada
     │
     ▼
Next.js → POST /api/nlp/extract → NLP (spaCy)
     │                                  │
     │         entities + relations     │
     │◄─────────────────────────────────┘
     │
     ▼
POST /notes → Go API → SQLite
                  │
                  ▼
             WebSocket broadcast → todos os clientes
                  │
                  ▼
             D3.js re-renderiza o grafo
```
