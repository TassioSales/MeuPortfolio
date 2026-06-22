#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "Iniciando ENEM Insights..."
echo ""

if command -v docker &>/dev/null && command -v docker-compose &>/dev/null; then
  echo "Usando Docker Compose..."
  docker-compose up --build "$@"
else
  echo "Docker nao encontrado. Rodando com Python direto..."
  pip install -q -r requirements.txt
  streamlit run "🏠_Home.py" \
    --server.port=8501 \
    --browser.gatherUsageStats=false \
    "$@"
fi
