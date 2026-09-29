"""
Os dados do escritório — leitura e escrita da linha única.

Existe porque o agente não sabia nada sobre o escritório que ele representa.
Perguntado "onde vocês ficam?" ou "qual o telefone?", ele não tinha o que
responder — e o prompt manda não inventar, então a conversa travava numa
pergunta que qualquer recepcionista responde.

Pior era o caso do cliente antigo: quem já tem processo no escritório e
escreve no número comercial caía numa triagem do zero, como se fosse gente
nova. O `telefone_suporte` existe para isso.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.db.models import ConfiguracaoEscritorio
from app.utils.logger import logger

# Uma instalação, um escritório, uma linha. O id fixo torna a segunda
# impossível de criar por engano.
ID_UNICO = "unica"


async def obter(db: AsyncSession) -> Optional[ConfiguracaoEscritorio]:
    """A configuração, ou `None` se ninguém preencheu nada ainda."""
    resultado = await db.execute(
        select(ConfiguracaoEscritorio).where(ConfiguracaoEscritorio.id == ID_UNICO)
    )
    return resultado.scalars().first()


async def obter_ou_criar(db: AsyncSession) -> ConfiguracaoEscritorio:
    """
    A configuração, criando a linha vazia se for a primeira vez.

    Sem commit: quem chama decide o momento.
    """
    config = await obter(db)
    if config is None:
        config = ConfiguracaoEscritorio(id=ID_UNICO)
        db.add(config)
        await db.flush()
    return config


async def para_o_prompt() -> Optional[ConfiguracaoEscritorio]:
    """
    A configuração, lida numa sessão própria, para o momento de montar o
    system prompt.

    É uma leitura por mensagem atendida, e é de propósito que não tem cache.
    Este projeto já teve um cache de contexto no Redis que ninguém invalidava:
    o escritório mudava algo no painel e o agente seguia dizendo o valor
    antigo por uma hora — sem erro, sem log, sem sintoma além de o cliente
    receber informação errada. Uma linha por chave primária é barata; a versão
    velha de um telefone não é.
    """
    try:
        async with AsyncSessionLocal() as db:
            return await obter(db)
    except Exception as e:
        # Falhar em ler a configuração não pode derrubar o atendimento: sem
        # ela o agente responde como respondia antes de existir esta tela.
        logger.warning(f"⚠️ Não foi possível ler a configuração do escritório: {e}")
        return None
