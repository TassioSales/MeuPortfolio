#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "Iniciando ENEM Insights..."
docker-compose up --build "$@"
