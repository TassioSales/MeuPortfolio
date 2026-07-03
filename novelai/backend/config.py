from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    app_name: str = "NovelAI"
    debug: bool = True
    secret_key: str = "novelai-secret-key-2025-troque-em-producao"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    refresh_token_expire_days: int = 30

    allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # PostgreSQL
    database_url: str = "postgresql+psycopg2://novelai:novelai_dev_local@localhost:5432/novelai"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # NVIDIA NIM
    nvidia_api_key: str = "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"
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model_roteiro: str = "mistralai/mistral-medium-3.5-128b"
    nvidia_model_tts: str = "resemble-ai/chatterbox-multilingual-tts"
    nvidia_model_imagem: str = "qwen/qwen-image"
    nvidia_model_video: str = "nvidia/cosmos3-nano"
    nvidia_model_lipsync: str = "nvidia/lip-sync"
    nvidia_model_seguranca: str = "nvidia/nemotron-3-content-safety"
    nvidia_model_ocr: str = "nvidia/nemotron-ocr-v2"
    nvidia_model_video_detector: str = "nvidia/synthetic-video-detector"

    # Storage
    videos_path: str = "./videos"
    uploads_path: str = "./uploads"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

os.makedirs(settings.videos_path, exist_ok=True)
os.makedirs(settings.uploads_path, exist_ok=True)

NVIDIA_MODELS = {
    "roteiro": settings.nvidia_model_roteiro,
    "tts": settings.nvidia_model_tts,
    "imagem": settings.nvidia_model_imagem,
    "video": settings.nvidia_model_video,
    "lipsync": settings.nvidia_model_lipsync,
    "seguranca": settings.nvidia_model_seguranca,
    "ocr": settings.nvidia_model_ocr,
    "video_detector": settings.nvidia_model_video_detector,
}
