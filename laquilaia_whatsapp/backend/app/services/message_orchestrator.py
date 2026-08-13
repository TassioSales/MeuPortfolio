"""Message orchestrator for handling WhatsApp messages end-to-end."""

from app.db.models import Agent, Conversation, Message
from app.services.llm_service import llm_service
from app.services.whatsapp_service import whatsapp_service
from app.services.lead_processor import lead_processor
from app.services.atendimento_context import (
    MENSAGENS_DE_CONTEXTO,
    com_nota,
    nota_de_atendimento_anterior,
)
from app.utils.logger import logger
from app.ws.manager import notify_new_message
from app.utils.exceptions import NotFoundException, ValidationException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import Optional, Dict, Any


class MessageOrchestrator:
    """Orchestrates the complete message flow."""

    # O que fica na transcrição quando o cliente manda um arquivo.
    #
    # O texto entra na conversa e no histórico do modelo; o arquivo em si não
    # fica guardado. Assim o advogado que abre o atendimento vê que houve um
    # documento, e a conversa não tem buraco.
    DESCRICAO_DO_ANEXO = {
        "imagem": "[o cliente enviou uma imagem]",
        "documento": "[o cliente enviou um documento]",
        "audio": "[o cliente enviou um áudio]",
    }

    # Quando o agente não lê anexos, é isto que ele responde. Dizer o que
    # fazer é melhor que ignorar em silêncio — a pessoa fica esperando.
    PEDIDO_DE_TEXTO = {
        "imagem": "Não consigo abrir imagens por aqui. Pode me contar por escrito o que aparece nela?",
        "documento": "Não consigo abrir documentos por aqui. Pode me contar por escrito o que ele diz?",
        "audio": "Não consigo ouvir áudios por aqui. Pode me escrever o que você falou?",
    }

    async def _preparar_anexo(
        self,
        agent,
        tipo_de_anexo: Optional[str],
        chave: Optional[dict],
        message_text: str,
    ):
        """
        Baixa o anexo, se o agente estiver configurado para lê-los.

        Devolve `(anexo, texto)` — e o texto muda mesmo quando o anexo não vem:
        sem ele o modelo receberia uma mensagem vazia e responderia no vácuo.

        Anexo que não baixou não derruba o atendimento: vira uma conversa sem
        anexo, com a descrição no lugar. Perder a foto é ruim; perder o
        atendimento por causa da foto é pior.
        """
        if not tipo_de_anexo:
            return None, message_text

        descricao = self.DESCRICAO_DO_ANEXO.get(tipo_de_anexo, "[anexo]")
        texto = f"{descricao} {message_text}".strip() if message_text else descricao

        if not getattr(agent, "anexos_habilitados", False):
            logger.info(f"📎 Anexo ignorado: o agente {agent.id} não lê anexos")
            return None, f"{texto}\n\n{self.PEDIDO_DE_TEXTO.get(tipo_de_anexo, '')}".strip()

        if not chave:
            return None, texto

        midia = await whatsapp_service.baixar_midia(chave)
        if not midia:
            logger.warning("⚠️ Anexo não baixou; seguindo sem ele")
            return None, texto

        logger.info(
            f"📎 Anexo lido: {midia['mimetype']} "
            f"({midia.get('tamanho') or '?'} bytes)"
        )
        return midia, texto

    async def process_incoming_message(
        self,
        agent_id: str,
        phone_number: str,
        message_text: str,
        db: AsyncSession,
        tipo_de_anexo: Optional[str] = None,
        chave_da_mensagem: Optional[dict] = None,
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

            # Conversa assumida por um humano: a mensagem é registrada, mas a
            # IA não responde. Sem esta checagem o agente responderia por cima
            # do operador, com os dois falando ao mesmo tempo com o cliente.
            if conversation.status == "pausada":
                user_msg = Message(
                    conversation_id=conversation.id,
                    remetente="user",
                    conteudo=message_text,
                    timestamp=datetime.utcnow(),
                )
                db.add(user_msg)
                conversation.data_ultima_msg = datetime.utcnow()
                await db.commit()

                await notify_new_message(agent_id, conversation.id, phone_number)
                logger.info(
                    f"⏸️ Conversa {conversation.id} pausada — mensagem salva sem resposta da IA"
                )
                return {
                    "success": True,
                    "paused": True,
                    "conversation_id": conversation.id,
                    "phone_number": phone_number,
                    "response": None,
                }

            # Step 3: Get conversation history
            history = await llm_service.get_conversation_history(
                conversation.id, db, limit=MENSAGENS_DE_CONTEXTO
            )

            # Quem já foi atendido não pode ouvir "seu caso é sobre o quê?"
            # de novo. A nota conta ao agente o que o banco sabe deste número
            # e que ele não deve recomeçar a triagem.
            nota = await nota_de_atendimento_anterior(phone_number, conversation.id, db)
            history = com_nota(history, nota)

            # O anexo, quando o agente estiver configurado para ler.
            anexo, message_text = await self._preparar_anexo(
                agent, tipo_de_anexo, chave_da_mensagem, message_text
            )

            # Step 4: Call Claude
            response_text, token_usage = await llm_service.generate_response(
                agent=agent,
                user_message=message_text,
                conversation_history=history,
                anexo=anexo,
            )

            # Step 5: Save user message
            user_msg = Message(
                conversation_id=conversation.id,
                remetente="user",
                conteudo=message_text,
                timestamp=datetime.utcnow(),
            )
            db.add(user_msg)

            # O bloco de qualificação é para o CRM, não para o cliente: sai do
            # texto antes de ser gravado e enviado. O `response_text` cru
            # segue para o lead_processor, que precisa do JSON.
            texto_para_o_cliente = lead_processor.texto_para_o_cliente(response_text)

            # Step 6: Save assistant response
            assistant_msg = Message(
                conversation_id=conversation.id,
                remetente="assistant",
                conteudo=texto_para_o_cliente,
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

            # Step 7: Send reply via WhatsApp
            #
            # Antes do processamento do lead, e não depois: a qualificação
            # dispara o parecer jurídico, que é uma segunda chamada ao modelo e
            # leva o tempo que um parecer leva — 2 minutos no Opus 5, medido.
            # Com a ordem invertida, o cliente ficava esperando por um texto
            # que ele nunca vai ler, no exato momento em que a triagem fecha e
            # ele espera um "pronto, o advogado te procura".
            send_result = await whatsapp_service.send_message(
                phone_number=phone_number,
                message_text=texto_para_o_cliente,
            )

            # Step 8: Process lead qualification (extract JSON if present)
            lead_result = await lead_processor.process_response(
                response_text=response_text,
                phone_number=phone_number,
                conversation_id=conversation.id,
                agent_id=agent_id,
                db=db,
            )

            if lead_result.get("success"):
                logger.info(f"🎯 Lead qualified: {lead_result.get('lead_id')}")

            logger.info(
                f"✅ Message processing complete for {phone_number}: "
                f"sent_id={send_result.get('message_id')}"
            )

            return {
                "success": True,
                "conversation_id": conversation.id,
                "phone_number": phone_number,
                "response": texto_para_o_cliente,
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

    # `validate_webhook_signature` foi removido: era um stub que devolvia
    # True sempre, dando a impressão de que havia validação. A conferência
    # real vive em `app/utils/webhook_security.py`.

orchestrator = MessageOrchestrator()
