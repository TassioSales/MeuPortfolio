"""
Validação da assinatura do webhook.

Sem isto, quem descobrisse a URL do webhook conseguiria injetar mensagens
como se fossem do WhatsApp — e cada injeção vira uma chamada paga ao Claude,
além de poluir conversas e leads reais.
"""

import hashlib
import hmac
from typing import Optional

from fastapi import HTTPException, status

from app.config import settings
from app.utils.logger import logger

# Cabeçalho onde a Evolution API envia o HMAC do corpo.
SIGNATURE_HEADER = "x-hub-signature-256"


def compute_signature(payload: bytes, secret: str) -> str:
    """HMAC-SHA256 do corpo cru, no formato `sha256=<hex>`."""
    digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def signature_is_valid(payload: bytes, signature: Optional[str], secret: str) -> bool:
    """
    Compare the received signature with the expected one.

    Usa `compare_digest` em vez de `==`: a comparação normal sai mais cedo no
    primeiro byte diferente, e esse tempo vaza quanto do prefixo estava certo.
    """
    if not signature:
        return False
    return hmac.compare_digest(compute_signature(payload, secret), signature)


def verify_webhook_request(payload: bytes, signature: Optional[str]) -> None:
    """
    Reject the request unless it carries a valid signature.

    Sem segredo configurado o endpoint fica aberto, o que serve para
    desenvolvimento — mas em produção (`DEBUG=false`) a requisição é recusada,
    para um deploy que esqueceu de definir `WEBHOOK_SECRET` falhar de forma
    visível em vez de aceitar tudo em silêncio.
    """
    if not settings.webhook_secret:
        if settings.debug:
            logger.warning(
                "⚠️ WEBHOOK_SECRET não definido: webhook aceitando qualquer origem "
                "(tolerado apenas em DEBUG)"
            )
            return

        logger.error("❌ WEBHOOK_SECRET não definido — webhook recusado em produção")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook not configured",
        )

    if not signature_is_valid(payload, signature, settings.webhook_secret):
        logger.warning("⚠️ Webhook com assinatura inválida recusado")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )
