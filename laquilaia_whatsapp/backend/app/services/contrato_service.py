"""
O contrato: preencher as lacunas e virar PDF.

O texto é do advogado, escrito no painel. Este módulo não decide cláusula
nenhuma — e principalmente não decide honorários, que são compromisso
comercial e profissional do escritório. Software que inventasse esse número
estaria assumindo obrigação em nome de alguém.

O que ele faz é substituir `{{cliente.nome}}` por um nome, e desenhar o
resultado numa página A4 com texto justificado.
"""

import re
from datetime import datetime
from io import BytesIO
from typing import Dict, Optional

from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.utils.logger import logger

# As lacunas que o modelo pode usar, e o que cada uma quer dizer.
#
# A lista é fechada de propósito: o advogado escreve o contrato numa caixa de
# texto, e uma variável escrita errado precisa aparecer como erro na tela — não
# virar uma linha em branco no meio de um instrumento jurídico.
VARIAVEIS: Dict[str, str] = {
    "cliente.nome": "Nome completo do cliente",
    "cliente.cpf": "CPF, formatado",
    "cliente.rg": "RG",
    "cliente.nacionalidade": "Nacionalidade",
    "cliente.estado_civil": "Estado civil",
    "cliente.profissao": "Profissão",
    "cliente.endereco": "Endereço completo",
    "cliente.cep": "CEP",
    "cliente.cidade": "Cidade",
    "cliente.uf": "UF",
    "cliente.telefone": "Telefone, formatado",
    "cliente.email": "E-mail",
    "caso.resumo": "Resumo do caso, do parecer",
    "caso.area": "Área do direito",
    "caso.empresa": "Empresa onde trabalhava",
    "caso.cargo": "Cargo que ocupava",
    "escritorio.nome": "Nome do escritório",
    "escritorio.cnpj": "CNPJ do escritório",
    "escritorio.oab": "OAB do responsável",
    "escritorio.fundador": "Nome do advogado responsável",
    "escritorio.endereco": "Endereço do escritório",
    "escritorio.cidade": "Cidade do escritório",
    "data.hoje": "Data de hoje, por extenso",
    "data.cidade_e_data": "Cidade e data, como se assina um contrato",
}

# Quando um dado não foi coletado. Uma linha em branco no meio de "portador do
# CPF nº ____" é o que faz alguém assinar sem reparar; a marca obriga a
# reparar.
LACUNA = "____________"

_PADRAO = re.compile(r"\{\{\s*([a-z_]+\.[a-z_]+)\s*\}\}")

MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def formatar_cpf(cpf: Optional[str]) -> Optional[str]:
    """`12345678901` vira `123.456.789-01`. Guardamos cru, exibimos formatado."""
    if not cpf:
        return None
    digitos = "".join(c for c in cpf if c.isdigit())
    if len(digitos) != 11:
        # CPF com tamanho errado sai como veio: esconder o erro atrás de uma
        # formatação bonita faria alguém assinar um número inválido.
        return cpf
    return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"


def data_por_extenso(quando: Optional[datetime] = None) -> str:
    d = quando or datetime.now()
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def variaveis_desconhecidas(corpo: str) -> list:
    """
    As lacunas que o modelo usa e o sistema não sabe preencher.

    Serve para a tela avisar **antes** de salvar. Descobrir isso na hora de
    gerar o contrato do cliente é tarde: alguém já prometeu o documento.
    """
    return sorted({nome for nome in _PADRAO.findall(corpo) if nome not in VARIAVEIS})


def montar_contexto(lead, dados, caso, detalhes_json: dict, escritorio) -> Dict[str, str]:
    """
    O que cada lacuna vale para este cliente.

    Tudo que falta vira `LACUNA` em vez de string vazia — ver a constante.
    """
    from app.utils.telefone import formatar_telefone_br  # local: evita ciclo

    def valor(x):
        texto = (str(x).strip() if x is not None else "")
        return texto or LACUNA

    cidade_escritorio = getattr(escritorio, "cidade", None) if escritorio else None

    return {
        "cliente.nome": valor(getattr(lead, "nome", None)),
        "cliente.cpf": valor(formatar_cpf(getattr(dados, "cpf", None))),
        "cliente.rg": valor(getattr(dados, "rg", None)),
        "cliente.nacionalidade": valor(getattr(dados, "nacionalidade", None)),
        "cliente.estado_civil": valor(getattr(dados, "estado_civil", None)),
        "cliente.profissao": valor(getattr(dados, "profissao", None)),
        "cliente.endereco": valor(getattr(dados, "endereco", None)),
        "cliente.cep": valor(getattr(dados, "cep", None)),
        "cliente.cidade": valor(getattr(dados, "cidade", None)),
        "cliente.uf": valor(getattr(dados, "uf", None)),
        "cliente.telefone": valor(formatar_telefone_br(getattr(lead, "phone_number", None))),
        "cliente.email": valor(getattr(lead, "email", None)),
        "caso.resumo": valor(getattr(caso, "resumo", None)),
        "caso.area": valor(getattr(caso, "area", None)),
        "caso.empresa": valor(detalhes_json.get("empresa")),
        "caso.cargo": valor(detalhes_json.get("cargo")),
        "escritorio.nome": valor(getattr(escritorio, "nome", None)),
        "escritorio.cnpj": valor(getattr(escritorio, "cnpj", None)),
        "escritorio.oab": valor(getattr(escritorio, "oab_responsavel", None)),
        "escritorio.fundador": valor(getattr(escritorio, "fundador", None)),
        "escritorio.endereco": valor(getattr(escritorio, "endereco", None)),
        "escritorio.cidade": valor(cidade_escritorio),
        "data.hoje": data_por_extenso(),
        "data.cidade_e_data": (
            f"{cidade_escritorio}, {data_por_extenso()}"
            if cidade_escritorio
            else data_por_extenso()
        ),
    }


def preencher(corpo: str, contexto: Dict[str, str]) -> str:
    """
    Troca as lacunas pelos valores.

    Variável que o contexto não conhece vira `LACUNA` e **não** some: um
    `{{cliente.cpj}}` digitado errado precisa aparecer como espaço a
    preencher, não como um buraco invisível no texto.
    """
    return _PADRAO.sub(lambda m: contexto.get(m.group(1), LACUNA), corpo)


def em_pdf(corpo: str, titulo: str = "Contrato") -> bytes:
    """
    O texto virando página A4.

    Linha começando com `#` é título centralizado; o resto é parágrafo
    justificado, que é como contrato se lê. Markdown de verdade seria uma
    dependência a mais para dois casos.
    """
    buffer = BytesIO()
    documento = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title=titulo,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
    )

    base = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle(
        "TituloContrato",
        parent=base["Heading1"],
        fontName="Times-Bold",
        fontSize=13,
        leading=17,
        alignment=TA_CENTER,
        spaceAfter=18,
    )
    estilo_corpo = ParagraphStyle(
        "CorpoContrato",
        parent=base["Normal"],
        fontName="Times-Roman",
        fontSize=11.5,
        leading=16,
        alignment=TA_JUSTIFY,
        spaceAfter=10,
    )

    partes = []
    for linha in corpo.split("\n"):
        texto = linha.strip()
        if not texto:
            partes.append(Spacer(1, 8))
            continue
        if texto.startswith("#"):
            partes.append(Paragraph(_para_html(texto.lstrip("#").strip()), estilo_titulo))
        else:
            partes.append(Paragraph(_para_html(texto), estilo_corpo))

    documento.build(partes)
    pdf = buffer.getvalue()
    buffer.close()
    logger.info(f"📄 Contrato gerado: {len(pdf)} bytes")
    return pdf


def _para_html(texto: str) -> str:
    """
    O mínimo de marcação que o reportlab entende, e o escape que ele exige.

    O escape vem primeiro: um `&` ou um `<` no nome de uma empresa —
    "Silva & Filhos" — quebraria o parser do reportlab e derrubaria a geração
    inteira no meio de um contrato.
    """
    seguro = (
        texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", seguro)
