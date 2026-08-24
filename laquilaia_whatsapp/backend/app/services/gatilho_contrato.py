"""
Quem decide que chegou a hora do contrato.

O dono foi explícito: *"a IA tem que gerar e enviar, não o advogado"*. Isto é
o que faz isso acontecer — e o que **não** faz.

**O modelo não decide.** Quem dispara é regra, checada em Python, sobre dados
que já existem no banco. Um LLM com poder de emitir contrato com honorários é
um LLM que um dia emite para a pessoa errada, e "o modelo achou que era hora"
não é defesa que se dê a um cliente. O modelo faz a parte dele — conversar e
coletar; a decisão de emitir é aritmética.

**O gatilho é depois do parecer, não da qualificação.** É o parecer que
estabelece o porte econômico, e emitir contrato antes dele significaria mandar
contrato para casos que o próprio escritório recusaria. São uns noventa
segundos de diferença e eles decidem se o produto é útil ou constrangedor.

**Nasce desligado.** Ver `settings.contrato_automatico`.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import (
    Caso,
    Contrato,
    Conversation,
    Lead,
    LeadTimeline,
    Message,
    ModeloDeContrato,
)
from app.services import coleta_service
from app.utils.logger import logger

# Vereditos de porte que impedem o contrato.
#
# Só `abaixo_do_piso` barra. `indeterminado` **não** barra, e a diferença é a
# mesma que o projeto já assume no funil: parecer sem porte não é caso
# inviável, é caso que ninguém dimensionou. Barrar o indeterminado faria o
# gatilho não disparar quase nunca.
VETADOS = ("abaixo_do_piso",)

# Motivos de não disparar que alguém consegue resolver — e que por isso
# precisam ser vistos. "Já tem contrato" e "já em coleta" ficam de fora: são o
# funcionamento normal, e avisar sobre eles encheria o log de ruído até
# ninguém mais ler.
_CORRIGIVEIS = {
    "sem caso registrado",
    "nenhum modelo de contrato ativo",
    "lead não qualificado",
}

ABERTURA = (
    "{saudacao}Tenho uma boa notícia: seu caso foi analisado pelo escritório e "
    "**nós vamos aceitar**. 🎉\n\n"
    "Para preparar o contrato eu preciso de alguns dados seus — os mesmos que "
    "vão na procuração. São rapidinhos, e eu vou perguntando um de cada vez.\n\n"
    "Pode começar pelo seu CPF?"
)


async def pode_abrir_coleta(
    db: AsyncSession, lead: Lead, caso: Optional[Caso]
) -> tuple:
    """
    Se este lead deve entrar na coleta agora. Devolve (pode, motivo).

    O motivo existe para o log: "não disparou" sem explicação é o tipo de
    silêncio que faz alguém achar que o recurso não funciona.
    """
    if not settings.contrato_automatico:
        return False, "contrato automático desligado"

    if caso is None:
        return False, "sem caso registrado"

    if (caso.viabilidade or "") in VETADOS:
        return False, f"viabilidade {caso.viabilidade}"

    if (lead.status_funil or "") == "nao_qualificado":
        return False, "lead não qualificado"

    conversa = (
        await db.execute(
            select(Conversation).where(Conversation.id == lead.conversation_id)
        )
    ).scalars().first()

    if conversa is None:
        return False, "sem conversa"
    if conversa.status != "ativa":
        # Pausada quer dizer que um humano assumiu; encerrada, que acabou. Um
        # robô anunciando "vamos aceitar seu caso" por cima do atendimento de
        # gente é pior que não anunciar nada.
        return False, f"conversa {conversa.status}"
    if conversa.fase != coleta_service.FASE_TRIAGEM:
        return False, f"conversa já em {conversa.fase}"

    modelo = (
        await db.execute(
            select(ModeloDeContrato.id).where(ModeloDeContrato.ativo.is_(True))
        )
    ).scalars().first()
    if modelo is None:
        # Sem modelo ativo o contrato sairia vazio. Melhor não prometer.
        return False, "nenhum modelo de contrato ativo"

    ja_tem = (
        await db.execute(
            select(func.count(Contrato.id)).where(Contrato.lead_id == lead.id)
        )
    ).scalar()
    if ja_tem:
        return False, "lead já tem contrato"

    return True, "ok"


async def abrir_coleta(db: AsyncSession, lead: Lead, caso: Optional[Caso]) -> bool:
    """
    Vira a chave e anuncia ao cliente, se as condições permitirem.

    A mensagem de abertura é **texto fixo**, não gerada pelo modelo. Ela diz
    que o escritório aceitou o caso — um compromisso — e não é hora de
    descobrir como o modelo resolveu formular isso hoje. Dali em diante ele
    assume, com o bloco de coleta no prompt.

    Não faz commit: quem chama está dentro de uma transação.
    """
    from app.services.whatsapp_service import whatsapp_service

    pode, motivo = await pode_abrir_coleta(db, lead, caso)
    if not pode:
        # Motivo corrigível sai em `warning`, não em `debug`.
        #
        # Um recurso que não faz nada e não diz por quê é o pior tipo de
        # defeito: o dono liga `CONTRATO_AUTOMATICO`, conduz uma triagem
        # inteira, nada acontece, e a única explicação está numa linha de
        # `debug` que ninguém tem ligada. Os motivos abaixo são todos
        # resolvíveis por quem opera — merecem aparecer.
        if motivo in _CORRIGIVEIS or motivo.startswith("viabilidade "):
            logger.warning(
                f"⚠️ Contrato automático não disparou para o lead {lead.id}: "
                f"{motivo}. Rode `python -m scripts.diagnostico_contrato "
                f"--telefone {lead.phone_number}` para o quadro completo."
            )
        else:
            logger.debug(f"⏭️ Coleta não aberta para o lead {lead.id}: {motivo}")
        return False

    conversa = (
        await db.execute(
            select(Conversation).where(Conversation.id == lead.conversation_id)
        )
    ).scalars().first()

    primeiro_nome = (lead.nome or "").strip().split(" ")[0]
    texto = ABERTURA.format(saudacao=f"Oi, {primeiro_nome}! " if primeiro_nome else "")

    try:
        envio = await whatsapp_service.send_message(
            phone_number=conversa.phone_number, message_text=texto
        )
        if not envio.get("success"):
            raise RuntimeError("a Evolution não confirmou o envio")
    except Exception as e:
        # A fase não vira se a mensagem não saiu. Senão o agente entraria em
        # coleta em silêncio e o cliente receberia, do nada, uma pergunta
        # sobre CPF sem nunca ter sido avisado de que o caso foi aceito.
        logger.warning(f"⚠️ Abertura da coleta não enviada ao lead {lead.id}: {e}")
        return False

    conversa.fase = coleta_service.FASE_COLETA
    conversa.data_ultima_msg = datetime.utcnow()
    db.add(
        Message(
            conversation_id=conversa.id,
            # Nem cliente nem resposta do modelo: é o sistema anunciando uma
            # decisão do escritório.
            remetente="sistema",
            conteudo=texto,
            timestamp=datetime.utcnow(),
        )
    )
    db.add(
        LeadTimeline(
            lead_id=lead.id,
            status_anterior=lead.status_funil,
            status_novo=lead.status_funil,
            mudado_por=None,
            motivo="Coleta de dados para contrato aberta",
            timestamp=datetime.utcnow(),
        )
    )

    logger.info(f"📝 Coleta aberta para o lead {lead.id}")
    return True


async def talvez_emitir(db: AsyncSession, lead: Lead) -> Optional[str]:
    """
    Dados completos? Gera o contrato e manda o link. Devolve o id, ou `None`.

    Este é o ponto em que o produto faz o que o dono pediu sem ninguém do
    escritório encostar: a agente coletou conversando, e a emissão sai daqui.

    **A emissão é idempotente por construção.** Um contrato já existente para
    o lead barra a segunda: o cliente pode confirmar o endereço duas vezes, e
    dois contratos com honorários indo para o mesmo WhatsApp é o pior desfecho
    possível deste recurso.

    Não faz commit — quem chama está numa transação.
    """
    from app.routers import contratos as rotas
    from app.services import assinatura_service, contrato_service
    from app.services.whatsapp_service import whatsapp_service

    if not settings.contrato_automatico:
        return None

    dados = await coleta_service.dados_do_lead(db, lead.id)
    if not coleta_service.esta_completo(dados):
        faltam = coleta_service.o_que_falta(dados)
        logger.debug(f"⏭️ Contrato do lead {lead.id} ainda falta: {', '.join(faltam)}")
        return None

    ja_tem = (
        await db.execute(
            select(func.count(Contrato.id)).where(Contrato.lead_id == lead.id)
        )
    ).scalar()
    if ja_tem:
        return None

    modelo = (
        await db.execute(
            select(ModeloDeContrato).where(ModeloDeContrato.ativo.is_(True))
        )
    ).scalars().first()
    if modelo is None:
        logger.warning(
            f"⚠️ Dados do lead {lead.id} completos e nenhum modelo ativo — "
            "o contrato não foi emitido"
        )
        return None

    conversa = (
        await db.execute(
            select(Conversation).where(Conversation.id == lead.conversation_id)
        )
    ).scalars().first()
    if conversa is None or conversa.status != "ativa":
        return None

    # O mesmo caminho da emissão manual, para não haver duas maneiras de
    # montar um contrato que possam divergir.
    contrato = await rotas.montar_contrato(
        db=db, lead=lead, modelo=modelo, gerado_por=None
    )
    db.add(contrato)
    await db.flush()

    link = assinatura_service.preparar_para_envio(contrato)
    texto = rotas.TEXTO_DO_ENVIO.format(
        saudacao=(
            f"Oi, {lead.nome.strip().split(' ')[0]}! " if lead.nome else ""
        ),
        link=link,
        dias=assinatura_service.DIAS_DE_VALIDADE,
    )

    try:
        envio = await whatsapp_service.send_message(
            phone_number=conversa.phone_number, message_text=texto
        )
        if not envio.get("success"):
            raise RuntimeError("a Evolution não confirmou o envio")
    except Exception as e:
        # Sem entrega, sem contrato. Um contrato marcado como enviado que
        # ninguém recebeu entra na fila de cobrança e cobra uma pessoa por um
        # documento que ela nunca viu.
        logger.warning(f"⚠️ Contrato do lead {lead.id} não enviado: {e}")
        await db.rollback()
        return None

    db.add(
        Message(
            conversation_id=conversa.id,
            remetente="sistema",
            conteudo=texto,
            timestamp=datetime.utcnow(),
        )
    )
    conversa.fase = coleta_service.FASE_CONTRATADO
    conversa.data_ultima_msg = datetime.utcnow()
    db.add(
        LeadTimeline(
            lead_id=lead.id,
            status_anterior=lead.status_funil,
            status_novo=lead.status_funil,
            mudado_por=None,
            motivo="Contrato emitido e enviado automaticamente",
            timestamp=datetime.utcnow(),
        )
    )

    logger.info(f"📄 Contrato {contrato.id} emitido e enviado sozinho ao lead {lead.id}")
    return contrato.id
