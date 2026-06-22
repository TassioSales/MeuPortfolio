#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "Iniciando Neon Drift..."
echo ""

echo "[1/2] Iniciando backend Go (porta 8080)..."
cd backend && go run ./cmd/api/main.go &
API_PID=$!
cd ..

sleep 2

echo "[2/2] Abrindo jogo no navegador..."
if command -v xdg-open &>/dev/null; then
  xdg-open "frontend/index.html"
elif command -v open &>/dev/null; then
  open "frontend/index.html"
fi

echo ""
echo "Neon Drift iniciado!"
echo "  API:  http://localhost:8080"
echo "  Jogo: frontend/index.html"
echo ""
echo "Para parar: Ctrl+C"
trap "kill $API_PID 2>/dev/null" EXIT
wait
