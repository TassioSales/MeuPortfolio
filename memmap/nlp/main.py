"""
MemMap NLP Service — FastAPI application for entity and relation extraction.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from loguru import logger
from pydantic import BaseModel

from extractor import extract_entities, extract_relations, load_model


class ExtractRequest(BaseModel):
    text: str
    note_id: str


class ExtractResponse(BaseModel):
    entities: list[dict]
    relations: list[dict]


class HealthResponse(BaseModel):
    status: str
    model: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the NLP model at startup."""
    logger.info("Loading NLP model...")
    try:
        _, model_name = load_model()
        logger.info(f"NLP service ready with model: {model_name}")
    except RuntimeError as e:
        logger.error(f"Failed to load NLP model: {e}")
        raise
    yield
    logger.info("NLP service shutting down")


app = FastAPI(
    title="MemMap NLP Service",
    description="Entity and relation extraction for the MemMap knowledge graph",
    version="1.0.0",
    lifespan=lifespan,
)


@app.post("/extract", response_model=ExtractResponse)
async def extract(request: ExtractRequest) -> ExtractResponse:
    """
    Extract entities and relations from text.

    Body: {"text": str, "note_id": str}
    Response: {"entities": [...], "relations": [...]}
    """
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    logger.info(
        f"Extracting from note_id={request.note_id}, text_length={len(request.text)}"
    )

    try:
        entities = extract_entities(request.text)
        relations = extract_relations(request.text, entities)
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

    return ExtractResponse(entities=entities, relations=relations)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    try:
        _, model_name = load_model()
        return HealthResponse(status="ok", model=model_name)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
