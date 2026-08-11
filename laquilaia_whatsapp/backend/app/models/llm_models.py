"""Pydantic models for LLM service."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class MessageRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str = Field(..., min_length=1, max_length=4000, description="User message")
    conversation_id: Optional[str] = Field(None, description="Optional conversation ID for context")


class TokenUsage(BaseModel):
    """Token usage statistics."""
    input_tokens: int
    output_tokens: int
    total_tokens: int


class MessageResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str = Field(..., description="Claude response")
    # Sem devolver o id, o cliente não consegue continuar a mesma conversa e
    # cada mensagem começaria um contexto novo. É opcional porque o endpoint
    # /test é stateless de propósito e não cria conversa.
    conversation_id: Optional[str] = Field(
        None, description="Conversation this message belongs to"
    )
    tokens_used: TokenUsage
    timestamp: datetime
    model: str = Field(..., description="Model used")


class ChatHistoryMessage(BaseModel):
    """One message of a conversation, as returned by the history endpoint."""
    id: str
    remetente: str  # "user" ou "assistant"
    conteudo: str
    timestamp: datetime


class ChatHistoryResponse(BaseModel):
    """Playground conversation history."""
    conversation_id: Optional[str] = None
    messages: List[ChatHistoryMessage] = []


class LLMConfig(BaseModel):
    """LLM configuration for agent."""
    model: str = Field(default="claude-sonnet-5")
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=1024, ge=1, le=4096)


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""
    max_tokens_per_minute: int = Field(default=40000)
    max_calls_per_minute: int = Field(default=60)


class ConversationMessage(BaseModel):
    """Represent a message in conversation history."""
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatHistoryRequest(BaseModel):
    """Request model with conversation history."""
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: Optional[str] = None
    include_history: bool = Field(default=True, description="Include conversation history")
