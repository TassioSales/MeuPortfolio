import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN: str = os.environ["TELEGRAM_TOKEN"]
MISTRAL_API_KEY: str = os.environ.get("MISTRAL_API_KEY", "")
DB_PATH: str = os.environ.get("DB_PATH", "data/bot.db")
ALLOWED_USERS: list[str] = [
    u.strip() for u in os.environ.get("ALLOWED_USERS", "").split(",") if u.strip()
]
