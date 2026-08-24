"""SQLAlchemy models for database ORM."""

from sqlalchemy import Column, String, Date, DateTime, Boolean, Integer, Float, LargeBinary, Text, ForeignKey, Index, UniqueConstraint
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
    # admin configura o sistema; operador só atende.
    #
    # O default é o menor privilégio: um papel que chega vazio por qualquer
    # caminho — importação, script, migração esquecida — não pode virar
    # administrador por omissão.
    papel = Column(String(20), default="operador", nullable=False)
    data_criacao = Column(DateTime, default=datetime.utcnow)
    data_atualizacao = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    # Sem `delete-orphan`: apagar quem criou o agente **não** apaga o agente.
    #
    # O `user_id` do agente significava "dono" e passou a significar "quem
    # criou" quando o agente virou do escritório. O CASCADE ficou para trás, e
    # com ele um alçapão: remover a conta de quem saiu do escritório levaria
    # junto o agente, as conversas, os leads e o histórico — tudo, em silêncio,
    # por uma linha de SQL que ninguém associaria a isso.
    agents = relationship("Agent", back_populates="user")
    # Sem `delete-orphan`, de novo, e pelo mesmo motivo do `agents` acima: a
    # coluna já é `ondelete=SET NULL` no banco, mas o cascade do ORM apagava as
    # linhas antes de o banco ter chance de anulá-las — e o histórico do
    # escritório perdia tudo que a pessoa fez, não só o nome dela.
    lead_timeline = relationship("LeadTimeline", back_populates="user")

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
    # Quem criou, não quem manda: o agente é do escritório (ver
    # `agent_service.get_agent`). `SET NULL` e não `CASCADE` porque a saída de
    # uma pessoa não pode apagar o atendimento do escritório inteiro.
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    nome = Column(String(255), nullable=False)
    # O nome pelo qual o cliente conhece quem o atende.
    #
    # Diferente de `nome`, que é o rótulo interno ("Triagem trabalhista"):
    # ninguém no WhatsApp deve ouvir "meu nome é Triagem trabalhista". Vazio é
    # estado válido e comum — aí o agente se apresenta como o escritório, sem
    # inventar nome próprio.
    nome_atendente = Column(String(80), nullable=True)
    descricao = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=False)
    modelo = Column(String(100), default="claude-sonnet-5")
    temperatura = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=1024)
    status = Column(String(50), default="ativo")  # ativo, inativo, em_teste
    # Se o agente lê o que o cliente anexa: foto da carta de demissão, PDF do
    # contrato, áudio de quem prefere falar.
    #
    # Desligado por padrão, e é decisão de quem administra: cada anexo é uma
    # chamada a mais à Evolution e tokens a mais no modelo, e há escritório que
    # prefere que documento chegue por outro canal. Ligado sem querer, a conta
    # sobe sem ninguém entender por quê.
    anexos_habilitados = Column(Boolean, default=False, nullable=False)
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
    # Quantas vezes o agente cutucou sem obter resposta, e quando foi a
    # última. Zera assim que o cliente escreve — a contagem é de silêncio
    # seguido, não de cutucadas na vida toda.
    followups_enviados = Column(Integer, nullable=False, default=0)
    ultimo_followup_em = Column(DateTime, nullable=True)

    # Em que ponto do ciclo a conversa está: `triagem`, `coleta`, `contratado`.
    #
    # Separado de `status` de propósito. `status` é sobre **quem responde** —
    # ativa (a IA), pausada (um humano assumiu), encerrada. `fase` é sobre **o
    # que está sendo perguntado**, e as duas coisas variam juntas sem se
    # implicar: uma conversa pausada pode estar em coleta, e uma ativa pode já
    # ter contrato assinado.
    #
    # É a fase que decide qual bloco de instrução vai anexado ao prompt. Na
    # triagem o agente não pede documento — pedir CPF a quem ainda não sabe se
    # vai ser cliente é onde a conversa morre.
    fase = Column(String(20), nullable=False, default="triagem")
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

    # Um contato pode trazer mais de um caso, inclusive de outra pessoa.
    casos = relationship(
        "Caso",
        back_populates="lead",
        cascade="all, delete-orphan",
        order_by="desc(Caso.data_abertura)",
    )

    def __repr__(self):
        return f"<Lead(id={self.id}, phone={self.phone_number})>"


class Caso(Base):
    """
    Um assunto jurídico trazido por um contato.

    `Lead` era as duas coisas ao mesmo tempo: a pessoa que manda mensagem e o
    caso dela. Isso quebra no primeiro cliente que volta com outro assunto — e
    quebra pior quando o assunto é de terceiro, porque o nome no card passa a
    ser o de quem escreveu, não o de quem é parte. O caso do irmão fica
    pendurado no cadastro do irmão.

    O funil continua no `Lead` nesta primeira volta: mover card por caso mexe
    no arrastar, nas métricas e no WebSocket, e a base vem antes.
    """

    __tablename__ = "casos"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(
        String(36), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # trabalhista, familia, consumidor, previdenciario, civel, criminal, outro
    area = Column(String(50), nullable=True)
    resumo = Column(Text, nullable=True)
    # Quem é parte no caso. Vazio significa o próprio contato — o comum.
    titular = Column(String(255), nullable=True)
    status = Column(String(50), default="aberto")  # aberto, arquivado
    # Parecer preliminar deste caso. Fica aqui, e não no contato, porque dois
    # casos do mesmo contato têm análises diferentes e uma sobrescreveria a
    # outra.
    analise_preliminar = Column(Text, nullable=True)
    score_qualificacao = Column(Integer, default=0)
    # Porte econômico, lido da seção do parecer. Faixa em reais inteiros — sem
    # os documentos, centavo é precisão que o número não tem, e valor único é
    # precisão que a estimativa não tem.
    valor_estimado_min = Column(Integer, nullable=True)
    valor_estimado_max = Column(Integer, nullable=True)
    # acima_do_piso, abaixo_do_piso, indeterminado, nao_se_aplica.
    #
    # `indeterminado` é o default porque parecer sem porte não é caso inviável:
    # é caso que ninguém dimensionou. A diferença importa — a segunda etiqueta
    # manda perguntar, a primeira mandaria descartar.
    viabilidade = Column(String(30), default="indeterminado")
    data_abertura = Column(DateTime, default=datetime.utcnow)
    data_atualizacao = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lead = relationship("Lead", back_populates="casos")

    def __repr__(self):
        return f"<Caso(id={self.id}, area={self.area}, lead={self.lead_id})>"


class DadosDoContrato(Base):
    """
    O que um contrato exige e uma triagem não pergunta.

    Nome e telefone bastam para atender; CPF, RG, estado civil e endereço só
    fazem sentido quando já se decidiu que o caso é aceito. Perguntá-los na
    triagem seria pedir documento a quem ainda não sabe se vai ser cliente —
    e é onde a conversa morre.

    Tabela separada de `LeadDetails` de propósito: aquela guarda o que a
    triagem apurou sobre o **caso**, esta guarda o que identifica a **pessoa**
    num instrumento jurídico. São dados com dono, ciclo e sensibilidade
    diferentes.
    """

    __tablename__ = "dados_do_contrato"
    __table_args__ = (UniqueConstraint("lead_id", name="uix_dados_do_contrato_lead"),)

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(
        String(36), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False
    )
    # Só dígitos, sem pontuação — a formatação é da tela, não do banco.
    cpf = Column(String(14), nullable=True)
    rg = Column(String(30), nullable=True)
    nacionalidade = Column(String(60), nullable=True)
    estado_civil = Column(String(40), nullable=True)
    profissao = Column(String(120), nullable=True)
    endereco = Column(Text, nullable=True)
    cep = Column(String(9), nullable=True)
    cidade = Column(String(120), nullable=True)
    uf = Column(String(2), nullable=True)
    data_atualizacao = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<DadosDoContrato(lead_id={self.lead_id})>"


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


class ConfiguracaoEscritorio(Base):
    """
    Os dados do escritório que o agente precisa saber.

    Uma linha só, sempre — esta instalação atende um escritório, a mesma
    premissa que sustenta a autorização por papel. O `id` fixo (`"unica"`)
    torna isso impossível de violar por engano: não há como criar a segunda.

    Por que isto não vive dentro do `system_prompt`: o prompt é editável pelo
    painel, e um telefone escondido no meio de nove mil caracteres se perde na
    primeira reescrita. Pior — quem edita o prompt é quem cuida do
    atendimento, e quem sabe o telefone do suporte é quem cuida do escritório.
    São duas pessoas e duas telas.
    """

    __tablename__ = "configuracao_escritorio"

    id = Column(String(36), primary_key=True, default="unica")
    nome = Column(String(255), nullable=True)
    cnpj = Column(String(32), nullable=True)
    oab_responsavel = Column(String(64), nullable=True)
    fundador = Column(String(255), nullable=True)
    endereco = Column(Text, nullable=True)
    # Cidade em campo próprio, apesar de já estar dentro de `endereco`. O
    # contrato precisa dela isolada em dois lugares — a cláusula de foro e a
    # linha "Cidade, 20 de agosto de 2026" acima da assinatura — e extraí-la
    # de um endereço escrito livremente é adivinhação.
    cidade = Column(String(120), nullable=True)
    email = Column(String(255), nullable=True)
    telefone = Column(String(32), nullable=True)
    # Número público entregue a quem **já é cliente** e escreveu no comercial
    # por engano. Sem ele, o agente ou reabre uma triagem que não existe ou
    # deixa a pessoa sem saída.
    telefone_suporte = Column(String(32), nullable=True)
    horario_atendimento = Column(String(255), nullable=True)
    site = Column(String(255), nullable=True)
    instagram = Column(String(255), nullable=True)
    data_atualizacao = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ConfiguracaoEscritorio(nome={self.nome})>"


class LancamentoMarketing(Base):
    """
    Um gasto do escritório em atrair cliente.

    Só o escritório sabe quanto pagou de anúncio — não há de onde deduzir
    isso. Já o consumo de IA o sistema conhece: fica em `Message.tokens_usados`
    e é somado na hora de calcular, em vez de ser digitado. Pedir os dois à
    mão daria o que os contadores do produto concorrente mostram: campo em
    branco para sempre.

    Dinheiro em **centavos inteiros**. Ponto flutuante em valor monetário
    acumula erro na soma — `0.1 + 0.2` não é `0.3` —, e um relatório de custo
    que não fecha com o extrato é um relatório que ninguém usa duas vezes.
    """

    __tablename__ = "lancamentos_marketing"
    __table_args__ = (Index("idx_lancamento_data", "data"),)

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    data = Column(Date, nullable=False)
    investimento_ads_centavos = Column(Integer, nullable=False, default=0)
    observacao = Column(Text, nullable=True)
    criado_por = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    data_criacao = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<LancamentoMarketing(data={self.data}, ads={self.investimento_ads_centavos})>"


class Agendamento(Base):
    """
    Um retorno combinado com o cliente.

    "Te ligo amanhã às 15h" era dito na conversa e morria ali: virava um
    compromisso que só existia na cabeça de quem prometeu, e o cliente
    esperava a ligação que ninguém marcou em lugar nenhum.

    `criado_por` é nulo quando quem agendou foi a triagem — hoje ninguém, mas
    a coluna existe para o dia em que o agente passar a extrair a combinação
    da conversa. Sem ela, ligar isso depois exigiria migração.
    """

    __tablename__ = "agendamentos"
    __table_args__ = (
        Index("idx_agendamento_quando", "quando"),
        Index("idx_agendamento_lead", "lead_id"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(
        String(36), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False
    )
    quando = Column(DateTime, nullable=False)
    motivo = Column(Text, nullable=True)
    # pendente, realizado, cancelado
    status = Column(String(20), nullable=False, default="pendente")
    criado_por = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    data_criacao = Column(DateTime, default=datetime.utcnow)
    data_atualizacao = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Agendamento(lead={self.lead_id}, quando={self.quando}, status={self.status})>"


class ModeloDeContrato(Base):
    """
    O texto do contrato, com lacunas.

    O corpo é escrito pelo advogado no painel, não por este código. É a única
    forma defensável: as cláusulas, e principalmente o percentual de
    honorários, são compromisso comercial e profissional do escritório — um
    software que os inventasse estaria assumindo obrigação em nome de alguém.

    As lacunas são `{{cliente.nome}}`, `{{escritorio.cnpj}}` e afins; a lista
    completa vive em `contrato_service.VARIAVEIS`.
    """

    __tablename__ = "modelos_contrato"
    __table_args__ = (UniqueConstraint("nome", name="uix_modelo_contrato_nome"),)

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nome = Column(String(255), nullable=False)
    corpo = Column(Text, nullable=False)
    # Só um ativo por vez — quem gera contrato não escolhe entre versões, usa
    # a que vale hoje. Rascunho e versão antiga ficam inativos.
    ativo = Column(Boolean, default=False, nullable=False)
    data_criacao = Column(DateTime, default=datetime.utcnow)
    data_atualizacao = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ModeloDeContrato(nome={self.nome}, ativo={self.ativo})>"


class Contrato(Base):
    """
    Um contrato gerado para um lead.

    `corpo` guarda o texto **já preenchido**, e não uma referência ao modelo.
    O modelo muda — o advogado corrige uma cláusula em março — e o contrato
    que alguém assinou em janeiro tem de continuar dizendo o que dizia em
    janeiro. Documento que se altera depois de emitido não é documento.
    """

    __tablename__ = "contratos"
    __table_args__ = (Index("idx_contrato_lead", "lead_id"),)

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(
        String(36), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False
    )
    # Só para saber de qual modelo veio; `SET NULL` porque apagar o modelo não
    # pode apagar contrato emitido.
    modelo_id = Column(
        String(36), ForeignKey("modelos_contrato.id", ondelete="SET NULL"), nullable=True
    )
    corpo = Column(Text, nullable=False)
    # gerado → enviado → assinado. `cancelado` sai de qualquer um deles.
    status = Column(String(20), nullable=False, default="gerado")
    gerado_por = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    data_criacao = Column(DateTime, default=datetime.utcnow)

    # ---------------------------------------------------------- assinatura

    # O segredo do fluxo inteiro. 256 bits de `secrets.token_urlsafe`, único,
    # indexado — é por ele que a página pública acha o contrato, e é a única
    # coisa que separa um estranho do documento. Nulo enquanto ninguém pediu
    # para enviar: contrato gerado e não enviado não tem por que ter link vivo.
    token_assinatura = Column(String(64), nullable=True, unique=True, index=True)
    # Link tem prazo. Um endereço que assina contrato e vale para sempre é um
    # endereço que continua valendo depois de o caso ser recusado, de o cliente
    # desistir ou de o celular dele ser vendido.
    token_expira_em = Column(DateTime, nullable=True)
    link_assinatura = Column(String(500), nullable=True)
    data_envio = Column(DateTime, nullable=True)

    data_assinatura = Column(DateTime, nullable=True)
    # O que a pessoa digitou. Não é conferido contra o cadastro de propósito:
    # divergência de grafia é prova a ser lida por gente, não motivo para
    # recusar a assinatura de quem escreveu o próprio nome sem acento.
    assinado_nome = Column(String(255), nullable=True)
    # IPv6 cabe em 45 caracteres.
    assinado_ip = Column(String(45), nullable=True)
    assinado_user_agent = Column(String(500), nullable=True)
    # SHA-256 do `corpo` no instante da assinatura. É o que permite provar
    # depois que o texto não mudou — e o que denunciaria se tivesse mudado.
    hash_documento = Column(String(64), nullable=True)

    # O contrato absorvido: os bytes do PDF, com a folha de auditoria, dentro
    # do nosso banco.
    #
    # Redesenhar o PDF a partir do `corpo` daria o mesmo texto, mas não é a
    # mesma coisa: o que a pessoa viu e aceitou foi *este* arquivo, e o que se
    # apresenta num litígio é *este* arquivo. Guardar o resultado é o que
    # significa "a pessoa pode sumir e o contrato fica".
    pdf_assinado = Column(LargeBinary, nullable=True)

    # Quantas vezes o agente já cobrou a assinatura, e quando foi a última.
    #
    # Contadas no contrato, e não na conversa, porque são coisas diferentes:
    # o follow-up de conversa cutuca quem parou de responder, e este cobra
    # quem recebeu um documento e não voltou. Um cliente pode estar em dia com
    # a conversa e devendo assinatura.
    cobrancas_enviadas = Column(Integer, nullable=False, default=0)
    ultima_cobranca_em = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Contrato(lead={self.lead_id}, status={self.status})>"
