"""SQLAlchemy models for database ORM."""

from sqlalchemy import Column, String, DateTime, Boolean, Integer, Float, Text, ForeignKey, Index, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


class User(Base):
    """User model."""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    nome = Column(String(255), nullable=False)
    senha_hash = Column(String(255), nullable=False)
    status = Column(String(50), default="ativo")  # ativo, inativo, bloqueado
    data_criacao = Column(DateTime, default=datetime.utcnow)
    data_atualizacao = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    agents = relationship("Agent", back_populates="user", cascade="all, delete-orphan")
    lead_timeline = relationship("LeadTimeline", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, nome={self.nome})>"


class ApiKey(Base):
    """API Key model."""
    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    chave = Column(String(255), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    expira_em = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="api_keys")

    def __repr__(self):
        return f"<ApiKey(id={self.id}, user_id={self.user_id})>"


class Agent(Base):
    """Agent IA model."""
    __tablename__ = "agents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    nome = Column(String(255), nullable=False)
    descricao = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=False)
    modelo = Column(String(100), default="claude-sonnet-5")
    temperatura = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=1024)
    status = Column(String(50), default="ativo")  # ativo, inativo, em_teste
    data_criacao = Column(DateTime, default=datetime.utcnow)
    data_atualizacao = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="agents")
    agent_variables = relationship("AgentVariable", back_populates="agent", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="agent", cascade="all, delete-orphan")
    kanban_columns = relationship("KanbanColumn", back_populates="agent", cascade="all, delete-orphan")
    conversation_metrics = relationship("ConversationMetrics", back_populates="agent", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Agent(id={self.id}, nome={self.nome})>"


class AgentVariable(Base):
    """Agent variable model."""
    __tablename__ = "agent_variables"
    __table_args__ = (
        UniqueConstraint("agent_id", "nome_variavel", name="uix_agent_variable_nome"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    nome_variavel = Column(String(255), nullable=False)
    descricao = Column(Text, nullable=True)
    tipo = Column(String(50), nullable=False)  # texto, numero, enum, booleano
    valor_padrao = Column(String(255), nullable=True)
    opcoes = Column(Text, nullable=True)  # JSON array para enum
    data_criacao = Column(DateTime, default=datetime.utcnow)

    # Relationships
    agent = relationship("Agent", back_populates="agent_variables")

    def __repr__(self):
        return f"<AgentVariable(id={self.id}, nome={self.nome_variavel})>"


class Conversation(Base):
    """Conversation model."""
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("agent_id", "phone_number", name="uix_conversation_agent_phone"),
        Index("idx_conversation_phone_number", "phone_number"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    phone_number = Column(String(20), nullable=False)
    status = Column(String(50), default="ativa")  # ativa, pausada, encerrada
    data_inicio = Column(DateTime, default=datetime.utcnow)
    data_ultima_msg = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # `metadata` é reservado pelo Declarative API do SQLAlchemy; o atributo
    # Python muda de nome, a coluna no banco continua sendo "metadata".
    metadados = Column("metadata", Text, nullable=True)

    # Relationships
    agent = relationship("Agent", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    lead = relationship("Lead", back_populates="conversation", uselist=False, cascade="all, delete-orphan")
    function_calls = relationship("FunctionCall", back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Conversation(id={self.id}, phone={self.phone_number})>"


class Message(Base):
    """Message model."""
    __tablename__ = "messages"
    __table_args__ = (
        Index("idx_message_conversation_id", "conversation_id"),
        Index("idx_message_timestamp", "timestamp"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    remetente = Column(String(20), nullable=False)  # "user" ou "assistant"
    conteudo = Column(Text, nullable=False)
    tokens_usados = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    # Ver nota em Conversation.metadados.
    metadados = Column("metadata", Text, nullable=True)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    function_calls = relationship("FunctionCall", back_populates="message", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Message(id={self.id}, timestamp={self.timestamp})>"


class FunctionCall(Base):
    """Function call model (AI function calling)."""
    __tablename__ = "function_calls"
    __table_args__ = (
        Index("idx_function_call_conversation_id", "conversation_id"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id = Column(String(36), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    nome_funcao = Column(String(255), nullable=False)  # "qualificar_lead", "agendar", etc
    parametros_json = Column(Text, nullable=False)
    resultado_json = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    message = relationship("Message", back_populates="function_calls")
    conversation = relationship("Conversation", back_populates="function_calls")

    def __repr__(self):
        return f"<FunctionCall(id={self.id}, funcao={self.nome_funcao})>"


class Lead(Base):
    """Lead model."""
    __tablename__ = "leads"
    __table_args__ = (
        UniqueConstraint("phone_number", name="uix_lead_phone_number"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    phone_number = Column(String(20), unique=True, nullable=False, index=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, unique=True)
    nome = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    status_funil = Column(String(50), default="novo")  # novo, em_qualificacao, qualificado, agendado, arquivado
    data_criacao = Column(DateTime, default=datetime.utcnow)
    data_atualizacao = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    conversation = relationship("Conversation", back_populates="lead")
    lead_details = relationship("LeadDetails", back_populates="lead", uselist=False, cascade="all, delete-orphan")
    lead_timeline = relationship("LeadTimeline", back_populates="lead", cascade="all, delete-orphan")
    kanban_card = relationship("KanbanCard", back_populates="lead", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Lead(id={self.id}, phone={self.phone_number})>"


class LeadDetails(Base):
    """Lead details model."""
    __tablename__ = "lead_details"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(String(36), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, unique=True)
    inconsistencias = Column(Text, nullable=True)
    problemas_detectados = Column(Text, nullable=True)
    score_qualificacao = Column(Integer, default=0)  # 0-100
    dados_json = Column(Text, nullable=True)
    # Parecer preliminar em markdown, para o advogado. Nunca vai ao cliente.
    analise_preliminar = Column(Text, nullable=True)
    data_atualizacao = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    lead = relationship("Lead", back_populates="lead_details")

    def __repr__(self):
        return f"<LeadDetails(id={self.id}, lead_id={self.lead_id})>"


class LeadTimeline(Base):
    """Lead timeline (audit log)."""
    __tablename__ = "lead_timeline"
    __table_args__ = (
        Index("idx_lead_timeline_lead_id", "lead_id"),
        Index("idx_lead_timeline_timestamp", "timestamp"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(String(36), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    status_anterior = Column(String(50), nullable=True)
    status_novo = Column(String(50), nullable=False)
    mudado_por = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    motivo = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    lead = relationship("Lead", back_populates="lead_timeline")
    user = relationship("User", back_populates="lead_timeline")

    def __repr__(self):
        return f"<LeadTimeline(id={self.id}, status={self.status_novo})>"


class KanbanColumn(Base):
    """Kanban column model."""
    __tablename__ = "kanban_columns"
    __table_args__ = (
        UniqueConstraint("agent_id", "nome", name="uix_kanban_column_agent_nome"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    nome = Column(String(255), nullable=False)
    ordem = Column(Integer, nullable=False)
    cor_hex = Column(String(7), default="#6366f1")
    data_criacao = Column(DateTime, default=datetime.utcnow)

    # Relationships
    agent = relationship("Agent", back_populates="kanban_columns")
    cards = relationship("KanbanCard", back_populates="column", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<KanbanColumn(id={self.id}, nome={self.nome})>"


class KanbanCard(Base):
    """Kanban card model."""
    __tablename__ = "kanban_cards"
    __table_args__ = (
        Index("idx_kanban_card_column_id", "column_id"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    column_id = Column(String(36), ForeignKey("kanban_columns.id", ondelete="CASCADE"), nullable=False)
    lead_id = Column(String(36), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, unique=True)
    ordem = Column(Integer, nullable=False)
    data_movimentacao = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    column = relationship("KanbanColumn", back_populates="cards")
    lead = relationship("Lead", back_populates="kanban_card")

    def __repr__(self):
        return f"<KanbanCard(id={self.id}, lead_id={self.lead_id})>"


class ConversationMetrics(Base):
    """Conversation metrics model."""
    __tablename__ = "conversation_metrics"
    __table_args__ = (
        UniqueConstraint("agent_id", "data", name="uix_metrics_agent_data"),
        Index("idx_metrics_data", "data"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    data = Column(DateTime, nullable=False)
    total_atendimentos = Column(Integer, default=0)
    taxa_qualificacao = Column(Float, default=0.0)
    tempo_medio_min = Column(Float, nullable=True)
    mensagens_recebidas = Column(Integer, default=0)
    mensagens_enviadas = Column(Integer, default=0)
    leads_qualificados = Column(Integer, default=0)

    # Relationships
    agent = relationship("Agent", back_populates="conversation_metrics")

    def __repr__(self):
        return f"<ConversationMetrics(id={self.id}, data={self.data})>"


class DailyStats(Base):
    """Daily statistics model."""
    __tablename__ = "daily_stats"
    __table_args__ = (
        # A unicidade é por (data, agente): o job de agregação grava uma linha
        # por agente e por dia, então unicidade só na data faria o segundo
        # agente estourar chave duplicada todo dia.
        UniqueConstraint("data", "agent_id", name="uix_daily_stats_data_agent"),
        Index("idx_daily_stats_data", "data"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    data = Column(DateTime, nullable=False)
    agent_id = Column(String(36), nullable=True)
    mensagens_recebidas = Column(Integer, default=0)
    mensagens_enviadas = Column(Integer, default=0)
    leads_criados = Column(Integer, default=0)
    leads_qualificados = Column(Integer, default=0)

    def __repr__(self):
        return f"<DailyStats(id={self.id}, data={self.data})>"
