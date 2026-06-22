"""Nexus — AI Agent Terminal.

Usage:
    python main.py           # launch the TUI
    python main.py --help    # show help
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is on the path when run directly.
sys.path.insert(0, str(Path(__file__).parent))

import config  # noqa: F401 — loads .env before anything else

from ui.app import main

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        print(
            "\n"
            "  NEXUS ◈ AI Agent Terminal\n"
            "  ─────────────────────────\n"
            "  Um agente IA com ferramentas reais:\n"
            "    🔍 Busca web (DuckDuckGo)\n"
            "    🐍 Execução Python segura\n"
            "    📁 Leitura e escrita de arquivos\n"
            "    🌐 Fetch de URLs\n\n"
            "  Configuração:\n"
            "    export MISTRAL_API_KEY='sua-chave'\n"
            "    python main.py\n\n"
            "  Atalhos:\n"
            "    Ctrl+N  Nova sessão\n"
            "    Ctrl+L  Limpar chat\n"
            "    Ctrl+Q  Sair\n"
        )
        sys.exit(0)

    main()
