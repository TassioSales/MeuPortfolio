#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "Iniciando Finanças ERP..."
echo ""

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  cp .env.example .env
  echo "[INFO] .env criado a partir do .env.example"
fi

pip install -q -r requirements.txt
python manage.py migrate --run-syncdb 2>/dev/null || true

echo ""
echo "Servidor iniciado em http://localhost:8000"
python manage.py runserver 0.0.0.0:8000 "$@"
