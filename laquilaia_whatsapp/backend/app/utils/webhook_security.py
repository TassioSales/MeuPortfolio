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

# Cabeçalho do HMAC do corpo.
SIGNATURE_HEADER = "x-hub-signature-256"

# Cabeçalho do token estático, usado quando o emissor não sabe assinar.
#
# A Evolution API não calcula HMAC: ela só repassa cabeçalhos fixos que você
# configura na instância. Ou seja, o esquema de assinatura acima — desenhado
# supondo um emissor que assina — recusaria **toda** mensagem vinda dela.
#
# O token estático é mais fraco de propósito, e a diferença importa: ele prova
# que quem chamou conhece o segredo, mas não que o corpo chegou íntegro nem
# que a requisição não é uma repetição de outra capturada antes. Por isso vive
# em variável própria: quem usa HMAC não perde nada, e quem liga o modo
# estático faz uma escolha consciente.
STATIC_TOKEN_HEADER = "x-webhook-token"


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


def static_token_is_valid(token: Optional[str]) -> bool:
    """Se o token estático confere com o configurado.

    Devolve False quando o modo não está ligado, para que a ausência de
    configuração nunca vire uma autorização.
    """
    esperado = settings.webhook_static_token
    if not esperado or not token:
        return False
    return hmac.compare_digest(esperado, token)


def verify_webhook_request(
    payload: bytes,
    signature: Optional[str],
    static_token: Optional[str] = None,
) -> None:
    """
    Reject the request unless it carries a valid signature.

    Aceita dois modos: o HMAC do corpo, e — se `WEBHOOK_STATIC_TOKEN` estiver
    definido — um token fixo em cabeçalho, para emissores que não assinam,
    como a Evolution API.

    Sem segredo configurado o endpoint fica aberto, o que serve para
    desenvolvimento — mas em produção (`DEBUG=false`) a requisição é recusada,
    para um deploy que esqueceu de definir `WEBHOOK_SECRET` falhar de forma
    visível em vez de aceitar tudo em silêncio.
    """
    if static_token_is_valid(static_token):
        return

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
