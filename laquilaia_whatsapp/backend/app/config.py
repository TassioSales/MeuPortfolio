from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Database
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://laquilaia:laquilaia_dev_pwd@localhost:5432/laquilaia_db"
    )

    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    # Sem uso desde que o cache de histórico saiu (ver `memory_service`).
    # Continua declarada de propósito: ela está no `.env.example` e portanto
    # nos `.env` já existentes, e o pydantic-settings recusa variável que não
    # conheça — remover daqui impediria o backend de subir na máquina de quem
    # já tem o arquivo.
    redis_cache_ttl: int = int(os.getenv("REDIS_CACHE_TTL", "3600"))
    metrics_cache_ttl: int = int(os.getenv("METRICS_CACHE_TTL", "900"))

    # Security
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    # API
    api_port: int = int(os.getenv("API_PORT", "8000"))
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # AI / LLM
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    claude_model: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-5")
    temperature: float = float(os.getenv("TEMPERATURE", "0.7"))
    max_tokens: int = int(os.getenv("MAX_TOKENS", "1024"))
    llm_max_tokens_per_minute: int = int(os.getenv("LLM_MAX_TOKENS_PER_MINUTE", "40000"))
    llm_max_calls_per_minute: int = int(os.getenv("LLM_MAX_CALLS_PER_MINUTE", "60"))

    # Provedor de reserva (Gemini). Vazio desliga a reserva: o erro do Claude
    # sobe como antes, em vez de virar uma resposta de outro modelo em silêncio.
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    # Modelo da transcrição de áudio. Vazio usa o `gemini_model`.
    #
    # Fica separado porque transcrever é tarefa mais simples que conversar, e
    # o modelo menor faz igual: no relato de teste, `gemini-flash-lite-latest`
    # transcreveu tão bem quanto o `flash` em 3,4s contra 9,2s. Foi medido com
    # fala sintética limpa — com áudio de WhatsApp de verdade, gravado na rua,
    # a diferença pode aparecer. Por isso o padrão continua sendo o modelo
    # maior, e trocar é uma variável de ambiente.
    gemini_transcricao_model: str = os.getenv("GEMINI_TRANSCRICAO_MODEL", "")

    # Parecer preliminar para o escritório (ver `legal_analyst.py`).
    # São duas chamadas ao LLM por lead qualificado em vez de uma — desligue
    # se o custo pesar mais que o insumo.
    analise_juridica_enabled: bool = os.getenv(
        "ANALISE_JURIDICA_ENABLED", "True"
    ).lower() == "true"

    # Modelo do parecer, por provedor. Vazio = o mesmo do atendimento.
    #
    # São dois campos e não um porque o parecer cai para a reserva como
    # qualquer outra chamada, e um id de modelo não atravessa provedores:
    # mandar "claude-opus-5" para o Gemini é 404 na hora em que o Claude
    # falhou — justamente quando não se pode falhar de novo.
    #
    # A separação existe porque as duas chamadas não pedem a mesma coisa. O
    # atendimento troca frases curtas no WhatsApp e o que importa é responder
    # rápido; o parecer é uma peça de raciocínio que alguém vai ler antes de
    # decidir o caso, e roda uma vez por lead. Pagar por um modelo melhor só
    # nele é a troca óbvia.
    analise_claude_model: str = os.getenv("ANALISE_CLAUDE_MODEL", "")
    analise_gemini_model: str = os.getenv("ANALISE_GEMINI_MODEL", "")

    # ========== Follow-up de conversa abandonada ==========
    #
    # Quem some no meio da triagem ficava para sempre na primeira coluna, sem
    # ninguém saber se desistiu ou se só não viu a mensagem. Estas variáveis
    # governam o agente cutucar, e depois desistir.
    followup_habilitado: bool = os.getenv(
        "FOLLOWUP_HABILITADO", "True"
    ).lower() == "true"

    # Minutos de silêncio antes de cada tentativa, em ordem.
    #
    # Escalonado e não fixo, de propósito: quem não respondeu em quinze
    # minutos provavelmente está trabalhando; quem não respondeu em dois dias
    # foi embora. Três cutucadas de cinco em cinco minutos é o que faz a
    # pessoa bloquear o número — e aí o escritório perde o lead E o número.
    followup_intervalos_min: str = os.getenv("FOLLOWUP_INTERVALOS_MIN", "15,120,1440")

    # A janela em que é aceitável escrever para alguém, hora local do
    # escritório. Mensagem automática às 3h da manhã queima a reputação do
    # número inteiro, e o WhatsApp não perdoa denúncia de spam.
    followup_hora_inicio: int = int(os.getenv("FOLLOWUP_HORA_INICIO", "8"))
    followup_hora_fim: int = int(os.getenv("FOLLOWUP_HORA_FIM", "20"))

    # Fuso do escritório, para a janela acima significar alguma coisa.
    followup_fuso: str = os.getenv("FOLLOWUP_FUSO", "America/Sao_Paulo")

    # ------------------------------------------- cobrança de assinatura

    cobranca_habilitada: bool = os.getenv(
        "COBRANCA_HABILITADA", "True"
    ).lower() == "true"

    # Minutos entre as cobranças de um contrato enviado e não assinado.
    #
    # Muito mais espaçado que o follow-up de conversa (15 min, 2h, 24h), e de
    # propósito. Lá o que se cobra é uma resposta de uma linha; aqui é a
    # leitura de um contrato de honorários — decisão que a pessoa vai querer
    # conversar em casa. Duas horas, um dia, três dias: quatro dias no total,
    # dentro dos sete de validade do link.
    cobranca_intervalos_min: str = os.getenv(
        "COBRANCA_INTERVALOS_MIN", "120,1440,4320"
    )

    @property
    def cobranca_intervalos(self) -> list:
        """Os intervalos como lista de minutos, ignorando lixo na variável."""
        valores = []
        for item in self.cobranca_intervalos_min.split(","):
            item = item.strip()
            if item.isdigit() and int(item) > 0:
                valores.append(int(item))
        # Lista vazia desligaria a cobrança em silêncio, que é pior que um
        # padrão herdado: quem escreveu lixo na variável não quis desligar.
        return valores or [120, 1440, 4320]

    @property
    def followup_intervalos(self) -> list:
        """
        Os intervalos como lista de minutos.

        Valor inválido vira a lista padrão em vez de derrubar o backend: uma
        vírgula a mais no `.env` não pode impedir o sistema de subir.
        """
        try:
            valores = [
                int(x.strip())
                for x in self.followup_intervalos_min.split(",")
                if x.strip()
            ]
            return valores if valores else [15, 120, 1440]
        except ValueError:
            return [15, 120, 1440]

    # Piso, em reais, a partir do qual o caso comporta o trabalho do escritório.
    #
    # É critério comercial, não jurídico: um caso de mil reais pode ter razão
    # inteira e ainda assim custar mais para tocar do que rende. Por isso o
    # número mora aqui e não no prompt — muda por escritório e muda com o
    # tempo, sem precisar reescrever texto.
    #
    # O parecer compara com o **piso** da faixa estimada, não com o valor
    # provável: caso que só compensa no melhor cenário não compensa. E nada
    # disso descarta ninguém sozinho — o veredito é etiqueta para o advogado
    # discordar, não filtro que apaga o caso.
    caso_valor_minimo: int = int(os.getenv("CASO_VALOR_MINIMO", "15000"))

    # WhatsApp / Evolution API
    # A Evolution v2 escuta na 8080 (SERVER_PORT do .env.example dela). O default
    # anterior, 4000, não corresponde a nenhuma versão.
    evolution_api_url: str = os.getenv("EVOLUTION_API_URL", "http://evolution:8080")
    evolution_api_key: str = os.getenv("EVOLUTION_API_KEY", "")
    evolution_instance_name: str = os.getenv("EVOLUTION_INSTANCE_NAME", "laquilaia")
    # Agente que atende as mensagens vindas da Evolution.
    #
    # A Evolution não sabe que agentes existem: ela manda a mensagem e pronto.
    # Sem este valor, todo webhook real morre com "Missing agent_id" — o
    # `agentId` dentro de `key` só existe nos payloads que nós mesmos
    # forjamos para teste. Uma instância atende por um agente.
    evolution_default_agent_id: str = os.getenv("EVOLUTION_DEFAULT_AGENT_ID", "")
    evolution_webhook_url: str = os.getenv("EVOLUTION_WEBHOOK_URL", "http://localhost:8000/webhook/whatsapp")
    # Segredo compartilhado do HMAC do webhook. Vazio deixa o endpoint
    # aberto, o que só é tolerado com DEBUG=true (ver webhook_security.py).
    webhook_secret: str = os.getenv("WEBHOOK_SECRET", "")
    # Alternativa ao HMAC para emissores que não assinam o corpo — a Evolution
    # API é um deles. Ver `webhook_security.py` para o que se perde.
    webhook_static_token: str = os.getenv("WEBHOOK_STATIC_TOKEN", "")

    # Frontend
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # Origens aceitas pelo CORS, separadas por vírgula.
    #
    # A variável estava documentada no `.env.example` e não era lida por
    # ninguém — o `Settings` não a declarava. A lista do middleware era fixa e
    # trazia "localhost" e "127.0.0.1" soltos, que não são origens válidas:
    # o navegador sempre manda `esquema://host:porta`, então essas entradas
    # nunca casavam e abrir o painel por 127.0.0.1 dava CORS no login.
    allowed_origins: str = os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    )

    @property
    def origens_permitidas(self) -> list:
        """`allowed_origins` como lista, sempre com o `frontend_url` junto."""
        origens = [
            item.strip()
            for item in self.allowed_origins.split(",")
            if item.strip()
        ]
        if self.frontend_url and self.frontend_url not in origens:
            origens.append(self.frontend_url)
        return origens

    class Config:
        env_file = ".env"
        case_sensitive = False
        # O `.env` é compartilhado com o compose e com o frontend, então tem
        # variáveis que não são deste Settings: DB_USER e DB_PORT servem ao
        # container do Postgres, NEXT_PUBLIC_* ao Next.js, ALLOWED_ORIGINS ao
        # proxy. O padrão do pydantic-settings v2 é recusar o que não conhece,
        # e o backend morria no boot com dez erros de `extra_forbidden` — só
        # quando o processo enxergava o arquivo, o que depende do diretório de
        # onde se sobe o uvicorn. Ignorar é o comportamento certo aqui: quem
        # define o contrato é esta classe, não o arquivo.
        extra = "ignore"


settings = Settings()
