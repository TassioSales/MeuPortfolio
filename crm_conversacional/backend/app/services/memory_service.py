"""O histórico da conversa que vai como contexto para o modelo."""

from typing import Any, Dict, List

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Message
from app.utils.exceptions import ValidationException
from app.utils.logger import logger


class MemoryService:
    """Lê do banco as últimas mensagens de uma conversa, em ordem cronológica.

    **Sem cache, de propósito.** Havia aqui um cache read-through no Redis com
    TTL de uma hora, e nenhum caminho de escrita o invalidava: a primeira
    mensagem da conversa lia o banco vazio, gravava `[]` e, pela hora
    seguinte, *toda* mensagem do cliente chegava ao modelo com esse histórico
    congelado. O agente respondia bem à frase recém-chegada e, no turno
    seguinte, não sabia que a tinha recebido — reperguntava a data de
    admissão, a função, o tipo de demissão, indefinidamente. Para o cliente,
    parecia um atendente desatento; era um atendente sendo reiniciado a cada
    turno.

    O `invalidate_cache` existia e tinha teste. O teste invalidava o cache com
    as próprias mãos e passava; produção nunca invalidava. Era um teste do
    método, não do comportamento.

    Podíamos ter espalhado a invalidação pelos quatro pontos que gravam
    mensagem (webhook, webhook em pausa, playground, resposta do operador) e
    torcido para o quinto lembrar. Em vez disso o cache saiu: esta consulta é
    um índice e vinte linhas, uns poucos milissegundos ao lado dos dois
    segundos da chamada ao modelo que vem logo depois. O cache economizava
    0,05% da latência do turno e custava a memória do atendimento inteiro.
    """

    async def get_conversation_history(
        self,
        conversation_id: str,
        db: AsyncSession,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        As últimas `limit` mensagens, da mais antiga para a mais recente.

        Devolve `[{"role": "user"|"assistant", "content": "..."}]`, no formato
        que a API espera. Lista vazia quando a conversa é nova.

        Raises:
            ValidationException: se a consulta ao banco falhar.
        """
        try:
            resultado = await db.execute(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(desc(Message.timestamp))
                .limit(limit)
            )
            mensagens = resultado.scalars().all()

            if not mensagens:
                logger.debug(f"📭 Conversa {conversation_id} ainda sem mensagens")
                return []

            # Cliente é `user`; **todo o resto** é o escritório falando.
            #
            # A comparação era ao contrário (`"assistant" if remetente ==
            # "assistant" else "user"`), e com ela a mensagem que o operador
            # escreve à mão entraria no histórico como se fosse o cliente. O
            # modelo leria a própria resposta do escritório como pergunta e
            # responderia a ela — o atendimento conversando sozinho.
            return [
                {
                    "role": "user" if msg.remetente == "user" else "assistant",
                    "content": msg.conteudo,
                }
                # A consulta ordena DESC para que o LIMIT pegue as *últimas*
                # mensagens; o modelo precisa lê-las na ordem em que
                # aconteceram.
                for msg in reversed(mensagens)
            ]

        except Exception as e:
            logger.error(f"❌ Erro ao ler o histórico da conversa: {e}")
            raise ValidationException(f"Failed to retrieve history: {str(e)}")


memory_service = MemoryService()
