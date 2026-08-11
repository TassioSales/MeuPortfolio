"""Tests for main FastAPI application."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "L'Aquila AI" in data["message"]


def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "laquilaia-backend"
    assert data["version"] == "0.1.0"


def test_docs_available():
    """Test that Swagger docs are available."""
    response = client.get("/docs")
    assert response.status_code == 200


def test_redoc_available():
    """Test that ReDoc is available."""
    response = client.get("/redoc")
    assert response.status_code == 200


def test_openapi_schema():
    """Test that OpenAPI schema is available."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert data["info"]["title"] == "L'Aquila AI - WhatsApp Clone"
