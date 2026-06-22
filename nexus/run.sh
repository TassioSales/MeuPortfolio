#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "Iniciando Nexus - AI Agent Terminal..."
pip install -q -r requirements.txt
python main.py "$@"
