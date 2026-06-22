#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "========================================"
echo "  Fuel Control Room - Live Intelligence"
echo "========================================"
echo ""

ROOT="$(pwd)"
PIPELINE_DIR="$ROOT/data-pipeline-python"
BACKEND_DIR="$ROOT/backend-go"
FRONTEND_DIR="$ROOT/frontend-next"
LOG_DIR="$ROOT/logs"

mkdir -p "$LOG_DIR"

# Verificar dependências
command -v python3 &>/dev/null || { echo "[ERRO] Python3 não encontrado."; exit 1; }
command -v go &>/dev/null || { echo "[ERRO] Go não encontrado."; exit 1; }
command -v node &>/dev/null || { echo "[ERRO] Node.js não encontrado."; exit 1; }

echo "[1/5] Configurando ambiente Python..."
if [ ! -d "$PIPELINE_DIR/.venv" ]; then
  python3 -m venv "$PIPELINE_DIR/.venv"
fi
source "$PIPELINE_DIR/.venv/bin/activate"
pip install -q -e "$PIPELINE_DIR[dev]"

echo "[2/5] Rodando pipeline de dados..."
python -m fuel_analytics.cli run 2>&1 | tee "$LOG_DIR/pipeline.log"

echo "[3/5] Sincronizando dependências Go..."
cd "$BACKEND_DIR" && go mod tidy && cd "$ROOT"

echo "[4/5] Instalando dependências frontend..."
cd "$FRONTEND_DIR" && npm install --silent && cd "$ROOT"

echo "[5/5] Iniciando serviços..."
cd "$BACKEND_DIR" && go run ./cmd/api &> "$LOG_DIR/backend.log" &
echo "API Go iniciada (PID $!)"

cd "$FRONTEND_DIR" && npm run dev &> "$LOG_DIR/frontend.log" &
echo "Frontend Next.js iniciado (PID $!)"

echo ""
echo "Serviços ativos:"
echo "  Frontend: http://localhost:3000"
echo "  API:      http://localhost:8080"
echo ""
echo "Logs em: $LOG_DIR"
echo "Para parar: Ctrl+C"
wait
