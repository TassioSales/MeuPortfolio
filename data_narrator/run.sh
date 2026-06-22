#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "Iniciando Data Narrator..."
pip install -r requirements.txt
streamlit run app.py "$@"
