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


# A `## Ficha` vem em segundo lugar, logo depois do Resumo, e não no fim.
#
# É ela que classifica o caso — área e titular — e é o que o `caso_service` lê
# para arquivar. Estando no fim, ela é a primeira coisa que se perde quando o
# modelo estoura o teto de saída: foi o que aconteceu no primeiro parecer real
# no Opus 5, que escreveu 19 mil caracteres, foi cortado, e devolveu um parecer
# ótimo que o sistema não conseguiu classificar. Ordem por fragilidade, não por
# elegância.
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

## Ficha
Duas linhas, exatamente neste formato, para o sistema arquivar o caso:

Área: uma de [trabalhista, familia, consumidor, previdenciario, civel, criminal, outro]
Titular: nome de quem é parte no caso — **só** quando for outra pessoa. \
Quando a parte for quem está escrevendo, escreva literalmente `o próprio \
contato`, sem repetir o nome.

O titular importa: quem manda a mensagem nem sempre é a parte. Um irmão \
perguntando pelo divórcio da irmã traz um caso que não é dele — e é esse caso, \
o de terceiro, que o campo existe para marcar.

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

## Porte econômico
Quanto o caso comporta, em **faixa**: piso e valor provável, com a conta à \
vista — o que entra, com que número, e de onde veio cada número. Se o número \
veio do relato, aponte de onde; se você teve de arbitrar, diga que arbitrou e \
com que base.

Feche a seção com duas linhas exatamente neste formato, que o sistema lê:

Valor estimado: R$ 20.000 a R$ 35.000
Viabilidade: acima do piso

As opções de viabilidade são: `acima do piso`, `abaixo do piso`, `não dá para \
dimensionar` e `não se aplica`.

Regras desta seção, e elas valem mais que o resto dela:

- **Faixa, nunca número único.** Você não tem os documentos; precisão aqui é \
falsa e o advogado repassa ao cliente como se fosse conta feita.
- **Sem os números básicos, não dimensione.** Escreva `Viabilidade: não dá \
para dimensionar` e diga em uma linha qual pergunta falta. Chutar é pior que \
não responder: o escritório descarta um caso bom por causa de um número que \
você inventou.
- O piso do escritório é **R$ {VALOR_MINIMO}**. Compare com o **piso** da sua \
faixa, não com o valor provável — caso que só compensa no melhor cenário não \
compensa.
- Estar abaixo do piso **não** é motivo para enfraquecer a análise nas outras \
seções, nem para recomendar não litigar. São coisas diferentes: uma é o \
direito da pessoa, outra é a conta do escritório.
- Em matéria criminal, escreva `Viabilidade: não se aplica`. Liberdade não se \
dimensiona por valor de causa.

## Caminhos possíveis
As vias que o escritório pode oferecer ao cliente, com o que cada uma custa em \
tempo e risco: acordo direto, ação judicial, tutela de urgência, via \
administrativa (INSS, Procon, delegacia, sindicato), ou não litigar. Recomende \
uma e diga por quê.

## Pontos fracos e o que confirmar
O que enfraquece o caso, o que o cliente pode estar omitindo, e as perguntas \
que faltaram na triagem.

## Regras

- **Você não tem os documentos.** Trate tudo como versão do cliente: "o cliente \
relata", "se confirmado". Nunca afirme fato que só o documento provaria.
- **O que não foi dito não aconteceu.** Não afirme ato processual que o cliente \
não relatou — ajuizamento, notificação, protocolo, audiência. Procurar o \
escritório não é ajuizar. Quando a existência do ato mudar a análise, coloque-a \
como pergunta em "Pontos fracos", não como fato no resumo.
- **Citação inventada é o pior erro possível aqui.** Vale para lei, súmula, \
tema e acórdão. Na dúvida sobre o número, descreva o entendimento sem ele.
- Não estime honorários, e não estime valor fora da seção de Porte econômico — \
lá é faixa, com a conta à vista; no meio do texto vira número solto que alguém \
repassa ao cliente.
- Não prometa resultado. Fale em risco e probabilidade, não em certeza.
- **Denso, não longo.** O parecer inteiro fica entre 800 e 1500 palavras. Toda \
frase precisa carregar informação que o advogado ainda não tem: corte adjetivo, \
repetição e explicação de conceito que qualquer advogado já sabe. Não corte \
análise para caber — corte texto.
- Se a conversa for curta ou confusa demais para analisar, escreva apenas o \
Resumo e, em "Pontos fracos", o que precisa ser perguntado antes de qualquer \
análise. Não invente para preencher seção.
"""


def prompt_do_analista(valor_minimo: Optional[int] = None) -> str:
    """
    O prompt com o piso do escritório preenchido.

    O piso entra por substituição e não por `str.format` porque o texto tem
    chaves e crases próprias — um `format` quebraria na primeira citação em
    bloco que alguém acrescentasse ao prompt, e quebraria em produção, não em
    revisão.
    """
    piso = settings.caso_valor_minimo if valor_minimo is None else valor_minimo
    return PROMPT_ANALISTA.replace("{VALOR_MINIMO}", f"{piso:,}".replace(",", "."))


class LegalAnalyst:
    """Gera o parecer preliminar a partir da conversa."""

    # A triagem inteira, e não as últimas 5 mensagens: uma análise que perde o
    # começo da conversa perde justamente o relato do caso.
    MAX_MENSAGENS = 60

    # Teto de saída do parecer.
    #
    # Eram 1500, e com as seções de jurisprudência, provas e caminhos o texto
    # passa disso — o corte chega como resposta interrompida no meio de uma
    # frase, sem erro nenhum.
    #
    # 4000 também não bastou: o Opus 5 escreveu 19 mil caracteres e ainda foi
    # cortado. Quem segura o tamanho agora é o prompt (800 a 1500 palavras, o
    # que dá ~2500 tokens), e o teto é rede de segurança, não meta. Alto de
    # propósito: teto não custa nada, só se paga o que o modelo gerar, e o
    # preço de errar para baixo é um parecer sem a Ficha.
    MAX_TOKENS = 8000

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
                system_prompt=prompt_do_analista(),
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
