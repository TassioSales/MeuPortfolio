"""
Testes da assinatura do webhook.

Antes desta correção o endpoint aceitava qualquer requisição: quem descobrisse
a URL conseguia injetar mensagens como se viessem do WhatsApp — e cada injeção
vira uma chamada paga ao Claude, além de poluir conversas e leads reais.
"""

import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.utils.webhook_security import SIGNATURE_HEADER, compute_signature

client = TestClient(app)

SEGREDO = "segredo-de-teste"
CORPO = {"event": "connection.update", "data": {}}


def _assinado(corpo: dict, segredo: str = SEGREDO) -> tuple[bytes, dict]:
    body = json.dumps(corpo).encode()
    return body, {SIGNATURE_HEADER: compute_signature(body, segredo)}


@pytest.fixture
def com_segredo(monkeypatch):
    monkeypatch.setattr(settings, "webhook_secret", SEGREDO)
    monkeypatch.setattr(settings, "debug", False)


class TestSignatureVerification:
    def test_accepts_correctly_signed_request(self, com_segredo):
        body, headers = _assinado(CORPO)

        response = client.post(
            "/api/v1/webhook/messages", content=body, headers=headers
        )

        assert response.status_code == 200

    def test_rejects_request_without_signature(self, com_segredo):
        response = client.post("/api/v1/webhook/messages", json=CORPO)

        assert response.status_code == 401

    def test_rejects_wrong_signature(self, com_segredo):
        body, _ = _assinado(CORPO)

        response = client.post(
            "/api/v1/webhook/messages",
            content=body,
            headers={SIGNATURE_HEADER: "sha256=" + "0" * 64},
        )

        assert response.status_code == 401

    def test_rejects_signature_from_another_secret(self, com_segredo):
        body, headers = _assinado(CORPO, segredo="outro-segredo")

        response = client.post(
            "/api/v1/webhook/messages", content=body, headers=headers
        )

        assert response.status_code == 401

    def test_rejects_tampered_body(self, com_segredo):
        """A assinatura é do corpo: alterar um byte tem de invalidar."""
        body, headers = _assinado(CORPO)
        adulterado = body.replace(b"connection.update", b"messages.upsert!")

        response = client.post(
            "/api/v1/webhook/messages", content=adulterado, headers=headers
        )

        assert response.status_code == 401


class TestMissingSecret:
    """Sem segredo configurado o comportamento depende do ambiente."""

    def test_production_refuses_to_run_unprotected(self, monkeypatch):
        monkeypatch.setattr(settings, "webhook_secret", "")
        monkeypatch.setattr(settings, "debug", False)

        response = client.post("/api/v1/webhook/messages", json=CORPO)

        # Falha visível é melhor que aceitar tudo em silêncio.
        assert response.status_code == 503

    def test_debug_allows_unsigned_for_local_development(self, monkeypatch):
        monkeypatch.setattr(settings, "webhook_secret", "")
        monkeypatch.setattr(settings, "debug", True)

        response = client.post("/api/v1/webhook/messages", json=CORPO)

        assert response.status_code == 200


class TestHealthReportsRealState:
    def test_reports_degraded_without_secret(self, monkeypatch):
        monkeypatch.setattr(settings, "webhook_secret", "")

        body = client.get("/api/v1/webhook/health").json()

        # Antes isto dizia "ok" mesmo sem proteção, porque chamava um stub
        # que devolvia True sempre.
        assert body["status"] == "degraded"
        assert body["signature_validation"] == "disabled"

    def test_reports_ok_with_secret(self, monkeypatch):
        monkeypatch.setattr(settings, "webhook_secret", SEGREDO)

        body = client.get("/api/v1/webhook/health").json()

        assert body["status"] == "ok"
        assert body["signature_validation"] == "enabled"


class TestInvalidPayload:
    def test_signed_but_malformed_body_is_422(self, com_segredo):
        body = b"nao e json"
        headers = {SIGNATURE_HEADER: compute_signature(body, SEGREDO)}

        response = client.post(
            "/api/v1/webhook/messages", content=body, headers=headers
        )

        assert response.status_code == 422
