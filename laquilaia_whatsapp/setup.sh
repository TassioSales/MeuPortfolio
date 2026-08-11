#!/bin/bash

# L'Aquila AI - Initial Setup Script (Linux/Mac)
# This script prepares the environment for first run

set -e

echo ""
echo "========================================"
echo " L'Aquila AI - Initial Setup"
echo " Linux/Mac Configuration"
echo "========================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo ""
    echo "[ERROR] Docker is not installed"
    echo "Please install Docker from: https://docs.docker.com/get-docker/"
    echo ""
    exit 1
fi

echo "[OK] Docker is installed"

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "[WARNING] docker-compose not found, will try docker compose"
fi

echo "[OK] Docker setup verified"
echo ""

# Create .env from .env.example if it doesn't exist
if [ -f .env ]; then
    echo "[INFO] .env file already exists, skipping copy"
    echo "[INFO] To reset, delete .env and run setup again"
else
    if [ -f .env.example ]; then
        echo "[INFO] Creating .env from .env.example..."
        cp .env.example .env
        chmod 600 .env
        echo "[OK] .env created (permissions: 600)"
        echo ""
        echo "[ACTION REQUIRED] Please update .env with your configuration:"
        echo "  - ANTHROPIC_API_KEY: Your Anthropic API key"
        echo "  - EVOLUTION_API_KEY: Your Evolution API key"
        echo "  - DATABASE_URL: PostgreSQL connection string (or use default)"
        echo "  - REDIS_URL: Redis connection string (or use default)"
        echo ""
        echo "Edit .env with your text editor:"
        echo "  nano .env"
        echo "  or"
        echo "  vi .env"
    else
        echo ""
        echo "[ERROR] .env.example not found"
        echo "Make sure you run this script from the project root directory"
        echo ""
        exit 1
    fi
fi

echo ""
echo "[INFO] Checking required environment variables..."

# Check if .env exists and has required keys
if [ -f .env ]; then
    if grep -qi "ANTHROPIC_API_KEY" .env; then
        echo "[OK] ANTHROPIC_API_KEY is configured"
    else
        echo "[WARNING] ANTHROPIC_API_KEY not configured"
    fi

    if grep -qi "DATABASE_URL" .env; then
        echo "[OK] DATABASE_URL is configured"
    else
        echo "[WARNING] DATABASE_URL not configured (will use defaults)"
    fi

    if grep -qi "EVOLUTION_API_KEY" .env; then
        echo "[OK] EVOLUTION_API_KEY is configured"
    else
        echo "[WARNING] EVOLUTION_API_KEY not configured"
    fi
fi

echo ""
echo "========================================"
echo " Setup Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your API keys and configuration"
echo "       nano .env"
echo ""
echo "  2. Make scripts executable:"
echo "       chmod +x run.sh setup.sh"
echo ""
echo "  3. Run:"
echo "       ./run.sh"
echo "       (to start all services)"
echo ""
echo "For more information, see:"
echo "  - CLAUDE.md for project structure"
echo "  - laquilaia_whatsapp/GUIA_WEBHOOK.md for webhook docs"
echo "  - laquilaia_whatsapp/GUIA_LLM.md for LLM docs"
echo ""
