"""
A tela de configuração do escritório.

Leitura liberada a quem tem conta — o operador precisa ver o telefone do
suporte para repassá-lo quando for ele quem estiver atendendo. Escrita só do
administrador: mudar o telefone do escritório muda o que a IA diz a **todo**
cliente, e isso não é decisão de quem está no plantão.
"""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session
from app.services import escritorio_service
from app.utils.auth_middleware import get_current_user, require_admin
from app.utils.logger import logger

router = APIRouter(prefix="/api/v1/escritorio", tags=["escritorio"])


class EscritorioBase(BaseModel):
    nome: Optional[str] = Field(default=None, max_length=255)
    cnpj: Optional[str] = Field(default=None, max_length=32)
    oab_responsavel: Optional[str] = Field(default=None, max_length=64)
    fundador: Optional[str] = Field(default=None, max_length=255)
    endereco: Optional[str] = Field(default=None, max_length=2000)
    email: Optional[str] = Field(default=None, max_length=255)
    telefone: Optional[str] = Field(default=None, max_length=32)
    telefone_suporte: Optional[str] = Field(default=None, max_length=32)
    horario_atendimento: Optional[str] = Field(default=None, max_length=255)
    site: Optional[str] = Field(default=None, max_length=255)
    instagram: Optional[str] = Field(default=None, max_length=255)


class EscritorioResponse(EscritorioBase):
    class Config:
        from_attributes = True


@router.get("", response_model=EscritorioResponse)
async def ler(
    _: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    O que está configurado hoje.

    Nunca 404: escritório sem nada preenchido é o estado inicial, e o
    formulário precisa abrir. Devolve todos os campos nulos.
    """
    config = await escritorio_service.obter(db)
    if config is None:
        return EscritorioResponse()
    return EscritorioResponse.model_validate(config)


@router.put("", response_model=EscritorioResponse)
async def salvar(
    dados: EscritorioBase,
    admin_id: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Grava a configuração inteira.

    PUT e não PATCH de propósito: o formulário manda todos os campos, e
    apagar um campo é uma edição legítima — com PATCH, limpar o telefone
    seria indistinguível de não mexer nele.

    Campo em branco vira `None`, e não string vazia: quem monta o prompt
    ignora o que é falsy, mas `""` no banco é lixo que aparece em relatório e
    exportação como se fosse valor.
    """
    config = await escritorio_service.obter_ou_criar(db)

    for campo, valor in dados.model_dump().items():
        limpo = valor.strip() if isinstance(valor, str) else valor
        setattr(config, campo, limpo or None)

    await db.commit()
    await db.refresh(config)

    logger.info(f"🏢 Configuração do escritório atualizada por {admin_id}")
    return EscritorioResponse.model_validate(config)
