"""
Cutucar quem sumiu no meio da triagem, e desistir na hora certa.

O sintoma era este: o agente pergunta o salário, a pessoa não responde, e a
conversa fica ali para sempre. O lead ocupa a primeira coluna do funil
indefinidamente, e ninguém sabe se ele desistiu ou se só não viu a mensagem —
as duas coisas têm a mesma aparência no painel.

Três tentativas e encerra. O escalonamento (15 min, 2h, 24h por padrão) não é
detalhe de configuração: quem não respondeu em quinze minutos provavelmente
está trabalhando, e quem não respondeu em dois dias foi embora. Três cutucadas
de cinco em cinco minutos é o que faz a pessoa bloquear o número — e aí o
escritório perde o lead **e** o número.

O texto do follow-up repete a pergunta que ficou pendente, e essa é a única
razão de ele funcionar. "Oi, ainda está aí?" é o que todo robô manda; repetir
a pergunta é o que uma pessoa faria, custa zero chamada de modelo, e a
resposta vem porque a pessoa lembra do que era.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import AsyncSessionLocal
from app.db.models import Conversation, Lead, LeadTimeline, Message
from app.utils.logger import logger

# Quantas conversas processar por rodada.
#
# Um teto existe porque a rodada roda dentro do scheduler do app: mil envios
# em sequência prenderiam o worker por minutos, e mensagens de cliente de
# verdade ficariam esperando atrás disso.
LOTE = 50


def _agora_local() -> datetime:
    """A hora do escritório, não a do servidor."""
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo(settings.followup_fuso))
    except Exception:
        # Fuso mal configurado não pode derrubar o follow-up inteiro; cai no
        # relógio do servidor, que em produção é UTC.
        logger.warning(f"⚠️ Fuso {settings.followup_fuso!r} desconhecido; usando UTC")
        return datetime.now(timezone.utc)


def dentro_do_horario(agora: Optional[datetime] = None) -> bool:
    """
    Se é hora de escrever para alguém.

    Mensagem automática às 3h da manhã queima a reputação do número inteiro, e
    o WhatsApp não perdoa denúncia de spam. Fora da janela o follow-up não é
    perdido — ele espera, e sai na primeira rodada do dia seguinte.
    """
    hora = (agora or _agora_local()).hour
    return settings.followup_hora_inicio <= hora < settings.followup_hora_fim


def texto_do_followup(pergunta_pendente: str, tentativa: int, nome: Optional[str]) -> str:
    """
    O que vai ser mandado.

    Repete a pergunta em vez de perguntar se a pessoa está aí. A última
    tentativa avisa que é a última — dar a saída explícita é mais honesto que
    sumir, e quem ainda tem interesse costuma responder justamente aí.
    """
    tratamento = f"Oi, {nome.split()[0]}!" if nome else "Oi!"
    trecho = pergunta_pendente.strip()

    if tentativa == 1:
        return f"{tratamento} Ficou faltando só isto aqui:\n\n{trecho}"
    if tentativa == 2:
        return (
            f"{tratamento} Passando de novo para não perder seu caso.\n\n{trecho}"
        )
    return (
        f"{tratamento} Última tentativa por aqui — se não der agora, tudo bem, "
        f"é só me chamar quando puder.\n\n{trecho}"
    )


TEXTO_DE_ENCERRAMENTO = (
    "Vou encerrar por aqui, tudo bem? Seu contato fica guardado com a gente — "
    "se quiser retomar é só mandar uma mensagem a qualquer momento."
)


async def conversas_para_cutucar(
    db: AsyncSession, agora: Optional[datetime] = None
) -> List[Tuple[Conversation, Message, Optional[Lead]]]:
    """
    As conversas em que o cliente deve resposta há tempo demais.

    O critério é o espelho do alerta de pendência: lá a **última** mensagem é
    do cliente e o escritório deve resposta; aqui a última é do agente e quem
    deve é o cliente.

    Conversa pausada fica de fora: um humano assumiu, e um robô cutucando por
    cima do atendimento de gente é pior que silêncio.
    """
    agora = agora or datetime.utcnow()
    intervalos = settings.followup_intervalos

    ultima = (
        select(
            Message.conversation_id.label("conversation_id"),
            func.max(Message.timestamp).label("quando"),
        )
        .group_by(Message.conversation_id)
        .subquery()
    )

    linhas = await db.execute(
        select(Conversation, Message, Lead)
        .join(ultima, ultima.c.conversation_id == Conversation.id)
        .join(
            Message,
            (Message.conversation_id == Conversation.id)
            & (Message.timestamp == ultima.c.quando),
        )
        .outerjoin(Lead, Lead.conversation_id == Conversation.id)
        .where(Conversation.status == "ativa")
        .where(Message.remetente == "assistant")
        .where(Conversation.followups_enviados <= len(intervalos))
        .order_by(ultima.c.quando)
        .limit(LOTE * 4)
    )

    devidas: List[Tuple[Conversation, Message, Optional[Lead]]] = []
    vistas = set()

    for conversa, mensagem, lead in linhas:
        if conversa.id in vistas:
            continue
        vistas.add(conversa.id)

        # O relógio conta do último contato — a mensagem do agente ou o
        # follow-up mais recente, o que for mais novo. Sem isso, as três
        # tentativas sairiam todas juntas assim que o primeiro prazo vencesse.
        referencia = mensagem.timestamp
        if conversa.ultimo_followup_em and conversa.ultimo_followup_em > referencia:
            referencia = conversa.ultimo_followup_em

        enviados = conversa.followups_enviados or 0
        espera = intervalos[min(enviados, len(intervalos) - 1)]

        if agora - referencia >= timedelta(minutes=espera):
            devidas.append((conversa, mensagem, lead))

        if len(devidas) >= LOTE:
            break

    return devidas


async def _registrar(db: AsyncSession, lead: Optional[Lead], motivo: str) -> None:
    """Deixa rastro na trilha do lead, quando há lead."""
    if lead is None:
        return
    db.add(
        LeadTimeline(
            lead_id=lead.id,
            status_anterior=lead.status_funil,
            status_novo=lead.status_funil,
            mudado_por=None,
            motivo=motivo,
            timestamp=datetime.utcnow(),
        )
    )


async def processar(db: AsyncSession, agora: Optional[datetime] = None) -> dict:
    """
    Uma rodada: cutuca quem está no prazo, encerra quem esgotou.

    Devolve o que fez, para o log e para os testes.
    """
    # O import fica aqui para o serviço poder ser importado em teste sem
    # arrastar o cliente HTTP da Evolution junto.
    from app.services.whatsapp_service import whatsapp_service

    agora = agora or datetime.utcnow()
    intervalos = settings.followup_intervalos
    enviados = encerrados = falhas = 0

    for conversa, mensagem, lead in await conversas_para_cutucar(db, agora):
        tentativa = (conversa.followups_enviados or 0) + 1
        esgotou = tentativa > len(intervalos)

        texto = (
            TEXTO_DE_ENCERRAMENTO
            if esgotou
            else texto_do_followup(
                mensagem.conteudo, tentativa, lead.nome if lead else None
            )
        )

        try:
            envio = await whatsapp_service.send_message(
                phone_number=conversa.phone_number, message_text=texto
            )
            if not envio.get("success"):
                raise RuntimeError("a Evolution não confirmou o envio")
        except Exception as e:
            # Falha de envio não pode gastar a tentativa: a pessoa não recebeu
            # nada, e queimar a cota faria a conversa ser encerrada sem que
            # ninguém tenha falado com ela.
            logger.warning(f"⚠️ Follow-up não enviado para {conversa.phone_number}: {e}")
            falhas += 1
            continue

        db.add(
            Message(
                conversation_id=conversa.id,
                remetente="assistant",
                conteudo=texto,
                timestamp=datetime.utcnow(),
            )
        )

        if esgotou:
            conversa.status = "encerrada"
            await _registrar(db, lead, "Encerrada por falta de retorno")
            encerrados += 1
            logger.info(f"🔚 Conversa {conversa.id} encerrada por falta de retorno")
        else:
            conversa.followups_enviados = tentativa
            conversa.ultimo_followup_em = datetime.utcnow()
            await _registrar(db, lead, f"Follow-up {tentativa} enviado")
            enviados += 1

        conversa.data_ultima_msg = datetime.utcnow()

    await db.commit()
    return {"enviados": enviados, "encerrados": encerrados, "falhas": falhas}


async def rodada() -> dict:
    """
    O que o agendador chama.

    Sessão própria, porque roda fora de qualquer requisição. E qualquer
    exceção morre aqui: um erro nesta rodada não pode derrubar o scheduler e
    levar junto a agregação de métricas.
    """
    if not settings.followup_habilitado:
        return {"enviados": 0, "encerrados": 0, "falhas": 0, "desligado": True}

    if not dentro_do_horario():
        return {"enviados": 0, "encerrados": 0, "falhas": 0, "fora_do_horario": True}

    try:
        async with AsyncSessionLocal() as db:
            resultado = await processar(db)
    except Exception as e:
        logger.error(f"❌ Rodada de follow-up falhou: {e}")
        return {"enviados": 0, "encerrados": 0, "falhas": 0, "erro": str(e)}

    if resultado["enviados"] or resultado["encerrados"]:
        logger.info(
            f"📨 Follow-up: {resultado['enviados']} enviado(s), "
            f"{resultado['encerrados']} conversa(s) encerrada(s)"
        )
    return resultado
