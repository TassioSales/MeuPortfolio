"""Pydantic models for request/response validation."""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List


# ========== User Models ==========

class UserBase(BaseModel):
    """Base user model."""
    email: EmailStr
    nome: str = Field(..., min_length=1, max_length=255)


class UserCreate(UserBase):
    """User creation model."""
    senha: str = Field(..., min_length=8, max_length=255)


class UserLogin(BaseModel):
    """User login model."""
    email: EmailStr
    senha: str


class UserResponse(UserBase):
    """User response model."""
    id: str
    status: str
    # admin ou operador. O front usa para decidir o que mostrar no menu; quem
    # decide o que é permitido continua sendo o backend, em cada rota.
    papel: str = "operador"
    data_criacao: datetime

    class Config:
        from_attributes = True


class UserCreateByAdmin(UserBase):
    """Corpo de `POST /auth/users` — o administrador criando um operador."""
    senha: str = Field(..., min_length=8, max_length=100)
    papel: str = Field(default="operador", pattern="^(admin|operador)$")


# ========== Agent Models ==========

class AgentBase(BaseModel):
    """Base agent model."""
    nome: str = Field(..., min_length=1, max_length=255)
    descricao: Optional[str] = None
    system_prompt: str
    temperatura: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=1024, ge=1, le=4096)


class AgentCreate(AgentBase):
    """Agent creation model."""
    pass


class AgentUpdate(BaseModel):
    """Agent update model."""
    nome: Optional[str] = None
    descricao: Optional[str] = None
    system_prompt: Optional[str] = None
    temperatura: Optional[float] = None
    max_tokens: Optional[int] = None


class AgentResponse(AgentBase):
    """Agent response model."""
    id: str
    user_id: str
    status: str
    data_criacao: datetime
    data_atualizacao: datetime

    class Config:
        from_attributes = True


# ========== Conversation Models ==========

class ConversationCreate(BaseModel):
    """Conversation creation model."""
    phone_number: str = Field(..., min_length=7, max_length=20)
    agent_id: str


class ConversationResponse(BaseModel):
    """Conversation response model."""
    id: str
    agent_id: str
    phone_number: str
    status: str
    data_inicio: datetime
    data_ultima_msg: datetime

    class Config:
        from_attributes = True


# ========== Message Models ==========

class MessageCreate(BaseModel):
    """Message creation model."""
    conversation_id: str
    conteudo: str = Field(..., min_length=1, max_length=4096)
    remetente: str = Field(..., pattern="^(user|agent)$")


class MessageResponse(MessageCreate):
    """Message response model."""
    id: str
    tokens_usados: Optional[int] = None
    timestamp: datetime

    class Config:
        from_attributes = True


# ========== Lead Models ==========

class LeadCreate(BaseModel):
    """Lead creation model."""
    phone_number: str
    nome: Optional[str] = None
    email: Optional[str] = None


class LeadResponse(LeadCreate):
    """Lead response model."""
    id: str
    status_funil: str
    data_criacao: datetime
    data_atualizacao: datetime

    class Config:
        from_attributes = True


# ========== Kanban Models ==========

class KanbanCardMove(BaseModel):
    """Kanban card movement model."""
    lead_id: str
    column_id: str


# ========== Token Models ==========

class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    """JWT token payload model."""
    sub: str  # user_id
    exp: int
    iat: int


# ========== API Response Models ==========

class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    service: str
    version: str


class ErrorResponse(BaseModel):
    """Error response model."""
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
