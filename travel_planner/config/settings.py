"""Application settings and configuration.

This module loads and validates environment variables and provides
application-wide configuration settings.
"""
import os
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

from pydantic import Field, validator, HttpUrl
from pydantic.types import DirectoryPath, FilePath
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    DEBUG: bool = Field(False, env="DEBUG")
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    LOG_FILE: str = Field("logs/app.log", env="LOG_FILE")

    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent.absolute()
    ASSETS_DIR: Path = Field("assets", env="ASSETS_DIR")
    DATA_DIR: Path = Field("data", env="DATA_DIR")
    
    # API Timeouts (in seconds)
    HTTP_TIMEOUT: float = Field(10.0, env="HTTP_TIMEOUT")
    MAX_RETRIES: int = Field(3, env="MAX_RETRIES")
    
    # Cache TTL (in seconds)
    CACHE_TTL_FLIGHTS: int = Field(3600, env="CACHE_TTL_FLIGHTS")  # 1 hour
    CACHE_TTL_IMAGES: int = Field(86400, env="CACHE_TTL_IMAGES")  # 24 hours
    
    # API Keys (optional for development with mock data)
    AMADEUS_API_KEY: Optional[str] = Field(None, env="AMADEUS_API_KEY")
    AMADEUS_API_SECRET: Optional[str] = Field(None, env="AMADEUS_API_SECRET")
    GEMINI_API_KEY: Optional[str] = Field(None, env="GEMINI_API_KEY")
    UNSPLASH_ACCESS_KEY: Optional[str] = Field(None, env="UNSPLASH_ACCESS_KEY")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        
    @property
    def assets_path(self) -> Path:
        """Get the full path to the assets directory."""
        return self.BASE_DIR / self.ASSETS_DIR
    
    @property
    def css_path(self) -> Path:
        """Get the full path to the CSS directory."""
        return self.assets_path / "css"
    
    @property
    def images_path(self) -> Path:
        """Get the full path to the images directory."""
        return self.assets_path / "images"
    
    @property
    def airports_data_path(self) -> Path:
        """Get the full path to the airports data file."""
        return self.DATA_DIR / "airports.csv"
    
    @property
    def log_file_path(self) -> Path:
        """Get the full path to the log file."""
        log_path = Path(self.LOG_FILE)
        if not log_path.is_absolute():
            return self.BASE_DIR / log_path
        return log_path


# Create settings instance
settings = Settings()

# Ensure required directories exist
for directory in [
    settings.assets_path,
    settings.css_path,
    settings.images_path,
    settings.DATA_DIR,
    settings.log_file_path.parent
]:
    directory.mkdir(parents=True, exist_ok=True)
