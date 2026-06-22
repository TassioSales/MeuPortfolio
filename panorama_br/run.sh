#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "Iniciando Panorama BR..."
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  cp .env.example .env
  echo "[INFO] .env criado a partir do .env.example"
fi
docker-compose up --build "$@"
