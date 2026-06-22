#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "Iniciando Gerador de Roteiros..."
docker-compose up --build "$@"
