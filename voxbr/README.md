# VoxBR — Plataforma de Transcrição de Áudio com IA

Plataforma completa para transcrição automática de áudio usando **OpenAI Whisper** e geração de resumos inteligentes com **Mistral AI**.

## Funcionalidades

- Upload de arquivos de áudio via drag & drop
- Transcrição automática com Whisper (modelo `base`, ~150MB)
- Resumo inteligente e pontos principais com Mistral AI
- Histórico completo de transcrições em SQLite
- Exportação em TXT
- Interface dark mode com tema roxo
- Suporte a múltiplos idiomas (PT, EN, ES e outros)

## Formatos suportados

`mp3`, `mp4`, `wav`, `m4a`, `ogg`, `flac`, `webm`

## Pré-requisitos

- Docker e Docker Compose instalados
- (Opcional) Chave de API Mistral AI para resumos com IA

## Como rodar

### Linux / macOS

```bash
cd voxbr
cp .env.example .env
# Edite .env e adicione MISTRAL_API_KEY (opcional)
./run.sh
```

### Windows

```bat
cd voxbr
copy .env.example .env
# Edite .env e adicione MISTRAL_API_KEY (opcional)
run.bat
```

Acesse:
- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000
- **Docs da API**: http://localhost:8000/docs

## Variáveis de ambiente

| Variável | Descrição | Obrigatório |
|----------|-----------|-------------|
| `MISTRAL_API_KEY` | Chave de API Mistral AI para resumos | Não (fallback automático) |

## Arquitetura

```
voxbr/
├── backend/          Python FastAPI + Whisper + Mistral AI + SQLite
└── frontend/         Next.js 14 + TypeScript + Tailwind CSS
```

### Backend (FastAPI)

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/transcribe` | POST | Upload de áudio — retorna status "processing" |
| `/transcriptions` | GET | Lista todas as transcrições |
| `/transcriptions/{id}` | GET | Busca por ID |
| `/transcriptions/{id}` | DELETE | Deleta por ID |
| `/transcriptions/{id}/export?format=txt` | GET | Exporta como TXT |
| `/health` | GET | Status da API |

### Frontend (Next.js)

- `AudioUpload`: drag & drop + polling de status
- `TranscriptView`: visualização lado a lado (transcrição + resumo)
- `HistoryPanel`: histórico com opção de deletar

## Desenvolvimento

### Backend

```bash
cd backend
pip install -r requirements.txt
mkdir -p data
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

## Notas

- A primeira inicialização baixa o modelo Whisper `base` (~150MB) automaticamente
- Sem `MISTRAL_API_KEY`, o resumo é gerado a partir das primeiras frases da transcrição
- Arquivos de áudio temporários são apagados após a transcrição
- Dados persistidos em volume Docker `voxbr_data`
