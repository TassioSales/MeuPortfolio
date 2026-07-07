from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    MISTRAL_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    DATABASE_URL: str = "sqlite+aiosqlite:///./ascend.db"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ALGORITHM: str = "HS256"


settings = Settings()
