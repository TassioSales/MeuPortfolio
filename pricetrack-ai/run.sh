#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "Iniciando PriceTrack AI..."
if [ ! -f ".env" ] && [ -f "config.env.example" ]; then
  cp config.env.example .env
  echo "[INFO] Configure sua GEMINI_API_KEY no arquivo .env"
fi
docker-compose up --build "$@"
