#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "Iniciando Bot Telegram..."
if [ ! -f ".env" ]; then
  echo "[AVISO] Arquivo .env nao encontrado. Copie .env.example para .env e configure seu TELEGRAM_BOT_TOKEN."
  exit 1
fi
docker-compose up --build "$@"
