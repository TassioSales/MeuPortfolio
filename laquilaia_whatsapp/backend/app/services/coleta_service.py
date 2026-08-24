"""
Os dados que a agente recolhe na conversa para o contrato.

A triagem apura o **caso**; esta fase qualifica a **pessoa** — CPF, RG,
nacionalidade, estado civil, profissão, endereço. São dados com dono, ciclo e
sensibilidade diferentes, e por isso moram em tabela própria
(`dados_do_contrato`).

**Nada aqui confia no modelo para completar.** O bloco JSON manda só o que a
pessoa disse, e este módulo grava só o que veio: campo ausente continua
ausente. Um CPF inventado num contrato é um contrato nulo, e o modelo que
inventa não avisa que inventou.

**A gravação é acumulativa, nunca destrutiva.** O agente manda o bloco a cada
mensagem com dado novo, e um bloco posterior com menos campos não pode apagar
o que um anterior já tinha trazido — senão a última mensagem da conversa
zeraria a coleta inteira.
"""

import json
import re
from typing import Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DadosDoContrato
from app.utils.logger import logger

# As fases de uma conversa. Ver o comentário da coluna `Conversation.fase`
# sobre por que ela não é o mesmo que `status`.
FASE_TRIAGEM = "triagem"
FASE_COLETA = "coleta"
FASE_CONTRATADO = "contratado"

# Os campos que o bloco pode trazer. Fechada: chave desconhecida é ignorada em
# vez de virar coluna que não existe.
CAMPOS = (
    "nome",
    "cpf",
    "rg",
    "nacionalidade",
    "estado_civil",
    "profissao",
    "endereco",
    "cep",
    "cidade",
    "uf",
)

# O que um contrato não pode sair sem.
#
# `rg` fica de fora de propósito: muita gente não sabe o número de cabeça, e
# travar o contrato por causa dele é perder o cliente por um campo que o
# advogado completa em trinta segundos. Ele sai como lacuna visível no PDF.
# `nome` também fica de fora porque vem do lead, não daqui.
OBRIGATORIOS = ("cpf", "endereco", "cidade", "uf")

_BLOCOS = re.compile(r"```json\s*([\s\S]*?)\s*```", re.IGNORECASE)


def extrair(response_text: str) -> Optional[Dict[str, str]]:
    """
    Acha o bloco `dados_contrato` na resposta do modelo.

    Varre **todos** os blocos em vez de pegar o primeiro: a mesma mensagem
    pode, em tese, trazer o bloco de qualificação e o de dados, e pegar o
    primeiro faria o de dados ser descartado em silêncio conforme a ordem em
    que o modelo os escreveu.
    """
    for bruto in _BLOCOS.findall(response_text or ""):
        try:
            corpo = json.loads(bruto)
        except (json.JSONDecodeError, TypeError):
            # JSON quebrado num bloco não pode impedir a leitura dos outros.
            continue

        if not isinstance(corpo, dict):
            continue

        dados = corpo.get("dados_contrato")
        if isinstance(dados, dict):
            return _limpar(dados)

    return None


def _limpar(bruto: dict) -> Dict[str, str]:
    """
    Só os campos conhecidos, sem os vazios, já normalizados.

    Vazio é descartado aqui e não na gravação porque `""` vindo do modelo
    significa "não tenho", e deixá-lo passar apagaria o valor que uma mensagem
    anterior trouxe.
    """
    limpos: Dict[str, str] = {}

    for campo in CAMPOS:
        valor = bruto.get(campo)
        if valor is None:
            continue
        texto = str(valor).strip()
        if not texto:
            continue

        if campo == "cpf":
            # Guardado só com dígitos; a formatação é da exibição. Assim
            # "123.456.789-01" e "12345678901" são o mesmo CPF no banco.
            digitos = "".join(c for c in texto if c.isdigit())
            if len(digitos) != 11:
                # CPF de tamanho errado é erro de digitação ou alucinação do
                # modelo. Descartar e continuar perguntando é melhor que
                # gravar um número que ninguém vai conferir.
                logger.warning(f"⚠️ CPF com {len(digitos)} dígitos, descartado")
                continue
            texto = digitos
        elif campo == "uf":
            letras = texto.strip().upper()
            if len(letras) != 2 or not letras.isalpha():
                continue
            texto = letras
        elif campo == "cep":
            digitos = "".join(c for c in texto if c.isdigit())
            texto = f"{digitos[:5]}-{digitos[5:]}" if len(digitos) == 8 else texto

        limpos[campo] = texto[:2000]

    return limpos


async def gravar(db: AsyncSession, lead_id: str, dados: Dict[str, str]) -> DadosDoContrato:
    """
    Junta o que veio ao que já existia. Não apaga nada.

    Não faz commit: quem chama está dentro da transação da mensagem, e um
    commit aqui gravaria os dados antes de a resposta ao cliente ter sido
    aceita.
    """
    registro = (
        await db.execute(
            select(DadosDoContrato).where(DadosDoContrato.lead_id == lead_id)
        )
    ).scalars().first()

    if registro is None:
        registro = DadosDoContrato(lead_id=lead_id)
        db.add(registro)

    novos = []
    for campo, valor in dados.items():
        # `nome` é do lead, não desta tabela — o contrato o lê de lá.
        if campo == "nome" or not hasattr(registro, campo):
            continue
        if getattr(registro, campo, None) != valor:
            setattr(registro, campo, valor)
            novos.append(campo)

    if novos:
        logger.info(f"📋 Dados do contrato do lead {lead_id}: {', '.join(novos)}")

    return registro


def esta_completo(dados: Optional[DadosDoContrato]) -> bool:
    """Se dá para emitir o contrato sem lacuna nos campos que importam."""
    if dados is None:
        return False
    return all(
        (getattr(dados, campo, None) or "").strip() for campo in OBRIGATORIOS
    )


def o_que_falta(dados: Optional[DadosDoContrato]) -> list:
    """Os obrigatórios ainda vazios — para o painel e para o log."""
    if dados is None:
        return list(OBRIGATORIOS)
    return [
        campo
        for campo in OBRIGATORIOS
        if not (getattr(dados, campo, None) or "").strip()
    ]


async def dados_do_lead(db: AsyncSession, lead_id: str) -> Optional[DadosDoContrato]:
    """O registro civil deste lead, ou `None` se ninguém preencheu nada."""
    return (
        await db.execute(
            select(DadosDoContrato).where(DadosDoContrato.lead_id == lead_id)
        )
    ).scalars().first()
