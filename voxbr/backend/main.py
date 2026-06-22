import os
import uuid
import shutil
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from loguru import logger
from dotenv import load_dotenv

import storage
import transcriber
import summarizer
from models import TranscriptionResponse, HealthResponse, DeleteResponse

load_dotenv()

# Temporary directory for uploaded audio files
UPLOAD_DIR = Path("/tmp/voxbr")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Supported audio formats
SUPPORTED_FORMATS = {"mp3", "mp4", "wav", "m4a", "ogg", "flac", "webm"}

app = FastAPI(
    title="VoxBR API",
    description="Plataforma de transcrição de áudio com Whisper + resumo com IA",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    storage.init_db()
    logger.info("VoxBR backend started")
    # Pre-load Whisper model in background
    try:
        transcriber.get_whisper_model()
    except Exception as e:
        logger.warning(f"Could not pre-load Whisper model: {e}")


def _process_transcription(record_id: int, file_path: str, language: str) -> None:
    """Background task: transcribe audio and generate summary, then update DB."""
    try:
        logger.info(f"Background processing started | id={record_id} | file={file_path}")

        # Step 1: Transcribe
        result = transcriber.transcribe(file_path, language)
        transcript_text = result["text"]
        duration = result["duration"]

        # Step 2: Summarize
        summary_result = summarizer.summarize(transcript_text, language)
        summary = summary_result["summary"]
        key_points = summary_result["key_points"]

        # Step 3: Update record
        storage.update_record(
            record_id,
            transcript=transcript_text,
            summary=summary,
            key_points=key_points,
            duration_seconds=duration,
            status="done",
        )
        logger.info(f"Background processing done | id={record_id}")

    except Exception as e:
        logger.error(f"Background processing failed | id={record_id} | error={e}")
        storage.update_record(
            record_id,
            status="error",
            error_message=str(e),
        )
    finally:
        # Clean up temporary file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Removed temp file: {file_path}")
        except OSError as oe:
            logger.warning(f"Could not remove temp file {file_path}: {oe}")


@app.post("/transcribe", response_model=TranscriptionResponse, status_code=202)
async def transcribe_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: str = Form(default="pt"),
):
    """
    Upload an audio file for transcription.
    Returns immediately with status='processing'; poll /transcriptions/{id} for updates.
    """
    # Validate file extension
    filename = file.filename or "audio"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported format '{ext}'. Supported: {', '.join(sorted(SUPPORTED_FORMATS))}",
        )

    # Save uploaded file to temp dir
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    temp_path = str(UPLOAD_DIR / unique_name)

    try:
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        logger.info(f"Saved uploaded file to {temp_path} ({len(content)} bytes)")
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # Create DB record
    record = storage.create_record(filename=filename, language=language)
    record_id = record["id"]

    # Queue background processing
    background_tasks.add_task(_process_transcription, record_id, temp_path, language)

    return TranscriptionResponse(
        id=record["id"],
        filename=record["filename"],
        language=record["language"],
        transcript=record["transcript"],
        summary=record["summary"],
        key_points=record["key_points"],
        duration_seconds=record["duration_seconds"],
        created_at=record["created_at"],
        status=record["status"],
    )


@app.get("/transcriptions", response_model=list[TranscriptionResponse])
async def list_transcriptions():
    """Return all transcriptions ordered by date (newest first)."""
    records = storage.get_all()
    return [
        TranscriptionResponse(
            id=r["id"],
            filename=r["filename"],
            language=r["language"],
            transcript=r["transcript"],
            summary=r["summary"],
            key_points=r["key_points"],
            duration_seconds=r["duration_seconds"],
            created_at=r["created_at"],
            status=r["status"],
        )
        for r in records
    ]


@app.get("/transcriptions/{record_id}", response_model=TranscriptionResponse)
async def get_transcription(record_id: int):
    """Return a single transcription by ID."""
    record = storage.get_by_id(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Transcription {record_id} not found")
    return TranscriptionResponse(
        id=record["id"],
        filename=record["filename"],
        language=record["language"],
        transcript=record["transcript"],
        summary=record["summary"],
        key_points=record["key_points"],
        duration_seconds=record["duration_seconds"],
        created_at=record["created_at"],
        status=record["status"],
    )


@app.delete("/transcriptions/{record_id}", response_model=DeleteResponse)
async def delete_transcription(record_id: int):
    """Delete a transcription by ID."""
    deleted = storage.delete_by_id(record_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Transcription {record_id} not found")
    return DeleteResponse(message="Transcription deleted successfully", id=record_id)


@app.get("/transcriptions/{record_id}/export")
async def export_transcription(record_id: int, format: str = "txt"):
    """Export a transcription as plain text."""
    record = storage.get_by_id(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Transcription {record_id} not found")

    if record["status"] != "done":
        raise HTTPException(
            status_code=400,
            detail=f"Transcription is not complete (status: {record['status']})",
        )

    if format not in ("txt",):
        raise HTTPException(status_code=400, detail=f"Unsupported export format: {format}")

    filename_base = Path(record["filename"]).stem
    key_points_text = "\n".join(
        f"  {i + 1}. {point}" for i, point in enumerate(record["key_points"])
    )

    content = (
        f"VoxBR - Transcrição de Áudio\n"
        f"{'=' * 50}\n\n"
        f"Arquivo: {record['filename']}\n"
        f"Idioma: {record['language']}\n"
        f"Duração: {record['duration_seconds']:.1f}s\n"
        f"Data: {record['created_at']}\n\n"
        f"{'=' * 50}\n"
        f"RESUMO\n"
        f"{'=' * 50}\n\n"
        f"{record['summary']}\n\n"
        f"{'=' * 50}\n"
        f"PONTOS PRINCIPAIS\n"
        f"{'=' * 50}\n\n"
        f"{key_points_text}\n\n"
        f"{'=' * 50}\n"
        f"TRANSCRIÇÃO COMPLETA\n"
        f"{'=' * 50}\n\n"
        f"{record['transcript']}\n"
    )

    return PlainTextResponse(
        content=content,
        headers={
            "Content-Disposition": f'attachment; filename="{filename_base}_transcricao.txt"'
        },
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="ok", whisper_model=transcriber.WHISPER_MODEL_SIZE)
