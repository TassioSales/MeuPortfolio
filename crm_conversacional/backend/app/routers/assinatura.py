"""
A página pública de assinatura.

**Este é o único roteador do sistema sem autenticação**, e é por ele que um
estranho chegaria a um contrato. Três decisões seguram a porta:

1. **O token é a credencial.** 256 bits, entregues só no WhatsApp do cliente,
   com prazo. Não há listagem, não há busca, não há id sequencial: ou se tem o
   endereço exato, ou não se chega a lugar nenhum.
2. **Contrato vencido, assinado ou inexistente respondem igual** — 404. Dizer
   "existe mas venceu" para um token adivinhado confirmaria que ele existe.
   Para quem **tem** o link legítimo a página distingue os casos, porque aí o
   token já provou quem é.
3. **Limite por IP.** Um endpoint público que lê o banco a cada visita é um
   endpoint que alguém vai varrer.

O que a página devolve é o mínimo: o texto do contrato, o nome de quem assina
e o do escritório. Nada do dossiê, nada do parecer, nada do caso — quem tem o
link tem o contrato, não o prontuário.
"""

import asyncio
from datetime import datetime
from typing import Optional, Set

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.db.models import Contrato, Conversation, Lead, Message
from app.services import assinatura_service, contrato_service, escritorio_service
from app.services.rate_limiter import RateLimiter
from app.services.whatsapp_service import whatsapp_service
from app.utils.exceptions import NotFoundException, ValidationException
from app.utils.logger import logger

router = APIRouter(prefix="/api/v1/assinatura", tags=["assinatura"])

# Ver `_TAREFAS` no lead_processor: sem a referência forte, a coleta de lixo
# pode encerrar a tarefa no meio.
_TAREFAS: Set[asyncio.Task] = set()

# Generoso para gente e apertado para varredura: ninguém abre a própria página
# de assinatura trinta vezes por minuto, e quem faz isso não é gente.
#
# O segundo número é o de "tokens" do limitador, que nasceu para contar
# consumo de LLM. Aqui não há consumo a contar, então ele fica alto para não
# interferir — quem limita é a contagem de chamadas.
_limite = RateLimiter(max_calls_per_minute=30, max_tokens_per_minute=10**9)

TEXTO_DA_CONFIRMACAO = (
    "Recebemos sua assinatura, {nome}. ✅\n\n"
    "O contrato está registrado e uma via fica guardada com o escritório. "
    "A partir de agora seu caso segue com a nossa equipe — qualquer novidade, "
    "a gente avisa por aqui."
)


class ContratoParaAssinar(BaseModel):
    """O mínimo para a pessoa ler e decidir."""

    corpo: str
    nome_do_cliente: Optional[str] = None
    nome_do_escritorio: Optional[str] = None
    ja_assinado: bool = False
    assinado_em: Optional[datetime] = None
    assinado_por: Optional[str] = None


class Assinatura(BaseModel):
    nome: str = Field(min_length=3, max_length=255)
    # Caixa marcada, e obrigatoriamente `True`. Aceite é ato, não default: um
    # POST que assina sem esta linha assinaria por quem só abriu a página.
    aceite: bool
    # O rabisco do `<canvas>`, como `data:image/png;base64,...`. Opcional: um
    # navegador sem canvas, ou alguém que não conseguiu desenhar, ainda assina
    # — o que prova a assinatura é a trilha, não o desenho.
    #
    # O teto aqui é o dobro do limite em bytes: o base64 cresce 4/3, e o
    # `png_da_assinatura` recusa o que passar do tamanho real.
    assinatura_png: Optional[str] = Field(default=None, max_length=800_000)


async def _contrato_do_token(token: str, db: AsyncSession) -> Contrato:
    """
    Acha o contrato pelo token, ou 404.

    Token vazio nunca casa: a coluna aceita nulo (contrato ainda não enviado),
    e `WHERE token IS NULL` devolveria justamente os que não deveriam ser
    alcançáveis.
    """
    if not token or not token.strip():
        raise NotFoundException("Contrato")

    resultado = await db.execute(
        select(Contrato).where(Contrato.token_assinatura == token)
    )
    contrato = resultado.scalars().first()
    if contrato is None:
        raise NotFoundException("Contrato")
    return contrato


@router.get("/{token}", response_model=ContratoParaAssinar)
async def abrir(token: str, request: Request):
    """
    O que o cliente vê ao abrir o link.

    Contrato já assinado **não** vira 404: quem assinou e volta ao link quer
    ver que assinou, e mandá-lo para uma tela de erro é fazer a pessoa achar
    que a assinatura se perdeu.
    """
    await _limite.check(f"assinatura:{assinatura_service.ip_do_pedido(request)}")
    await _limite.track(f"assinatura:{assinatura_service.ip_do_pedido(request)}", 0)

    async with AsyncSessionLocal() as db:
        contrato = await _contrato_do_token(token, db)

        if assinatura_service.ja_assinado(contrato):
            return ContratoParaAssinar(
                corpo=contrato.corpo,
                ja_assinado=True,
                assinado_em=contrato.data_assinatura,
                assinado_por=contrato.assinado_nome,
                nome_do_escritorio=await _nome_do_escritorio(db),
            )

        if assinatura_service.expirado(contrato):
            # 404 e não 410: para quem adivinhou o token, "venceu" é confirmação
            # de que existe.
            raise NotFoundException("Contrato")

        lead = (
            await db.execute(select(Lead).where(Lead.id == contrato.lead_id))
        ).scalars().first()

        return ContratoParaAssinar(
            corpo=contrato.corpo,
            nome_do_cliente=getattr(lead, "nome", None),
            nome_do_escritorio=await _nome_do_escritorio(db),
        )


@router.post("/{token}", response_model=ContratoParaAssinar)
async def assinar(token: str, entrada: Assinatura, request: Request):
    """
    Registra a assinatura e **absorve** o documento.

    O PDF com a folha de auditoria é gerado e guardado aqui, no mesmo commit.
    É o que faz o contrato deixar de depender de qualquer coisa externa: a
    partir deste ponto o link pode morrer, a pessoa pode sumir e o documento
    continua inteiro, dentro do banco do escritório.

    A confirmação no WhatsApp sai **depois** do commit, em tarefa própria: uma
    Evolution fora do ar não pode fazer uma assinatura já registrada parecer
    que falhou.
    """
    ip = assinatura_service.ip_do_pedido(request)
    await _limite.check(f"assinatura:{ip}")
    await _limite.track(f"assinatura:{ip}", 0)

    if not entrada.aceite:
        raise ValidationException("É preciso marcar o aceite para assinar.")

    async with AsyncSessionLocal() as db:
        contrato = await _contrato_do_token(token, db)

        if assinatura_service.ja_assinado(contrato):
            # Não é erro: é o segundo toque no botão, ou o link aberto de novo.
            # Recusar assustaria quem já assinou.
            return ContratoParaAssinar(
                corpo=contrato.corpo,
                ja_assinado=True,
                assinado_em=contrato.data_assinatura,
                assinado_por=contrato.assinado_nome,
                nome_do_escritorio=await _nome_do_escritorio(db),
            )

        if assinatura_service.expirado(contrato):
            raise NotFoundException("Contrato")

        assinatura_service.registrar_assinatura(
            contrato,
            nome=entrada.nome,
            ip=ip,
            user_agent=request.headers.get("user-agent"),
        )
        contrato.assinatura_imagem = assinatura_service.png_da_assinatura(
            entrada.assinatura_png
        )

        nome_do_escritorio = await _nome_do_escritorio(db)
        contrato.pdf_assinado = contrato_service.em_pdf(
            contrato.corpo,
            titulo="Contrato assinado",
            assinatura=_para_a_folha(contrato),
            cabecalho=(
                f"{nome_do_escritorio} — Contrato de honorários"
                if nome_do_escritorio
                else ""
            ),
            rabisco=contrato.assinatura_imagem,
        )

        lead_id = contrato.lead_id
        nome = contrato.assinado_nome
        await db.commit()

    _agendar_confirmacao(lead_id, nome)

    async with AsyncSessionLocal() as db:
        contrato = await _contrato_do_token(token, db)
        return ContratoParaAssinar(
            corpo=contrato.corpo,
            ja_assinado=True,
            assinado_em=contrato.data_assinatura,
            assinado_por=contrato.assinado_nome,
            nome_do_escritorio=await _nome_do_escritorio(db),
        )


async def _nome_do_escritorio(db: AsyncSession) -> Optional[str]:
    config = await escritorio_service.obter(db)
    return getattr(config, "nome", None) if config else None


def _para_a_folha(contrato: Contrato) -> dict:
    """Os campos da folha de auditoria, já formatados para leitura humana."""
    from app.utils.fuso import em_brasilia

    return {
        "nome": contrato.assinado_nome,
        "quando": em_brasilia(contrato.data_assinatura),
        "ip": contrato.assinado_ip,
        "dispositivo": contrato.assinado_user_agent,
        "contrato_id": contrato.id,
        "hash": contrato.hash_documento,
    }


def _agendar_confirmacao(lead_id: str, nome: Optional[str]) -> Optional[asyncio.Task]:
    """Larga a confirmação para rodar sozinha e devolve o controle na hora."""
    tarefa = asyncio.create_task(_confirmar_no_whatsapp(lead_id, nome))
    _TAREFAS.add(tarefa)
    tarefa.add_done_callback(_TAREFAS.discard)
    return tarefa


async def _confirmar_no_whatsapp(lead_id: str, nome: Optional[str]) -> None:
    """
    Avisa no chat que a assinatura chegou, e grava a mensagem na conversa.

    Sem isto o cliente assina e fica no escuro — clicou num botão e não
    aconteceu nada visível no lugar onde ele conversa com o escritório. E o
    escritório perde o registro: a conversa não contaria que houve assinatura.

    Falha aqui não desfaz nada. O contrato já está assinado e guardado; o que
    se perde é o aviso, e ele aparece no log.
    """
    try:
        async with AsyncSessionLocal() as db:
            lead = (
                await db.execute(select(Lead).where(Lead.id == lead_id))
            ).scalars().first()
            if lead is None:
                logger.warning(f"⚠️ Lead {lead_id} sumiu antes da confirmação")
                return

            conversa = (
                await db.execute(
                    select(Conversation).where(Conversation.id == lead.conversation_id)
                )
            ).scalars().first()
            if conversa is None:
                logger.warning(f"⚠️ Conversa do lead {lead_id} não encontrada")
                return

            primeiro_nome = (nome or lead.nome or "").strip().split(" ")[0]
            texto = TEXTO_DA_CONFIRMACAO.format(nome=primeiro_nome or "tudo certo")

            envio = await whatsapp_service.send_message(
                phone_number=conversa.phone_number, message_text=texto
            )
            if not envio.get("success"):
                logger.warning(
                    f"⚠️ Evolution não confirmou o aviso de assinatura ao lead {lead_id}"
                )
                return

            db.add(
                Message(
                    conversation_id=conversa.id,
                    # Nem cliente nem IA: é o sistema avisando. O histórico do
                    # modelo trata tudo que não é "user" como o escritório
                    # falando, então entra no lugar certo.
                    remetente="sistema",
                    conteudo=texto,
                    timestamp=datetime.utcnow(),
                )
            )
            conversa.data_ultima_msg = datetime.utcnow()
            await db.commit()

        logger.info(f"✅ Confirmação de assinatura enviada ao lead {lead_id}")
    except Exception as e:
        logger.error(f"❌ Falha ao confirmar a assinatura do lead {lead_id}: {e}")
