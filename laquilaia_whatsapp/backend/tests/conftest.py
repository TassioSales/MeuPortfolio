"""Pytest configuration and fixtures."""

import pytest
import sys
import os
from pathlib import Path

# Add app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Provide a FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def sample_user_data():
    """Provide sample user data for tests."""
    return {
        "email": "test@example.com",
        "nome": "Test User",
        "senha": "TestPassword123!",
    }


@pytest.fixture
def sample_agent_data():
    """Provide sample agent data for tests."""
    return {
        "nome": "Agent de Vendas",
        "descricao": "Agente especializado em vendas",
        "system_prompt": "Você é um agente de vendas assistente.",
        "temperatura": 0.7,
        "max_tokens": 1024,
    }


@pytest.fixture
def sample_conversation_data():
    """Provide sample conversation data for tests."""
    return {
        "phone_number": "+5561999887234",
        "status": "ativa",
    }
