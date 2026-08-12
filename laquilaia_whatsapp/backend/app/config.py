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
