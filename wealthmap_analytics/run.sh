#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "Iniciando WealthMap Analytics..."
if [ ! -f ".env" ]; then
  echo "[AVISO] Configure MISTRAL_API_KEY no arquivo .env para habilitar IA."
fi
docker-compose up --build "$@"
