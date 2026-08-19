"""Chat and LLM interaction routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db_session
from app.models.caso_schemas import CasoDoContato
from app.models.llm_models import (
    MessageRequest,
    MessageResponse,
    TokenUsage,
    ChatHistoryMessage,
    ChatHistoryResponse,
)
from app.db.models import LeadTimeline, Agent, Caso, Conversation, Lead, LeadDetails, Message
from app.services.llm_service import llm_service
from app.services.whatsapp_service import whatsapp_service
from app.ws.manager import notify_new_message
from app.utils.auth_middleware import get_current_user, require_admin
from app.utils.exceptions import ValidationException, NotFoundException
from app.utils.logger import logger
from sqlalchemy import select
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

router = APIRouter(
    prefix="/api/v1/agents",
    tags=["chat"],
)

# Telefone usado pelas conversas criadas pelo playground, para distingui-las
# das conversas reais vindas do WhatsApp.
TEST_PHONE_NUMBER = "test_api"


async def _get_agent_or_404(agent_id: str, db: AsyncSession) -> Agent:
    """
    O agente do escritório, ou 404.

    Sem filtro por dono: esta instalação atende um escritório só e ninguém se
    cadastra sozinho nela, então o filtro nunca barrou estranho — barrava o
    operador que o próprio administrador criou. Quem pode **mexer** no agente
    é decidido pelo papel, em `require_admin`, na rota.
    """
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalars().first()

    if not agent:
        logger.warning(f"⚠️ Agent not found: {agent_id}")
        raise NotFoundException("Agent")

    return agent


async def _find_test_conversation(agent_id: str, db: AsyncSession) -> Conversation | None:
    """Return the playground conversation of an agent, if it already exists."""
    result = await db.execute(
        select(Conversation).where(
            (Conversation.agent_id == agent_id)
            & (Conversation.phone_number == TEST_PHONE_NUMBER)
        )
    )
    return result.scalars().first()


async def _get_or_create_test_conversation(
    agent_id: str, db: AsyncSession
) -> Conversation:
    """Reuse the agent's playground conversation, creating it on first use."""
    conversation = await _find_test_conversation(agent_id, db)

    if conversation is None:
        conversation = Conversation(
            agent_id=agent_id,
            phone_number=TEST_PHONE_NUMBER,
            status="ativa",
        )
        db.add(conversation)
        await db.flush()  # Get conversation ID without committing

    return conversation


@router.post("/{agent_id}/chat", response_model=MessageResponse)
async def chat_with_agent(
    agent_id: str,
    request: MessageRequest,
    user_id: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Chat with an agent and get AI-generated response.

    This endpoint:
    1. Verifies agent ownership
    2. Retrieves or creates conversation
    3. Gets conversation history for context
    4. Calls Claude with agent's system prompt
    5. Saves conversation and returns response
    """
    try:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalars().first()

        if not agent:
            logger.warning(f"⚠️ Agent not found: {agent_id}")
            raise NotFoundException("Agent")

        # Get or create conversation
        conversation_id = request.conversation_id
        if conversation_id:
            result = await db.execute(
                select(Conversation).where(
                    (Conversation.id == conversation_id) &
                    (Conversation.agent_id == agent_id)
                )
            )
            conversation = result.scalars().first()
            if not conversation:
                raise NotFoundException("Conversation")
        else:
            # A conversa de teste é reaproveitada, não recriada: existe uma
            # constraint única (agent_id, phone_number) e o telefone aqui é
            # fixo, então um segundo INSERT com o mesmo agente estouraria.
            conversation = await _get_or_create_test_conversation(agent_id, db)

        # Get conversation history for context
        history = await llm_service.get_conversation_history(
            conversation.id, db, limit=5
        )

        # Generate response from Claude
        response_text, token_usage = await llm_service.generate_response(
            agent=agent,
            user_message=request.message,
            conversation_history=history,
        )

        # Save user message
        user_msg = Message(
            conversation_id=conversation.id,
            remetente="user",
            conteudo=request.message,
            timestamp=datetime.utcnow(),
        )
        db.add(user_msg)

        # Save assistant response
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
            f"✅ Chat message processed: agent={agent_id}, "
            f"conversation={conversation.id}, tokens={token_usage['total_tokens']}"
        )

        return MessageResponse(
            response=response_text,
            conversation_id=conversation.id,
            tokens_used=TokenUsage(
                input_tokens=token_usage["input_tokens"],
                output_tokens=token_usage["output_tokens"],
                total_tokens=token_usage["total_tokens"],
            ),
            timestamp=datetime.utcnow(),
            model=token_usage.get("model", llm_service.model),
        )

    except NotFoundException as e:
        logger.warning(f"⚠️ {e.detail}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.detail,
        )
    except ValidationException as e:
        logger.warning(f"⚠️ Validation error: {e.detail}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.detail,
        )
    # Erros HTTP deliberados (404, 400, 403...) precisam subir intactos:
    # o catch-all abaixo os transformaria em 500.
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in chat: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing chat message",
        )


@router.get("/{agent_id}/chat/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    agent_id: str,
    _admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """Return the playground conversation history, oldest message first."""
    try:
        await _get_agent_or_404(agent_id, db)

        conversation = await _find_test_conversation(agent_id, db)
        if conversation is None:
            # Agente que ainda não foi testado: histórico vazio, não é erro.
            return ChatHistoryResponse(conversation_id=None, messages=[])

        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.timestamp)
        )

        return ChatHistoryResponse(
            conversation_id=conversation.id,
            messages=[
                ChatHistoryMessage(
                    id=message.id,
                    remetente=message.remetente,
                    conteudo=message.conteudo,
                    timestamp=message.timestamp,
                )
                for message in result.scalars().all()
            ],
        )

    except NotFoundException as e:
        logger.warning(f"⚠️ {e.detail}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting chat history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting chat history",
        )


@router.delete("/{agent_id}/chat/history", status_code=status.HTTP_200_OK)
async def reset_chat_history(
    agent_id: str,
    _admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Clear the playground conversation.

    Apaga as mensagens e a própria conversa: como o telefone de teste é fixo,
    manter a conversa vazia serviria só para ocupar a constraint única.
    """
    try:
        await _get_agent_or_404(agent_id, db)

        conversation = await _find_test_conversation(agent_id, db)
        if conversation is None:
            return {"detail": "No test conversation to reset", "deleted": 0}

        result = await db.execute(
            select(Message).where(Message.conversation_id == conversation.id)
        )
        messages = result.scalars().all()
        for message in messages:
            await db.delete(message)

        await db.delete(conversation)
        await db.commit()

        logger.info(f"🧹 Playground conversation reset: agent={agent_id}")
        return {"detail": "Test conversation reset", "deleted": len(messages)}

    except NotFoundException as e:
        logger.warning(f"⚠️ {e.detail}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error resetting chat history: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error resetting chat history",
        )


@router.post("/{agent_id}/test", response_model=MessageResponse)
async def test_agent(
    agent_id: str,
    request: MessageRequest,
    user_id: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Quick test endpoint for agent without saving conversation.

    Useful for:
    - Testing agent prompts before deployment
    - Verifying system prompt behavior
    - Development and debugging
    - Does NOT save conversation history
    """
    try:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalars().first()

        if not agent:
            logger.warning(f"⚠️ Agent not found: {agent_id}")
            raise NotFoundException("Agent")

        # Generate response without conversation history
        response_text, token_usage = await llm_service.generate_response(
            agent=agent,
            user_message=request.message,
            conversation_history=None,  # No history for test
        )

        logger.info(
            f"✅ Agent test: agent={agent_id}, tokens={token_usage['total_tokens']}"
        )

        return MessageResponse(
            response=response_text,
            tokens_used=TokenUsage(
                input_tokens=token_usage["input_tokens"],
                output_tokens=token_usage["output_tokens"],
                total_tokens=token_usage["total_tokens"],
            ),
            timestamp=datetime.utcnow(),
            model=token_usage.get("model", llm_service.model),
        )

    except NotFoundException as e:
        logger.warning(f"⚠️ {e.detail}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.detail,
        )
    except ValidationException as e:
        logger.warning(f"⚠️ Validation error: {e.detail}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.detail,
        )
    # Erros HTTP deliberados (404, 400, 403...) precisam subir intactos:
    # o catch-all abaixo os transformaria em 500.
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in agent test: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error testing agent",
        )


@router.get("/{agent_id}/rate-limit-status")
async def get_rate_limit_status(
    agent_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get current rate limit status for LLM API.

    Returns:
    - calls_used: Number of API calls in last minute
    - calls_limit: Maximum calls per minute
    - tokens_used: Tokens used in last minute
    - tokens_limit: Maximum tokens per minute
    - calls_remaining: Calls left in current window
    - tokens_remaining: Tokens left in current window
    """
    try:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalars().first()

        if not agent:
            raise NotFoundException("Agent")

        # Com o user_id, e não sem: sem ele a resposta vinha do balde
        # compartilhado e mostrava sempre zero, qualquer que fosse o uso da
        # conta — o limite é por conta desde que deixou de ser do processo.
        return await llm_service.get_rate_limit_status(user_id)

    except NotFoundException as e:
        logger.warning(f"⚠️ {e.detail}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.detail,
        )
    # Erros HTTP deliberados (404, 400, 403...) precisam subir intactos:
    # o catch-all abaixo os transformaria em 500.
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting rate limit status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving rate limit status",
        )


# ========== PAUSA HUMANA (Fase 16) ==========
#
# Router próprio: o `router` deste módulo tem prefixo /api/v1/agents, o que
# faria a URL virar /agents/conversations/... — a conversa não é subrecurso
# do agente nesta operação.

conversations_router = APIRouter(
    prefix="/api/v1/conversations",
    tags=["conversations"],
)

class ConversationStatusResponse(BaseModel):
    """Estado de automação de uma conversa."""
    conversation_id: str
    status: str
    ia_ativa: bool


class ConversationListItem(BaseModel):
    """Uma conversa na lista do operador."""
    id: str
    phone_number: str
    status: str
    ia_ativa: bool
    lead_nome: Optional[str] = None
    lead_status_funil: Optional[str] = None
    data_ultima_msg: Optional[datetime] = None
    total_mensagens: int = 0
    ultima_mensagem: Optional[str] = None
    ultimo_remetente: Optional[str] = None


class ConversationMessagesResponse(BaseModel):
    """Transcrição de uma conversa, da mais antiga para a mais recente."""
    conversation_id: str
    status: str
    ia_ativa: bool
    phone_number: str
    lead_nome: Optional[str] = None
    # Parecer preliminar em markdown, quando houver. É interno: o cliente
    # nunca o recebe, e esta rota exige token e escopo do dono do agente.
    analise_preliminar: Optional[str] = None
    # Os assuntos deste contato, do mais recente para o mais antigo. Um
    # contato pode trazer mais de um, e um deles pode ser de terceiro.
    casos: List[CasoDoContato] = []
    messages: List[ChatHistoryMessage] = []


@router.get("/{agent_id}/conversations", response_model=List[ConversationListItem])
async def list_agent_conversations(
    agent_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Conversas reais do agente, da mais recente para a mais antiga.

    Sem esta listagem os endpoints de pausa eram inalcançáveis pelo painel: os
    três recebem um `conversation_id` que o operador não tinha por onde
    descobrir.

    A conversa do playground fica de fora — ela é do desenvolvedor testando o
    prompt, não de um cliente esperando atendimento.
    """
    try:
        await _get_agent_or_404(agent_id, db)

        result = await db.execute(
            select(Conversation)
            .where(
                (Conversation.agent_id == agent_id)
                & (Conversation.phone_number != TEST_PHONE_NUMBER)
            )
            .order_by(Conversation.data_ultima_msg.desc())
        )
        conversations = result.scalars().all()

        if not conversations:
            return []

        ids = [c.id for c in conversations]

        # As mensagens de todas as conversas de uma vez: uma query por conversa
        # transformaria uma lista de 50 atendimentos em 50 idas ao banco.
        mensagens_result = await db.execute(
            select(Message)
            .where(Message.conversation_id.in_(ids))
            .order_by(Message.timestamp)
        )
        por_conversa: dict[str, list[Message]] = {}
        for mensagem in mensagens_result.scalars().all():
            por_conversa.setdefault(mensagem.conversation_id, []).append(mensagem)

        leads_result = await db.execute(select(Lead).where(Lead.conversation_id.in_(ids)))
        leads = {lead.conversation_id: lead for lead in leads_result.scalars().all()}

        itens = []
        for conversation in conversations:
            mensagens = por_conversa.get(conversation.id, [])
            ultima = mensagens[-1] if mensagens else None
            lead = leads.get(conversation.id)

            itens.append(
                ConversationListItem(
                    id=conversation.id,
                    phone_number=conversation.phone_number,
                    status=conversation.status,
                    ia_ativa=conversation.status != "pausada",
                    lead_nome=lead.nome if lead else None,
                    lead_status_funil=lead.status_funil if lead else None,
                    data_ultima_msg=conversation.data_ultima_msg,
                    total_mensagens=len(mensagens),
                    ultima_mensagem=ultima.conteudo if ultima else None,
                    ultimo_remetente=ultima.remetente if ultima else None,
                )
            )

        return itens

    except NotFoundException as e:
        logger.warning(f"⚠️ {e.detail}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao listar conversas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listing conversations",
        )


async def _get_conversa_ou_404(conversation_id: str, db: AsyncSession) -> Conversation:
    """
    A conversa pelo id.

    Atender é justamente o trabalho do operador: ler a transcrição, assumir a
    conversa e responder ao cliente. Filtrar por dono do agente tirava dele
    exatamente isso — e não protegia ninguém, porque toda conta desta
    instalação foi criada pelo administrador do mesmo escritório.
    """
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalars().first()

    if not conversation:
        raise NotFoundException("Conversation")

    return conversation


async def _set_conversation_status(
    conversation_id: str, user_id: str, novo_status: str, db: AsyncSession
) -> ConversationStatusResponse:
    conversation = await _get_conversa_ou_404(conversation_id, db)
    anterior = conversation.status
    conversation.status = novo_status

    # Assumir e devolver a conversa entram na trilha do lead.
    #
    # Era o buraco maior do histórico: quem lia a transcrição via a IA parar
    # de responder no meio e não tinha como saber quem tinha assumido, nem
    # quando. Num escritório com plantão isso é a pergunta que se faz primeiro.
    lead = (
        await db.execute(select(Lead).where(Lead.conversation_id == conversation_id))
    ).scalars().first()
    if lead is not None and anterior != novo_status:
        db.add(
            LeadTimeline(
                lead_id=lead.id,
                status_anterior=lead.status_funil,
                status_novo=lead.status_funil,
                mudado_por=user_id,
                motivo=(
                    "Humano assumiu a conversa"
                    if novo_status == "pausada"
                    else "Conversa devolvida para a IA"
                ),
                timestamp=datetime.utcnow(),
            )
        )

    await db.commit()

    # Quem assumiu vai no log: agora que a fila é do escritório inteiro,
    # "a IA parou de responder" sem dizer por ordem de quem é meia informação.
    logger.info(f"🔄 Conversa {conversation_id} agora está '{novo_status}' (por {user_id})")
    return ConversationStatusResponse(
        conversation_id=conversation.id,
        status=novo_status,
        ia_ativa=novo_status != "pausada",
    )


@conversations_router.get(
    "/{conversation_id}/messages",
    response_model=ConversationMessagesResponse,
)
async def get_conversation_messages(
    conversation_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Transcrição da conversa, da mensagem mais antiga para a mais recente.

    O operador precisa ler o que já foi dito antes de assumir; pausar às cegas
    faria o humano repetir o que a IA acabou de perguntar.

    O estado da automação vem junto para a tela não precisar de uma segunda
    chamada só para saber se o botão mostra "pausar" ou "retomar".
    """
    try:
        conversation = await _get_conversa_ou_404(conversation_id, db)

        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.timestamp)
        )

        lead_result = await db.execute(
            select(Lead).where(Lead.conversation_id == conversation.id)
        )
        lead = lead_result.scalars().first()

        parecer = None
        casos: List[CasoDoContato] = []
        if lead is not None:
            detalhes_result = await db.execute(
                select(LeadDetails).where(LeadDetails.lead_id == lead.id)
            )
            detalhes = detalhes_result.scalars().first()
            parecer = detalhes.analise_preliminar if detalhes else None

            casos_result = await db.execute(
                select(Caso)
                .where(Caso.lead_id == lead.id)
                .order_by(Caso.data_abertura.desc())
            )
            casos = [
                CasoDoContato(
                    id=caso.id,
                    area=caso.area,
                    resumo=caso.resumo,
                    titular=caso.titular,
                    score_qualificacao=caso.score_qualificacao or 0,
                    valor_estimado_min=caso.valor_estimado_min,
                    valor_estimado_max=caso.valor_estimado_max,
                    viabilidade=caso.viabilidade or "indeterminado",
                    data_abertura=caso.data_abertura,
                    analise_preliminar=caso.analise_preliminar,
                )
                for caso in casos_result.scalars().all()
            ]

        return ConversationMessagesResponse(
            conversation_id=conversation.id,
            status=conversation.status,
            ia_ativa=conversation.status != "pausada",
            phone_number=conversation.phone_number,
            lead_nome=lead.nome if lead else None,
            analise_preliminar=parecer,
            casos=casos,
            messages=[
                ChatHistoryMessage(
                    id=message.id,
                    remetente=message.remetente,
                    conteudo=message.conteudo,
                    timestamp=message.timestamp,
                )
                for message in result.scalars().all()
            ],
        )

    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao buscar mensagens da conversa: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting conversation messages",
        )


@conversations_router.post(
    "/{conversation_id}/pause",
    response_model=ConversationStatusResponse,
)
async def pause_conversation(
    conversation_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Hand the conversation over to a human.

    As mensagens do cliente continuam sendo registradas; a IA é que para de
    responder, para operador e agente não falarem juntos com o cliente.
    """
    try:
        return await _set_conversation_status(conversation_id, user_id, "pausada", db)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao pausar conversa: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error pausing conversation",
        )


@conversations_router.post(
    "/{conversation_id}/resume",
    response_model=ConversationStatusResponse,
)
async def resume_conversation(
    conversation_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Give the conversation back to the AI."""
    try:
        return await _set_conversation_status(conversation_id, user_id, "ativa", db)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao retomar conversa: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error resuming conversation",
        )


class MensagemDoOperador(BaseModel):
    """O que o operador digitou para mandar ao cliente."""

    conteudo: str = Field(..., min_length=1, max_length=4096)


@conversations_router.post(
    "/{conversation_id}/mensagens",
    response_model=ChatHistoryMessage,
    status_code=status.HTTP_201_CREATED,
)
async def responder_como_operador(
    conversation_id: str,
    corpo: MensagemDoOperador,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    O operador escreve ao cliente, pelo painel.

    Antes disto, assumir a conversa parava a IA e mais nada: para responder, a
    pessoa abria o WhatsApp no celular, e a mensagem que ela mandava nunca
    entrava na transcrição. Quem lesse o atendimento depois via a conversa com
    um buraco.

    **Só com a conversa pausada.** Com a IA ativa, os dois responderiam ao
    mesmo tempo à mesma pergunta — e o cliente receberia duas versões da mesma
    resposta, que é pior que demorar. Daí o 409: não é erro de digitação, é o
    operador tentando falar por cima do agente.

    O envio vem antes do commit de propósito: gravar uma mensagem que a
    Evolution recusou faria a transcrição mentir para quem a lê.
    """
    try:
        conversa = await _get_conversa_ou_404(conversation_id, db)

        if conversa.status != "pausada":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Assuma a conversa antes de responder: a IA ainda está ativa.",
            )

        envio = await whatsapp_service.send_message(
            phone_number=conversa.phone_number,
            message_text=corpo.conteudo,
        )
        if not envio.get("success"):
            raise ValidationException("A Evolution não confirmou o envio.")

        mensagem = Message(
            conversation_id=conversa.id,
            # Nem "user" nem "assistant": quem escreveu foi gente do
            # escritório. O histórico do modelo trata tudo que não é "user"
            # como o escritório falando, então isto entra no lugar certo sem
            # virar pergunta do cliente.
            remetente="operador",
            conteudo=corpo.conteudo,
            timestamp=datetime.utcnow(),
        )
        db.add(mensagem)
        conversa.data_ultima_msg = datetime.utcnow()
        await db.commit()
        await db.refresh(mensagem)

        await notify_new_message(conversa.agent_id, conversa.id, conversa.phone_number)

        logger.info(f"🧑 Operador respondeu na conversa {conversa.id}")
        return ChatHistoryMessage(
            id=mensagem.id,
            remetente=mensagem.remetente,
            conteudo=mensagem.conteudo,
            timestamp=mensagem.timestamp,
        )

    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except ValidationException as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Não foi possível enviar pelo WhatsApp: {e.detail}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao responder como operador: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error sending operator message",
        )


@conversations_router.get(
    "/{conversation_id}/status",
    response_model=ConversationStatusResponse,
)
async def get_conversation_status(
    conversation_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Whether the AI is answering this conversation."""
    try:
        conversation = await _get_conversa_ou_404(conversation_id, db)
        return ConversationStatusResponse(
            conversation_id=conversation.id,
            status=conversation.status,
            ia_ativa=conversation.status != "pausada",
        )
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao consultar conversa: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting conversation status",
        )
