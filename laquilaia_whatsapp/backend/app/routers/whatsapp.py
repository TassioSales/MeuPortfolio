"""
Conexão do número de WhatsApp, pelo painel.

Até aqui o QR e o estado da instância só existiam no Manager da Evolution:
para reconectar o número o administrador precisava sair do sistema, abrir
outra ferramenta e saber que ela existe. Estas duas rotas trazem isso para
dentro.

São **proxy**, e de propósito: a chave da Evolution fica no servidor. Expor o
Manager ou a `EVOLUTION_API_KEY` ao navegador entregaria, junto, o poder de
mandar mensagem em nome do escritório.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from app.config import settings
from app.services.whatsapp_service import whatsapp_service
from app.utils.auth_middleware import require_admin

router = APIRouter(prefix="/api/v1/whatsapp", tags=["whatsapp"])


class EstadoDaConexao(BaseModel):
    """`conectado`, `conectando`, `desconectado`, `indisponivel` ou `desconhecido`."""

    estado: str
    instancia: str
    # Preenchido quando o estado não é um dos esperados, ou quando não deu para
    # falar com a Evolution. É o que distingue "o número caiu" de "a Evolution
    # caiu" — problemas diferentes, com donos diferentes.
    detalhe: Optional[str] = None


class QrCode(BaseModel):
    """O QR para parear, e o código de pareamento quando a Evolution o envia."""

    qrcode: Optional[str] = None
    codigo: Optional[str] = None
    detalhe: Optional[str] = None


@router.get("/status", response_model=EstadoDaConexao)
async def status_da_conexao(_: str = Depends(require_admin)):
    """Se o número está no ar. Só administrador: é configuração, não atendimento."""
    resultado = await whatsapp_service.estado_da_conexao()
    return EstadoDaConexao(
        estado=resultado["estado"],
        instancia=settings.evolution_instance_name,
        detalhe=resultado.get("detalhe"),
    )


class ResultadoDaDesconexao(BaseModel):
    """O que aconteceu com o pedido de desconectar."""

    desconectado: bool
    detalhe: Optional[str] = None


@router.post("/desconectar", response_model=ResultadoDaDesconexao)
async def desconectar(_: str = Depends(require_admin)):
    """
    Despareia o número.

    Derruba o atendimento: enquanto ninguém ler o QR de novo, nenhuma mensagem
    chega ao agente. Por isso é `POST` e não `GET` — um `GET` seria disparado
    por um pré-carregamento de link ou por um crawler de extensão.
    """
    resultado = await whatsapp_service.desconectar()
    return ResultadoDaDesconexao(**resultado)


@router.get("/qrcode", response_model=QrCode)
async def qrcode(_: str = Depends(require_admin)):
    """
    O QR para parear o número.

    Vem vazio quando a instância já está conectada — não é erro, é a resposta
    certa para "já está pareado".
    """
    resultado = await whatsapp_service.qrcode()
    return QrCode(**resultado)
