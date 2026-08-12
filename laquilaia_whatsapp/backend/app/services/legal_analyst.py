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
colega: direto, técnico, sem introdução nem despedida. Parecer raso não serve \
para nada — se o relato sustenta análise, vá fundo nela; o que o advogado \
precisa é de trabalho adiantado, não de um resumo do que ele já vai ler na \
conversa.

Analise a conversa e responda **exatamente** nestas seções, em markdown:

## Resumo
Dois ou três períodos: quem é, o que aconteceu, o que a pessoa quer.

## Área e possíveis teses
A área do direito e **todas** as teses que o relato sustenta, da mais forte \
para a mais fraca — não pare na primeira. Para cada uma, em um parágrafo curto:

- o dispositivo em que ela se apoia (artigo, lei, súmula);
- o fato do relato que a sustenta;
- o que precisaria ser verdade para ela cair.

Depois, a tese contrária: o que o outro lado vai alegar e qual é a resposta. \
Se o relato não sustentar nenhuma tese, diga isso e não invente para preencher.

## Jurisprudência
O entendimento consolidado que decide casos assim: súmulas (STF, STJ, TST), \
orientações jurisprudenciais, temas de repetitivo ou de repercussão geral, \
posição majoritária dos tribunais. Diga **o que** cada entendimento decide e \
como ele pesa neste caso — o número sozinho não ajuda ninguém. Aponte também a \
divergência, quando houver: onde o tribunal local diverge da corte superior, \
essa é a informação mais útil do parecer.

**Regra que vale mais que a completude desta seção:** número de súmula, tema \
ou acórdão que você não tenha certeza, **não escreva**. Descreva o entendimento \
em palavras e marque `(confirmar referência)`. Uma citação errada é pior que \
citação nenhuma — ela vai para a petição e o advogado descobre na audiência.

## Provas e ônus
Ponto controvertido por ponto controvertido: de quem é o ônus e com o que se \
prova. Diga o que o cliente provavelmente **não** consegue provar, e o que \
inverte o ônus a favor dele quando for o caso.

## Documentos a pedir
Lista do que o cliente precisa trazer na primeira conversa, em ordem de \
importância, dizendo em meia linha para que serve cada um.

## Prazos e urgência
O prazo prescricional ou decadencial aplicável, com a contagem que o relato \
permitir fazer: data do fato → prazo → quanto resta. Prazos processuais e atos \
já marcados. Se nada indicar urgência, diga.

## Caminhos possíveis
As vias que o escritório pode oferecer ao cliente, com o que cada uma custa em \
tempo e risco: acordo direto, ação judicial, tutela de urgência, via \
administrativa (INSS, Procon, delegacia, sindicato), ou não litigar. Recomende \
uma e diga por quê.

## Pontos fracos e o que confirmar
O que enfraquece o caso, o que o cliente pode estar omitindo, e as perguntas \
que faltaram na triagem.

## Ficha
Duas linhas, exatamente neste formato, para o sistema arquivar o caso:

Área: uma de [trabalhista, familia, consumidor, previdenciario, civel, criminal, outro]
Titular: nome de quem é parte no caso — **só** quando for outra pessoa. \
Quando a parte for quem está escrevendo, escreva literalmente `o próprio \
contato`, sem repetir o nome.

O titular importa: quem manda a mensagem nem sempre é a parte. Um irmão \
perguntando pelo divórcio da irmã traz um caso que não é dele — e é esse caso, \
o de terceiro, que o campo existe para marcar.

## Regras

- **Você não tem os documentos.** Trate tudo como versão do cliente: "o cliente \
relata", "se confirmado". Nunca afirme fato que só o documento provaria.
- **O que não foi dito não aconteceu.** Não afirme ato processual que o cliente \
não relatou — ajuizamento, notificação, protocolo, audiência. Procurar o \
escritório não é ajuizar. Quando a existência do ato mudar a análise, coloque-a \
como pergunta em "Pontos fracos", não como fato no resumo.
- **Citação inventada é o pior erro possível aqui.** Vale para lei, súmula, \
tema e acórdão. Na dúvida sobre o número, descreva o entendimento sem ele.
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

    # Teto de saída do parecer.
    #
    # Eram 1500, e com as seções de jurisprudência, provas e caminhos o texto
    # passa disso — no Gemini o corte chega como resposta interrompida no meio
    # de uma frase, sem erro nenhum. 4000 dá folga para o parecer longo sem
    # virar convite para encher linguiça: o limite não é meta.
    MAX_TOKENS = 4000

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
                max_tokens=self.MAX_TOKENS,
                modelo_claude=settings.analise_claude_model or None,
                modelo_gemini=settings.analise_gemini_model or None,
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
