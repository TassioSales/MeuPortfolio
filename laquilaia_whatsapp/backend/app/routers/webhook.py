"""Webhook routes for Evolution API integration."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.db.database import get_db_session
from app.models.webhook_models import WebhookPayload
from app.services.message_orchestrator import orchestrator
from pydantic import ValidationError
from app.utils.logger import logger
from app.utils.webhook_security import (
    SIGNATURE_HEADER,
    STATIC_TOKEN_HEADER,
    verify_webhook_request,
)
from app.utils.exceptions import NotFoundException, ValidationException
from datetime import datetime

router = APIRouter(
    prefix="/api/v1",
    tags=["webhook"],
)


@router.post("/webhook/messages")
async def webhook_messages(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Receive incoming WhatsApp messages from Evolution API.

    Expected flow:
    1. Evolution API sends message to this endpoint
    2. Extract agent_id, phone, and message text
    3. Process message through orchestrator
    4. Return success response

    Note: This is a simplified implementation.
    In production, you'd need:
    - Signature validation
    - Retry logic with idempotency keys
    - Dead letter queue for failed messages
    - Async task processing
    """
    # A assinatura é conferida sobre o corpo CRU, antes de qualquer parse:
    # validar depois do Pydantic deixaria requisição não assinada mexer no
    # parser, e o HMAC é calculado sobre os bytes exatos que chegaram.
    body = await request.body()
    verify_webhook_request(
        body,
        request.headers.get(SIGNATURE_HEADER),
        request.headers.get(STATIC_TOKEN_HEADER),
    )

    try:
        payload = WebhookPayload.model_validate_json(body)
    except ValidationError as e:
        logger.warning(f"⚠️ Webhook com corpo inválido: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid webhook payload",
        )

    try:
        event_type = payload.event

        # O tipo do evento é checado ANTES de ler campos de mensagem: eventos
        # como connection.update não trazem `key` nem `message`.
        if event_type != "messages.upsert":
            logger.debug(f"⏭️ Ignoring event type: {event_type}")
            return {"status": "ignored", "event": event_type}

        phone = payload.data.key.get("remoteJid", "unknown").replace("@s.whatsapp.net", "")
        message_body = payload.data.message.messageBody or "[non-text message]"

        logger.info(
            f"🔔 Webhook received: event={event_type}, phone={phone}, "
            f"message={message_body[:50]}"
        )

        # Ignore outgoing messages (fromMe=true)
        if payload.data.key.get("fromMe", False):
            logger.debug("⏭️ Ignoring outgoing message")
            return {"status": "ignored", "reason": "outgoing message"}

        # Ignore non-text messages for now
        if payload.data.message.messageType != "textMessage":
            logger.debug(
                f"⏭️ Ignoring non-text message: {payload.data.message.messageType}"
            )
            return {"status": "ignored", "reason": "non-text message"}

        # Extract message content
        message_text = payload.data.message.messageBody
        if not message_text or not message_text.strip():
            logger.warning("⚠️ Empty message body")
            return {"status": "ignored", "reason": "empty message"}

        # Extract phone number from remoteJid
        remote_jid = payload.data.key.get("remoteJid", "")
        phone_number = remote_jid.replace("@s.whatsapp.net", "")

        # Qual agente responde.
        #
        # O `agentId` dentro de `key` é conveniência para teste: a Evolution
        # real nunca o envia — ela não sabe que agentes existem. Sem a queda
        # para a variável de ambiente, plugar a Evolution de verdade dava
        # "Missing agent_id" em toda mensagem recebida.
        #
        # Uma instalação com vários agentes precisa de mapeamento por
        # instância do WhatsApp, que ainda não existe; enquanto isso, uma
        # instância atende por um agente só.
        agent_id = payload.data.key.get("agentId") or settings.evolution_default_agent_id
        if not agent_id:
            logger.error(
                "❌ Sem agente para atender: defina EVOLUTION_DEFAULT_AGENT_ID "
                "ou mande `agentId` em data.key"
            )
            raise ValidationException("Missing agent_id in webhook")

        # Process message
        result = await orchestrator.process_incoming_message(
            agent_id=agent_id,
            phone_number=phone_number,
            message_text=message_text,
            db=db,
        )

        return {
            "status": "success",
            "conversation_id": result["conversation_id"],
            "message_id": result.get("sent_message_id"),
        }

    except NotFoundException as e:
        logger.warning(f"⚠️ Not found: {e.detail}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.detail,
        )
    except ValidationException as e:
        logger.warning(f"⚠️ Validation error: {e.detail}")
        # Return 200 to Evolution API (we processed it, even if error)
        # This prevents retries
        return {
            "status": "error",
            "detail": e.detail,
        }
    # Erros HTTP deliberados (404, 400, 403...) precisam subir intactos:
    # o catch-all abaixo os transformaria em 500.
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        # Return 200 to prevent infinite retries from Evolution API
        return {
            "status": "error",
            "detail": str(e),
        }


@router.get("/webhook/health")
async def webhook_health():
    """
    Health check endpoint for webhooks.

    Returns status of Evolution API connectivity.
    """
    try:
        # Reporta se o webhook está protegido — antes isto chamava um stub que
        # devolvia True sempre, então dizia "ok" mesmo sem proteção nenhuma.
        protegido = bool(settings.webhook_secret)
        return {
            "status": "ok" if protegido else "degraded",
            "signature_validation": "enabled" if protegido else "disabled",
            "detail": None if protegido else "WEBHOOK_SECRET não configurado",
            "timestamp": datetime.utcnow().isoformat(),
        }
    # Erros HTTP deliberados (404, 400, 403...) precisam subir intactos:
    # o catch-all abaixo os transformaria em 500.
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Webhook health check failed: {e}")
        return {
            "status": "error",
            "detail": str(e),
        }


@router.post("/webhook/whatsapp")
async def webhook_whatsapp(request: Request):
    """
    Placeholder endpoint for Evolution API webhooks.

    This is kept for backward compatibility.
    New webhook integration uses /webhook/messages endpoint.
    """
    try:
        body = await request.json()
        logger.info(f"📨 Legacy webhook received: {body.get('event', 'unknown')}")
        return {"status": "ok", "message": "Webhook received"}
    # Erros HTTP deliberados (404, 400, 403...) precisam subir intactos:
    # o catch-all abaixo os transformaria em 500.
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Legacy webhook error: {e}")
        return {"status": "error", "detail": str(e)}
