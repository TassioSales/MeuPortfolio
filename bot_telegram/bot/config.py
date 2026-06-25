import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Try multiple paths to find .env — handles different launch scenarios
_candidates = [
    Path(__file__).resolve().parent.parent / ".env",  # bot_telegram/.env (expected)
    Path.cwd() / ".env",                              # current working directory
    Path(__file__).resolve().parent / ".env",         # bot/.env (fallback)
]

_loaded = False
for _path in _candidates:
    if _path.exists():
        load_dotenv(_path, override=True)
        _loaded = True
        break

if not _loaded:
    # Last resort: let load_dotenv search upward from cwd
    load_dotenv(override=True)

# Validate required token
TELEGRAM_TOKEN: str = os.environ.get("TELEGRAM_TOKEN", "")
if not TELEGRAM_TOKEN:
    print(
        "\n[ERRO] TELEGRAM_TOKEN não encontrado.\n"
        f"Arquivo .env procurado em: {[str(p) for p in _candidates]}\n"
        "Verifique se o arquivo .env existe e contém TELEGRAM_TOKEN=<seu_token>\n",
        file=sys.stderr,
    )
    sys.exit(1)

MISTRAL_API_KEY: str = os.environ.get("MISTRAL_API_KEY", "")
DB_PATH: str = os.environ.get("DB_PATH", "data/bot.db")
ALLOWED_USERS: list[str] = [
    u.strip() for u in os.environ.get("ALLOWED_USERS", "").split(",") if u.strip()
]
