"""
Cobrar quem recebeu o contrato e não assinou.

O dono descreveu o buraco em uma frase: *"a pessoa pode assinar e sumir"* — e
o inverso é o mesmo problema. O contrato sai, o link chega no WhatsApp, e
depois disso ninguém sabe se a pessoa não assinou porque desistiu, porque
travou numa cláusula, ou porque simplesmente não abriu. As três coisas têm a
mesma aparência no painel: um contrato parado.

**Cobrar não é repetir o link.** A primeira mensagem manda o link de novo,
porque a hipótese mais provável é que a pessoa não viu. A segunda **pergunta**,
que é o que o dono pediu: ficou dúvida, ou prefere não seguir? A terceira dá a
saída, porque insistir uma quarta vez é o que faz alguém bloquear o número —
e aí o escritório perde o cliente e o número junto.

**Por que é um serviço separado do follow-up de conversa.** Aquele cutuca quem
parou de responder; este cobra quem recebeu um documento e não voltou. Dá para
estar em dia com a conversa e devendo assinatura. Os dois não se atropelam por
construção: o follow-up de conversa só pega conversas cuja última mensagem é
do agente (`remetente == "assistant"`), e o envio do contrato entra como
`sistema` — ninguém leva as duas cutucadas.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import AsyncSessionLocal
from app.db.models import Contrato, Conversation, Lead, LeadTimeline, Message
from app.services import assinatura_service
from app.services.followup_service import LOTE, dentro_do_horario
from app.utils.fuso import em_brasilia
from app.utils.logger import logger


def texto_da_cobranca(
    tentativa: int, nome: Optional[str], link: str, vence_em: Optional[datetime]
) -> str:
    """
    O que vai ser mandado, e por que cada uma é diferente da anterior.

    Três mensagens iguais são três mensagens ignoradas. A escada aqui é:
    lembrar → perguntar → oferecer a saída.
    """
    tratamento = f"Oi, {nome.split()[0]}!" if nome else "Oi!"
    prazo = em_brasilia(vence_em, com_fuso=False)

    if tentativa == 1:
        # A hipótese mais provável é a mais boba: não viu a mensagem.
        return (
            f"{tratamento} Passando para lembrar do contrato — ele ainda está "
            f"esperando sua assinatura.\n\n{link}\n\n"
            "Dá para assinar pelo próprio celular, leva menos de um minuto."
        )

    if tentativa == 2:
        # A pergunta que o dono pediu. Aberta de propósito: "ficou alguma
        # dúvida?" recebe resposta; "você vai assinar?" recebe silêncio.
        return (
            f"{tratamento} Vi que o contrato ainda não foi assinado. Ficou "
            "alguma dúvida sobre alguma parte dele, ou prefere não seguir "
            "agora?\n\n"
            "Pode falar comigo com sinceridade — se for o caso de esclarecer "
            "algo antes, é só dizer o que ficou confuso.\n\n"
            f"E se estiver tudo certo, o link é este:\n{link}"
        )

    fecho = (
        f"O link segue valendo até {prazo}"
        if prazo
        else "O link ainda está valendo"
    )
    return (
        f"{tratamento} Não vou insistir mais para não incomodar. "
        f"{fecho}, e se mudar de ideia é só me chamar por aqui a qualquer "
        f"momento — seu caso fica guardado com a gente.\n\n{link}"
    )


async def contratos_para_cobrar(
    db: AsyncSession, agora: Optional[datetime] = None
) -> List[Tuple[Contrato, Conversation, Optional[Lead]]]:
    """
    Os contratos que estão esperando assinatura há tempo demais.

    Ficam de fora, e cada exclusão tem motivo:

    - **Assinado ou cancelado** — não há o que cobrar.
    - **Sem link** — contrato gerado e nunca enviado. Cobrar assinatura de um
      documento que a pessoa não recebeu é constrangedor.
    - **Conversa pausada ou encerrada** — na pausada um humano assumiu, e um
      robô cobrando por cima do atendimento de gente é pior que silêncio.
    - **Cota esgotada** — três e para.
    - **Cliente respondeu depois da última cobrança** — a pessoa está falando
      com a gente agora; cortar a conversa com "assina aí" é exatamente o
      movimento errado. O relógio passa a contar da fala dela, então a
      cobrança volta se a conversa esfriar, e não some para sempre.
    """
    agora = agora or datetime.utcnow()
    intervalos = settings.cobranca_intervalos

    # A última mensagem **do cliente** em cada conversa, numa consulta só.
    # Buscar por contrato dentro do laço seria uma ida ao banco por linha — o
    # defeito que o board do Kanban já teve.
    ultima_do_cliente = (
        select(
            Message.conversation_id.label("conversation_id"),
            func.max(Message.timestamp).label("quando"),
        )
        .where(Message.remetente == "user")
        .group_by(Message.conversation_id)
        .subquery()
    )

    linhas = await db.execute(
        select(Contrato, Conversation, Lead, ultima_do_cliente.c.quando)
        .join(Lead, Lead.id == Contrato.lead_id)
        .join(Conversation, Conversation.id == Lead.conversation_id)
        .outerjoin(
            ultima_do_cliente,
            ultima_do_cliente.c.conversation_id == Conversation.id,
        )
        .where(Contrato.data_assinatura.is_(None))
        .where(Contrato.status == assinatura_service.STATUS_ENVIADO)
        .where(Contrato.data_envio.isnot(None))
        .where(Contrato.cobrancas_enviadas < len(intervalos))
        .where(Conversation.status == "ativa")
        .order_by(Contrato.data_envio)
        .limit(LOTE * 4)
    )

    devidos: List[Tuple[Contrato, Conversation, Optional[Lead]]] = []

    for contrato, conversa, lead, falou_em in linhas:
        # O relógio conta do contato mais recente entre os três: o envio, a
        # última cobrança, ou a última fala do cliente.
        referencia = contrato.data_envio
        for candidato in (contrato.ultima_cobranca_em, falou_em):
            if candidato and candidato > referencia:
                referencia = candidato

        enviadas = contrato.cobrancas_enviadas or 0
        espera = intervalos[min(enviadas, len(intervalos) - 1)]

        if agora - referencia >= timedelta(minutes=espera):
            devidos.append((contrato, conversa, lead))

        if len(devidos) >= LOTE:
            break

    return devidos


async def processar(db: AsyncSession, agora: Optional[datetime] = None) -> dict:
    """
    Uma rodada. Devolve o que fez, para o log e para os testes.
    """
    # Import local, como no follow-up: o serviço precisa ser importável em
    # teste sem arrastar o cliente HTTP da Evolution junto.
    from app.services.whatsapp_service import whatsapp_service

    agora = agora or datetime.utcnow()
    enviadas = falhas = renovados = 0

    for contrato, conversa, lead in await contratos_para_cobrar(db, agora):
        tentativa = (contrato.cobrancas_enviadas or 0) + 1

        # Link vencido não pode ser cobrado com o link vencido. Com os
        # intervalos padrão isto não acontece (4 dias de cobrança contra 7 de
        # validade), mas basta alguém alargar um intervalo no `.env` para a
        # cobrança passar a mandar endereço morto — e o defeito apareceria
        # como "o cliente diz que o link não abre", que ninguém liga à
        # configuração.
        if assinatura_service.expirado(contrato, agora):
            assinatura_service.preparar_para_envio(contrato, agora)
            # `preparar_para_envio` marca data_envio, que é a referência do
            # relógio. Renovar não pode reiniciar a contagem: seria uma
            # cobrança perpétua.
            contrato.data_envio = agora
            renovados += 1

        texto = texto_da_cobranca(
            tentativa,
            lead.nome if lead else None,
            contrato.link_assinatura,
            contrato.token_expira_em,
        )

        try:
            envio = await whatsapp_service.send_message(
                phone_number=conversa.phone_number, message_text=texto
            )
            if not envio.get("success"):
                raise RuntimeError("a Evolution não confirmou o envio")
        except Exception as e:
            # Falha de envio não gasta a tentativa: a pessoa não recebeu nada,
            # e queimar a cota faria a cobrança terminar sem que ninguém
            # tivesse sido cobrado.
            logger.warning(
                f"⚠️ Cobrança não enviada para {conversa.phone_number}: {e}"
            )
            falhas += 1
            continue

        db.add(
            Message(
                conversation_id=conversa.id,
                remetente="sistema",
                conteudo=texto,
                timestamp=datetime.utcnow(),
            )
        )
        contrato.cobrancas_enviadas = tentativa
        contrato.ultima_cobranca_em = datetime.utcnow()
        conversa.data_ultima_msg = datetime.utcnow()

        if lead is not None:
            db.add(
                LeadTimeline(
                    lead_id=lead.id,
                    status_anterior=lead.status_funil,
                    status_novo=lead.status_funil,
                    mudado_por=None,
                    motivo=f"Cobrança de assinatura {tentativa}",
                    timestamp=datetime.utcnow(),
                )
            )

        enviadas += 1

    await db.commit()
    return {"enviadas": enviadas, "falhas": falhas, "links_renovados": renovados}


async def rodada() -> dict:
    """
    O que o agendador chama.

    Sessão própria, porque roda fora de qualquer requisição. E qualquer
    exceção morre aqui: um erro nesta rodada não pode derrubar o scheduler e
    levar junto o follow-up e a agregação de métricas.
    """
    if not settings.cobranca_habilitada:
        return {"enviadas": 0, "falhas": 0, "links_renovados": 0, "desligada": True}

    if not dentro_do_horario():
        return {
            "enviadas": 0, "falhas": 0, "links_renovados": 0,
            "fora_do_horario": True,
        }

    try:
        async with AsyncSessionLocal() as db:
            resultado = await processar(db)
    except Exception as e:
        logger.error(f"❌ Rodada de cobrança falhou: {e}")
        return {"enviadas": 0, "falhas": 0, "links_renovados": 0, "erro": str(e)}

    if resultado["enviadas"]:
        logger.info(f"📄 Cobrança de assinatura: {resultado['enviadas']} enviada(s)")
    return resultado
