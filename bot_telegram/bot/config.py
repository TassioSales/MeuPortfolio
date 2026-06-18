import os
from pathlib import Path
from dotenv import load_dotenv

# Explicit path so load_dotenv works regardless of where the script is launched from
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

TELEGRAM_TOKEN: str = os.environ["TELEGRAM_TOKEN"]
MISTRAL_API_KEY: str = os.environ.get("MISTRAL_API_KEY", "")
DB_PATH: str = os.environ.get("DB_PATH", "data/bot.db")
ALLOWED_USERS: list[str] = [
    u.strip() for u in os.environ.get("ALLOWED_USERS", "").split(",") if u.strip()
]
