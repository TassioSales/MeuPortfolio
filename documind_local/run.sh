#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "Iniciando DocuMind Local..."
echo ""

# Instalar dependências Python do backend se existir requirements.txt
if [ -f "backend/requirements.txt" ]; then
  echo "Instalando dependências Python..."
  pip install -q -r backend/requirements.txt
fi

echo "[1/1] Iniciando backend Go (porta 8080)..."
cd backend && go run ./cmd/api/main.go &
API_PID=$!
cd ..

sleep 3
echo ""
echo "DocuMind iniciado!"
echo "  Interface: http://localhost:8080"
echo ""
echo "Para parar: Ctrl+C"
trap "kill $API_PID 2>/dev/null" EXIT
wait
