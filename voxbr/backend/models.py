from pydantic import BaseModel
from typing import Optional


class TranscriptionCreate(BaseModel):
    filename: str
    language: str = "pt"


class TranscriptionResponse(BaseModel):
    id: int
    filename: str
    language: str
    transcript: str
    summary: str
    key_points: list[str]
    duration_seconds: float
    created_at: str
    status: str  # "processing" | "done" | "error"


class TranscriptionUpdate(BaseModel):
    transcript: Optional[str] = None
    summary: Optional[str] = None
    key_points: Optional[list[str]] = None
    duration_seconds: Optional[float] = None
    status: Optional[str] = None
    error_message: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    whisper_model: str


class DeleteResponse(BaseModel):
    message: str
    id: int
