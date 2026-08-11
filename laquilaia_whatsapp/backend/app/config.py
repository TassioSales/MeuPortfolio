from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Database
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://laquilaia:laquilaia_dev_pwd@localhost:5432/laquilaia_db"
    )

    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_cache_ttl: int = int(os.getenv("REDIS_CACHE_TTL", "3600"))
    metrics_cache_ttl: int = int(os.getenv("METRICS_CACHE_TTL", "900"))

    # Security
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    # API
    api_port: int = int(os.getenv("API_PORT", "8000"))
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # AI / LLM
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    claude_model: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-5")
    temperature: float = float(os.getenv("TEMPERATURE", "0.7"))
    max_tokens: int = int(os.getenv("MAX_TOKENS", "1024"))
    llm_max_tokens_per_minute: int = int(os.getenv("LLM_MAX_TOKENS_PER_MINUTE", "40000"))
    llm_max_calls_per_minute: int = int(os.getenv("LLM_MAX_CALLS_PER_MINUTE", "60"))

    # WhatsApp / Evolution API
    evolution_api_url: str = os.getenv("EVOLUTION_API_URL", "http://evolution:4000")
    evolution_api_key: str = os.getenv("EVOLUTION_API_KEY", "")
    evolution_instance_name: str = os.getenv("EVOLUTION_INSTANCE_NAME", "laquilaia")
    evolution_webhook_url: str = os.getenv("EVOLUTION_WEBHOOK_URL", "http://localhost:8000/webhook/whatsapp")

    # Frontend
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
