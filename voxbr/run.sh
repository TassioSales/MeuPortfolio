#!/bin/bash
set -e

echo "============================================"
echo "   VoxBR - Plataforma de Transcricao de Audio"
echo "============================================"
echo ""
echo "NOTA: A primeira inicializacao baixa o modelo"
echo "      Whisper 'base' (~150MB). Aguarde..."
echo ""

# Check for .env file
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "Arquivo .env nao encontrado. Copiando .env.example..."
        cp .env.example .env
        echo "Edite .env e adicione sua MISTRAL_API_KEY para habilitar resumos com IA."
        echo ""
    fi
fi

echo "Iniciando servicos com Docker Compose..."
echo ""
docker-compose up --build "$@"
