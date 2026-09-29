#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "============================================"
echo "  Conciliacao Bancaria"
echo "============================================"

command -v python3 >/dev/null || { echo "[ERRO] Python 3 nao encontrado."; exit 1; }

if [ ! -d ".venv" ]; then
  echo "[1/3] Criando ambiente virtual..."
  python3 -m venv .venv
fi

echo "[2/3] Ativando ambiente e instalando dependencias..."
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt

case "${1:-}" in
  testes)  echo "[3/3] Rodando os testes...";  exec python -m pytest tests -q ;;
  avaliar) echo "[3/3] Medindo contra o gabarito..."; exec python avaliar.py ;;
esac

echo "[3/3] Iniciando a interface na porta 8504..."
exec streamlit run app.py --server.port=8504 --browser.gatherUsageStats=false "$@"
