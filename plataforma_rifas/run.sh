#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "Iniciando Plataforma de Rifas..."
docker-compose up --build "$@"
