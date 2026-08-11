"""Message orchestrator for handling WhatsApp messages end-to-end."""

from app.db.models import Agent, Conversation, Message
from app.services.llm_service import llm_service
from app.services.whatsapp_service import whatsapp_service
from app.services.lead_processor import lead_processor
from app.utils.logger import logger
from app.ws.manager import notify_new_message
from app.utils.exceptions import NotFoundException, ValidationException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import Optional, Dict, Any


class MessageOrchestrator:
    """Orchestrates the complete message flow."""

    async def process_incoming_message(
        self,
        agent_id: str,
        phone_number: str,
        message_text: str,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Process incoming WhatsApp message end-to-end.

        Flow:
        1. Find agent by ID
        2. Get or create conversation
        3. Retrieve conversation history
        4. Call Claude LLM
        5. Save user message
        6. Save assistant response
        7. Process lead qualification (if JSON present)
        8. Send reply via WhatsApp
        9. Return result

        Args:
            agent_id: Agent ID
            phone_number: Sender phone number
            message_text: Message content
            db: Database session

        Returns:
            Dict with processing result

        Raises:
            NotFoundException: If agent not found
            ValidationException: If processing fails
        """
        try:
            # Step 1: Verify agent exists
            result = await db.execute(
                select(Agent).where(Agent.id == agent_id)
            )
            agent = result.scalars().first()

            if not agent:
                logger.warning(f"⚠️ Agent not found: {agent_id}")
                raise NotFoundException("Agent")

            logger.info(f"📨 Processing message from {phone_number} for agent {agent_id}")

            # Step 2: Get or create conversation
            conversation = await self._get_or_create_conversation(
                agent_id, phone_number, db
            )

            # Step 3: Get conversation history
            history = await llm_service.get_conversation_history(
                conversation.id, db, limit=5
            )

            # Step 4: Call Claude
            response_text, token_usage = await llm_service.generate_response(
                agent=agent,
                user_message=message_text,
                conversation_history=history,
            )

            # Step 5: Save user message
            user_msg = Message(
                conversation_id=conversation.id,
                remetente="user",
                conteudo=message_text,
                timestamp=datetime.utcnow(),
            )
            db.add(user_msg)

            # Step 6: Save assistant response
            assistant_msg = Message(
                conversation_id=conversation.id,
                remetente="assistant",
                conteudo=response_text,
                timestamp=datetime.utcnow(),
            )
            db.add(assistant_msg)

            # Update conversation timestamp
            conversation.data_ultima_msg = datetime.utcnow()

            await db.commit()

            logger.info(
                f"✅ Messages saved for conversation {conversation.id} "
                f"(tokens: {token_usage['total_tokens']})"
            )

            # Avisa o painel depois do commit — antes dele o evento poderia
            # anunciar uma mensagem que a transação ainda vai desfazer.
            await notify_new_message(agent_id, conversation.id, phone_number)

            # Step 7: Process lead qualification (extract JSON if present)
            lead_result = await lead_processor.process_response(
                response_text=response_text,
                phone_number=phone_number,
                conversation_id=conversation.id,
                agent_id=agent_id,
                db=db,
            )

            if lead_result.get("success"):
                logger.info(f"🎯 Lead qualified: {lead_result.get('lead_id')}")

            # Step 8: Send reply via WhatsApp
            send_result = await whatsapp_service.send_message(
                phone_number=phone_number,
                message_text=response_text,
            )

            logger.info(
                f"✅ Message processing complete for {phone_number}: "
                f"sent_id={send_result.get('message_id')}"
            )

            return {
                "success": True,
                "conversation_id": conversation.id,
                "phone_number": phone_number,
                "response": response_text,
                "tokens_used": token_usage["total_tokens"],
                "sent_message_id": send_result.get("message_id"),
                "lead_qualification": lead_result,
            }

        except NotFoundException as e:
            logger.warning(f"⚠️ {e.detail}")
            raise
        except ValidationException as e:
            logger.warning(f"⚠️ Validation error: {e.detail}")
            await db.rollback()
            raise
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}")
            await db.rollback()
            raise ValidationException(f"Error processing message: {str(e)}")

    async def _get_or_create_conversation(
        self,
        agent_id: str,
        phone_number: str,
        db: AsyncSession,
    ) -> Any:
        """
        Get existing conversation or create new one.

        Args:
            agent_id: Agent ID
            phone_number: Phone number
            db: Database session

        Returns:
            Conversation model instance
        """
        # Try to find existing conversation
        result = await db.execute(
            select(Conversation).where(
                (Conversation.agent_id == agent_id) &
                (Conversation.phone_number == phone_number)
            )
        )
        conversation = result.scalars().first()

        if conversation:
            logger.debug(f"📝 Using existing conversation {conversation.id}")
            return conversation

        # Create new conversation
        logger.debug(f"🆕 Creating new conversation for {phone_number}")
        conversation = Conversation(
            agent_id=agent_id,
            phone_number=phone_number,
            status="ativa",
            # O campo em Conversation chama-se `data_inicio`; `data_criacao`
            # não existe no modelo e fazia toda mensagem recebida falhar.
            data_inicio=datetime.utcnow(),
            data_ultima_msg=datetime.utcnow(),
        )
        db.add(conversation)
        await db.flush()  # Get ID without committing

        logger.info(f"✅ New conversation created: {conversation.id}")
        return conversation

    async def validate_webhook_signature(
        self,
        payload: str,
        signature: Optional[str],
    ) -> bool:
        """
        Validate webhook signature (stub for future implementation).

        In production, validate using Evolution API's signature method.
        For now, returns True to allow testing.

        Args:
            payload: Request body
            signature: X-API-Signature header value

        Returns:
            True if valid, False otherwise
        """
        # TODO: Implement signature validation
        # For MVP, we trust all requests
        logger.debug("⏭️ Webhook signature validation skipped (MVP mode)")
        return True


orchestrator = MessageOrchestrator()
