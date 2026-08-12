"""
Parecer preliminar do caso, para o escritório ler.

Roda **depois** da triagem e não toca na conversa: o cliente continua vendo só
o atendimento. A separação é o ponto — um bot dizendo "você tem direito a X"
ao cliente vira responsabilidade do advogado que assina, enquanto uma análise
interna é insumo de trabalho, lida por quem sabe descartá-la.

São duas chamadas ao LLM por lead qualificado, e não uma. O custo dobra;
`ANALISE_JURIDICA_ENABLED=false` desliga sem mexer em código.
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Message
from app.utils.logger import logger


PROMPT_ANALISTA = """Você é advogado sênior e está fazendo a análise preliminar \
de um caso que chegou pelo WhatsApp do escritório.

Quem vai ler é o advogado que assumirá o caso — não o cliente. Escreva para um \
colega: direto, técnico onde precisa ser, sem introdução nem despedida.

Analise a conversa e responda **exatamente** nestas seções, em markdown:

## Resumo
Dois ou três períodos: quem é, o que aconteceu, o que a pessoa quer.

## Área e possíveis teses
A área do direito e as teses que o relato sugere. Cite o dispositivo legal \
quando ele for evidente (ex.: art. 482 da CLT para justa causa). Se o relato \
não sustentar nenhuma tese, diga isso.

## Documentos a pedir
Lista do que o cliente precisa trazer na primeira conversa, em ordem de \
importância.

## Prazos e urgência
Prazos prescricionais ou processuais que o relato deixa entrever, e o que \
justifica pressa. Se nada indicar urgência, diga.

## Pontos fracos e o que confirmar
O que enfraquece o caso, o que o cliente pode estar omitindo, e as perguntas \
que faltaram na triagem.

## Ficha
Duas linhas, exatamente neste formato, para o sistema arquivar o caso:

Área: uma de [trabalhista, familia, consumidor, previdenciario, civel, criminal, outro]
Titular: nome de quem é parte no caso, ou "o próprio contato" quando for quem \
está escrevendo

O titular importa: quem manda a mensagem nem sempre é a parte. Um irmão \
perguntando pelo divórcio da irmã traz um caso que não é dele.

## Regras

- **Você não tem os documentos.** Trate tudo como versão do cliente: "o cliente \
relata", "se confirmado". Nunca afirme fato que só o documento provaria.
- **O que não foi dito não aconteceu.** Não afirme ato processual que o cliente \
não relatou — ajuizamento, notificação, protocolo, audiência. Procurar o \
escritório não é ajuizar. Quando a existência do ato mudar a análise, coloque-a \
como pergunta em "Pontos fracos", não como fato no resumo.
- Não estime valor de causa nem honorários.
- Não prometa resultado. Fale em risco e probabilidade, não em certeza.
- Se a conversa for curta ou confusa demais para analisar, escreva apenas o \
Resumo e, em "Pontos fracos", o que precisa ser perguntado antes de qualquer \
análise. Não invente para preencher seção.
"""


class LegalAnalyst:
    """Gera o parecer preliminar a partir da conversa."""

    # A triagem inteira, e não as últimas 5 mensagens: uma análise que perde o
    # começo da conversa perde justamente o relato do caso.
    MAX_MENSAGENS = 60

    @property
    def enabled(self) -> bool:
        return settings.analise_juridica_enabled

    async def analisar(
        self,
        conversation_id: str,
        db: AsyncSession,
        agent=None,
    ) -> Optional[str]:
        """
        Devolve o parecer em markdown, ou `None` se não der para gerar.

        Nunca levanta exceção: a análise é acessória, e derrubar a qualificação
        de um lead porque o parecer falhou seria trocar o essencial pelo
        acessório.
        """
        if not self.enabled:
            return None

        try:
            transcricao = await self._transcrever(conversation_id, db)
            if not transcricao:
                logger.debug(f"⏭️ Sem conversa para analisar ({conversation_id})")
                return None

            from app.services.llm_service import llm_service

            texto, uso = await llm_service.analisar_com_prompt(
                system_prompt=PROMPT_ANALISTA,
                user_message=transcricao,
                user_id=getattr(agent, "user_id", None),
                max_tokens=1500,
            )
            logger.info(
                f"⚖️ Parecer preliminar gerado para a conversa {conversation_id} "
                f"({uso.get('total_tokens')} tokens, {uso.get('model')})"
            )
            return texto

        except Exception as e:
            logger.warning(f"⚠️ Não foi possível gerar o parecer: {e}")
            return None

    async def _transcrever(self, conversation_id: str, db: AsyncSession) -> str:
        resultado = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.timestamp.asc())
            .limit(self.MAX_MENSAGENS)
        )
        mensagens: List[Message] = list(resultado.scalars().all())
        if not mensagens:
            return ""

        linhas = [
            f"{'CLIENTE' if m.remetente == 'user' else 'ATENDIMENTO'}: {m.conteudo}"
            for m in mensagens
        ]
        return "Conversa recebida pelo WhatsApp:\n\n" + "\n\n".join(linhas)


legal_analyst = LegalAnalyst()
