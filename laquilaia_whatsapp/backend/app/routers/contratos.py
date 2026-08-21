"""
Contrato: o modelo que o advogado escreve e o documento que sai dele.

Três coisas moram aqui, e a separação é deliberada:

1. **Modelos** — o texto com lacunas. Escrita só do administrador: o corpo
   contém as cláusulas e o percentual de honorários, que são compromisso
   comercial do escritório. Leitura liberada, porque quem gera o contrato
   precisa ver o que vai sair antes de mandar ao cliente.
2. **Dados do contrato** — CPF, RG, estado civil, endereço. Não vêm da
   triagem; entram aqui, à mão ou (numa próxima etapa) pela conversa.
3. **Contratos emitidos** — o texto já preenchido, congelado.

Não há endpoint de assinatura: enquanto o provedor não estiver contratado,
`link_assinatura` e `data_assinatura` existem no banco e ficam nulos. Fingir
uma assinatura seria pior do que não ter nenhuma.
"""

import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session
from app.db.models import (
    Caso,
    Contrato,
    Conversation,
    DadosDoContrato,
    Lead,
    LeadDetails,
    Message,
    ModeloDeContrato,
)
from app.services import assinatura_service, contrato_service, escritorio_service
from app.services.whatsapp_service import whatsapp_service
from app.utils.auth_middleware import get_current_user, require_admin
from app.utils.exceptions import NotFoundException, ValidationException
from app.utils.logger import logger

router = APIRouter(prefix="/api/v1/contratos", tags=["contratos"])


# ---------------------------------------------------------------- esquemas

class ModeloEntrada(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    corpo: str = Field(min_length=1)
    ativo: bool = False


class ModeloResponse(BaseModel):
    id: str
    nome: str
    corpo: str
    ativo: bool
    data_atualizacao: Optional[datetime] = None

    class Config:
        from_attributes = True


class VariavelResponse(BaseModel):
    nome: str
    descricao: str


class DadosEntrada(BaseModel):
    cpf: Optional[str] = Field(default=None, max_length=14)
    rg: Optional[str] = Field(default=None, max_length=30)
    nacionalidade: Optional[str] = Field(default=None, max_length=60)
    estado_civil: Optional[str] = Field(default=None, max_length=40)
    profissao: Optional[str] = Field(default=None, max_length=120)
    endereco: Optional[str] = Field(default=None, max_length=2000)
    cep: Optional[str] = Field(default=None, max_length=9)
    cidade: Optional[str] = Field(default=None, max_length=120)
    uf: Optional[str] = Field(default=None, max_length=2)


class DadosResponse(DadosEntrada):
    class Config:
        from_attributes = True


class ContratoResponse(BaseModel):
    id: str
    lead_id: str
    modelo_id: Optional[str] = None
    corpo: str
    status: str
    link_assinatura: Optional[str] = None
    token_expira_em: Optional[datetime] = None
    data_envio: Optional[datetime] = None
    data_assinatura: Optional[datetime] = None
    assinado_nome: Optional[str] = None
    hash_documento: Optional[str] = None
    data_criacao: Optional[datetime] = None

    class Config:
        from_attributes = True


class GerarEntrada(BaseModel):
    # Sem modelo escolhido, usa o ativo. A tela normalmente não escolhe — quem
    # gera contrato quer o que vale hoje.
    modelo_id: Optional[str] = None


# ---------------------------------------------------------------- modelos

@router.get("/variaveis", response_model=List[VariavelResponse])
async def listar_variaveis(_: str = Depends(get_current_user)):
    """
    O que se pode escrever entre chaves no modelo.

    Vem do backend em vez de estar escrito na tela para não haver duas listas
    que possam divergir — a que o editor mostra e a que o preenchimento
    conhece.
    """
    return [
        VariavelResponse(nome=nome, descricao=descricao)
        for nome, descricao in contrato_service.VARIAVEIS.items()
    ]


@router.get("/modelos", response_model=List[ModeloResponse])
async def listar_modelos(
    _: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """O ativo primeiro; depois os demais, do mais recente para o mais antigo."""
    resultado = await db.execute(
        select(ModeloDeContrato).order_by(
            ModeloDeContrato.ativo.desc(), ModeloDeContrato.data_criacao.desc()
        )
    )
    return [ModeloResponse.model_validate(m) for m in resultado.scalars().all()]


async def _desativar_os_outros(db: AsyncSession, manter_id: str) -> None:
    """
    Só um modelo ativo por vez.

    Sem isto, `gerar` teria de escolher entre dois — e escolheria pela ordem
    do banco, que não é escolha nenhuma.
    """
    await db.execute(
        update(ModeloDeContrato)
        .where(ModeloDeContrato.id != manter_id, ModeloDeContrato.ativo.is_(True))
        .values(ativo=False)
    )


@router.post("/modelos", response_model=ModeloResponse, status_code=201)
async def criar_modelo(
    entrada: ModeloEntrada,
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    desconhecidas = contrato_service.variaveis_desconhecidas(entrada.corpo)
    if desconhecidas:
        raise ValidationException(
            "Variáveis que o sistema não sabe preencher: " + ", ".join(desconhecidas)
        )

    ja_existe = await db.execute(
        select(ModeloDeContrato.id).where(ModeloDeContrato.nome == entrada.nome)
    )
    if ja_existe.scalars().first() is not None:
        raise ValidationException("Já existe um modelo com esse nome")

    modelo = ModeloDeContrato(
        nome=entrada.nome, corpo=entrada.corpo, ativo=entrada.ativo
    )
    db.add(modelo)
    await db.flush()
    if entrada.ativo:
        await _desativar_os_outros(db, modelo.id)
    await db.commit()
    await db.refresh(modelo)
    logger.info(f"📄 Modelo de contrato criado: {modelo.nome}")
    return ModeloResponse.model_validate(modelo)


@router.put("/modelos/{modelo_id}", response_model=ModeloResponse)
async def atualizar_modelo(
    modelo_id: str,
    entrada: ModeloEntrada,
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    desconhecidas = contrato_service.variaveis_desconhecidas(entrada.corpo)
    if desconhecidas:
        raise ValidationException(
            "Variáveis que o sistema não sabe preencher: " + ", ".join(desconhecidas)
        )

    resultado = await db.execute(
        select(ModeloDeContrato).where(ModeloDeContrato.id == modelo_id)
    )
    modelo = resultado.scalars().first()
    if modelo is None:
        raise NotFoundException("Modelo")

    conflito = await db.execute(
        select(ModeloDeContrato.id).where(
            ModeloDeContrato.nome == entrada.nome, ModeloDeContrato.id != modelo_id
        )
    )
    if conflito.scalars().first() is not None:
        raise ValidationException("Já existe um modelo com esse nome")

    modelo.nome = entrada.nome
    modelo.corpo = entrada.corpo
    modelo.ativo = entrada.ativo
    if entrada.ativo:
        await _desativar_os_outros(db, modelo.id)
    await db.commit()
    await db.refresh(modelo)
    return ModeloResponse.model_validate(modelo)


@router.delete("/modelos/{modelo_id}", status_code=204)
async def excluir_modelo(
    modelo_id: str,
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Apaga o modelo. Contratos já emitidos continuam existindo, com o texto que
    tinham — a FK é `SET NULL`, não `CASCADE`.
    """
    resultado = await db.execute(
        select(ModeloDeContrato).where(ModeloDeContrato.id == modelo_id)
    )
    modelo = resultado.scalars().first()
    if modelo is None:
        raise NotFoundException("Modelo")
    await db.delete(modelo)
    await db.commit()
    return Response(status_code=204)


# ------------------------------------------------- dados civis do cliente

async def _lead_ou_404(lead_id: str, db: AsyncSession) -> Lead:
    resultado = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = resultado.scalars().first()
    if lead is None:
        raise NotFoundException("Lead")
    return lead


@router.get("/leads/{lead_id}/dados", response_model=DadosResponse)
async def ler_dados(
    lead_id: str,
    _: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Nunca 404 por falta de dados: cliente sem qualificação civil preenchida é
    o estado normal, e o formulário precisa abrir vazio.
    """
    await _lead_ou_404(lead_id, db)
    resultado = await db.execute(
        select(DadosDoContrato).where(DadosDoContrato.lead_id == lead_id)
    )
    dados = resultado.scalars().first()
    if dados is None:
        return DadosResponse()
    return DadosResponse.model_validate(dados)


@router.put("/leads/{lead_id}/dados", response_model=DadosResponse)
async def gravar_dados(
    lead_id: str,
    entrada: DadosEntrada,
    _: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Cria ou atualiza. Quem atende preenche isto na hora de fechar — por isso
    não exige admin.
    """
    await _lead_ou_404(lead_id, db)
    resultado = await db.execute(
        select(DadosDoContrato).where(DadosDoContrato.lead_id == lead_id)
    )
    dados = resultado.scalars().first()
    if dados is None:
        dados = DadosDoContrato(lead_id=lead_id)
        db.add(dados)

    for campo, valor in entrada.model_dump().items():
        if campo == "cpf" and valor:
            # Guardado só com dígitos; a formatação é da exibição. Assim
            # "123.456.789-01" e "12345678901" são o mesmo CPF no banco.
            valor = "".join(c for c in valor if c.isdigit()) or None
        if campo == "uf" and valor:
            valor = valor.strip().upper()
        setattr(dados, campo, valor)

    await db.commit()
    await db.refresh(dados)
    return DadosResponse.model_validate(dados)


# ---------------------------------------------------------- os contratos

@router.get("/leads/{lead_id}", response_model=List[ContratoResponse])
async def listar_do_lead(
    lead_id: str,
    _: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    await _lead_ou_404(lead_id, db)
    resultado = await db.execute(
        select(Contrato)
        .where(Contrato.lead_id == lead_id)
        .order_by(Contrato.data_criacao.desc())
    )
    return [ContratoResponse.model_validate(c) for c in resultado.scalars().all()]


@router.post("/leads/{lead_id}", response_model=ContratoResponse, status_code=201)
async def gerar(
    lead_id: str,
    entrada: GerarEntrada,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Gera o contrato deste cliente, com o texto já preenchido.

    O que falta de dado vira `____________` em vez de sumir: contrato com
    linha para preencher é contrato incompleto e se vê; contrato com o campo
    apagado é contrato que alguém assina sem reparar.
    """
    lead = await _lead_ou_404(lead_id, db)

    if entrada.modelo_id:
        busca = select(ModeloDeContrato).where(ModeloDeContrato.id == entrada.modelo_id)
    else:
        busca = select(ModeloDeContrato).where(ModeloDeContrato.ativo.is_(True))
    resultado = await db.execute(busca)
    modelo = resultado.scalars().first()
    if modelo is None:
        raise NotFoundException("Modelo")

    # O caso mais recente do contato. Um contato pode ter vários; o contrato é
    # sobre o que se acabou de fechar, que é o último aberto.
    resultado = await db.execute(
        select(Caso)
        .where(Caso.lead_id == lead_id)
        .order_by(Caso.data_abertura.desc())
    )
    caso = resultado.scalars().first()

    resultado = await db.execute(
        select(DadosDoContrato).where(DadosDoContrato.lead_id == lead_id)
    )
    dados = resultado.scalars().first()

    resultado = await db.execute(
        select(LeadDetails).where(LeadDetails.lead_id == lead_id)
    )
    detalhes = resultado.scalars().first()
    detalhes_json = {}
    if detalhes is not None and detalhes.dados_json:
        try:
            detalhes_json = json.loads(detalhes.dados_json) or {}
        except (json.JSONDecodeError, TypeError):
            # JSON quebrado tira empresa e cargo do contrato, não o contrato
            # inteiro do ar.
            detalhes_json = {}

    escritorio = await escritorio_service.obter(db)

    contexto = contrato_service.montar_contexto(
        lead=lead, dados=dados, caso=caso, detalhes_json=detalhes_json,
        escritorio=escritorio,
    )
    corpo = contrato_service.preencher(modelo.corpo, contexto)

    contrato = Contrato(
        lead_id=lead_id,
        modelo_id=modelo.id,
        corpo=corpo,
        status="gerado",
        gerado_por=user_id,
    )
    db.add(contrato)
    await db.commit()
    await db.refresh(contrato)
    logger.info(f"📄 Contrato gerado para o lead {lead_id} (modelo {modelo.nome})")
    return ContratoResponse.model_validate(contrato)


@router.get("/{contrato_id}/pdf")
async def baixar_pdf(
    contrato_id: str,
    _: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Assinado, devolve **o arquivo guardado**; não assinado, desenha na hora.

    A distinção é o ponto. Redesenhar um contrato assinado daria o mesmo
    texto, mas não o mesmo documento: o que a pessoa viu e aceitou foi aquele
    arquivo, com aquela folha de auditoria, e é ele que se apresenta se
    alguém contestar. Documento que se regenera não é documento — é relatório.

    Enquanto não há assinatura não há o que preservar, e desenhar na hora
    evita guardar binário que ninguém vai comparar com nada.
    """
    resultado = await db.execute(select(Contrato).where(Contrato.id == contrato_id))
    contrato = resultado.scalars().first()
    if contrato is None:
        raise NotFoundException("Contrato")

    if contrato.pdf_assinado:
        pdf = contrato.pdf_assinado
    else:
        pdf = contrato_service.em_pdf(contrato.corpo, titulo="Contrato")
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="contrato-{contrato_id[:8]}.pdf"'
        },
    )


# ------------------------------------------------------------- assinatura

class LinkResponse(BaseModel):
    link: str
    expira_em: datetime
    enviado: bool = False
    detalhe: Optional[str] = None


TEXTO_DO_ENVIO = (
    "{saudacao}Seu contrato de honorários está pronto.\n\n"
    "É só abrir o link abaixo, conferir os dados e assinar — leva menos de um "
    "minuto e dá para fazer pelo próprio celular:\n\n{link}\n\n"
    "O link é individual e vale por {dias} dias. Qualquer dúvida antes de "
    "assinar, é só me chamar por aqui."
)


async def _contrato_ou_404(contrato_id: str, db: AsyncSession) -> Contrato:
    resultado = await db.execute(select(Contrato).where(Contrato.id == contrato_id))
    contrato = resultado.scalars().first()
    if contrato is None:
        raise NotFoundException("Contrato")
    return contrato


@router.post("/{contrato_id}/link", response_model=LinkResponse)
async def gerar_link(
    contrato_id: str,
    _: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Dá ao contrato um link de assinatura, sem enviar nada.

    Serve para copiar e mandar por outro canal — e para renovar um link que
    venceu. Chamar de novo **invalida o anterior**: dois endereços vivos para
    o mesmo contrato é um endereço a mais para vazar.
    """
    contrato = await _contrato_ou_404(contrato_id, db)

    if assinatura_service.ja_assinado(contrato):
        raise ValidationException("Este contrato já foi assinado.")

    link = assinatura_service.preparar_para_envio(contrato)
    await db.commit()
    await db.refresh(contrato)

    logger.info(f"🔗 Link de assinatura gerado para o contrato {contrato_id}")
    return LinkResponse(link=link, expira_em=contrato.token_expira_em)


@router.post("/{contrato_id}/enviar", response_model=LinkResponse)
async def enviar(
    contrato_id: str,
    _: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Manda o link pelo WhatsApp do cliente e grava a mensagem na conversa.

    O envio vem **antes** do commit, seguindo o que já vale para a resposta do
    operador: gravar uma mensagem que a Evolution recusou faria a transcrição
    mentir para quem a lê. Se a Evolution recusar, o link nem chega a existir —
    e é melhor assim, porque link gerado e não entregue é link que vence sem
    ninguém ter recebido.
    """
    contrato = await _contrato_ou_404(contrato_id, db)

    if assinatura_service.ja_assinado(contrato):
        raise ValidationException("Este contrato já foi assinado.")

    lead = await _lead_ou_404(contrato.lead_id, db)
    conversa = (
        await db.execute(
            select(Conversation).where(Conversation.id == lead.conversation_id)
        )
    ).scalars().first()
    if conversa is None:
        raise NotFoundException("Conversa")

    link = assinatura_service.preparar_para_envio(contrato)

    primeiro_nome = (lead.nome or "").strip().split(" ")[0]
    texto = TEXTO_DO_ENVIO.format(
        saudacao=f"Oi, {primeiro_nome}! " if primeiro_nome else "",
        link=link,
        dias=assinatura_service.DIAS_DE_VALIDADE,
    )

    envio = await whatsapp_service.send_message(
        phone_number=conversa.phone_number, message_text=texto
    )
    if not envio.get("success"):
        await db.rollback()
        raise ValidationException("A Evolution não confirmou o envio.")

    db.add(
        Message(
            conversation_id=conversa.id,
            remetente="sistema",
            conteudo=texto,
            timestamp=datetime.utcnow(),
        )
    )
    conversa.data_ultima_msg = datetime.utcnow()
    await db.commit()
    await db.refresh(contrato)

    logger.info(f"📤 Contrato {contrato_id} enviado para assinatura")
    return LinkResponse(
        link=link, expira_em=contrato.token_expira_em, enviado=True
    )
