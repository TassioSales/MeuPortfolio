#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "Iniciando DevMetrics..."
echo ""

echo "[1/2] Iniciando backend Go (porta 8080)..."
cd backend && go run ./cmd/api/main.go &
BACKEND_PID=$!
cd ..

sleep 2

echo "[2/2] Iniciando frontend Next.js (porta 3000)..."
cd frontend && npm install --silent && npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "Servicos iniciados!"
echo "  Backend:  http://localhost:8080"
echo "  Frontend: http://localhost:3000"
echo ""
echo "Para parar: Ctrl+C"
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
