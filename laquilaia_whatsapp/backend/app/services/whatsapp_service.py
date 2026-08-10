"""WhatsApp service for Evolution API integration."""

from app.config import settings
from app.utils.logger import logger
from app.utils.exceptions import ValidationException
import httpx
from typing import Optional, Dict, Any


class WhatsAppService:
    """Service for sending messages via Evolution API."""

    def __init__(self):
        """Initialize WhatsApp service."""
        self.api_url = settings.evolution_api_url
        self.api_key = settings.evolution_api_key
        self.instance_name = settings.evolution_instance_name
        self.timeout = 30

    async def send_message(
        self,
        phone_number: str,
        message_text: str,
        quoted_message_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send message via WhatsApp using Evolution API.

        Args:
            phone_number: Phone number (with or without +55)
            message_text: Message content
            quoted_message_id: Optional message ID to quote

        Returns:
            Dict with success status and message ID

        Raises:
            ValidationException: If API call fails
        """
        try:
            # Clean phone number (remove +55 if present)
            clean_phone = phone_number.replace("+", "").replace(" ", "")
            if clean_phone.startswith("55"):
                clean_phone = clean_phone[2:]

            # Build payload
            payload = {
                "number": clean_phone,
                "textMessage": message_text,
            }

            if quoted_message_id:
                payload["quotedMessageId"] = quoted_message_id

            # Build URL
            url = (
                f"{self.api_url}/message/sendText/{self.instance_name}"
            )

            # Headers
            headers = {
                "apikey": self.api_key,
                "Content-Type": "application/json",
            }

            # Send request
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)

            # Check response
            if response.status_code in [200, 201]:
                data = response.json()
                logger.info(
                    f"✅ WhatsApp message sent to {clean_phone} "
                    f"(message_id: {data.get('messageId', 'N/A')})"
                )
                return {
                    "success": True,
                    "message_id": data.get("messageId"),
                    "phone": clean_phone,
                }
            else:
                logger.error(
                    f"❌ Failed to send WhatsApp message: {response.status_code} "
                    f"- {response.text}"
                )
                raise ValidationException(
                    f"Failed to send message: {response.status_code}"
                )

        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"❌ Error sending WhatsApp message: {e}")
            raise ValidationException(f"Error sending message: {str(e)}")

    async def health_check(self) -> bool:
        """
        Check Evolution API health.

        Returns:
            True if API is accessible, False otherwise
        """
        try:
            url = f"{self.api_url}/instance/info/{self.instance_name}"
            headers = {"apikey": self.api_key}

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)

            is_healthy = response.status_code in [200, 401]  # 401 also means API is up
            logger.info(f"🔍 Evolution API health: {'✅ OK' if is_healthy else '❌ Down'}")
            return is_healthy

        except Exception as e:
            logger.error(f"❌ Evolution API health check failed: {e}")
            return False


whatsapp_service = WhatsAppService()
