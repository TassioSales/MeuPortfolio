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

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

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
    "caso.objeto": "Objeto do contrato, em linguagem de contrato",
    "caso.resumo": "Resumo do caso (texto da triagem — ver aviso)",
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


# Como cada área se chama num contrato.
#
# **Por que isto existe.** O modelo base usava `{{caso.resumo}}`, e no primeiro
# contrato real ele saiu assim: *"Contato relata contratação CLT como
# coordenador de estoque (R$ 4.000), 3 anos, seguida de 'promoção' a gerente
# com migração para PJ..."*. É correto, e é escrito **para o advogado ler** —
# num instrumento jurídico soa a ficha de atendimento.
#
# O objeto de um contrato de honorários é seco: diz a natureza da demanda e
# contra quem. O relato do caso vive no dossiê, que é onde ele serve.
OBJETO_POR_AREA = {
    "trabalhista": "ação de natureza trabalhista",
    "consumidor": "ação de natureza consumerista",
    "previdenciario": "ação de natureza previdenciária",
    "familia": "ação de natureza familiar",
    "civel": "ação de natureza cível",
    "criminal": "defesa em matéria criminal",
}
OBJETO_GENERICO = "demanda judicial"


def objeto_do_contrato(area: Optional[str], empresa: Optional[str]) -> str:
    """
    "ação de natureza trabalhista em face de Silva & Filhos Ltda".

    Sem área conhecida vira "demanda judicial", e sem empresa a frase para
    antes do "em face de" — o que é preferível a "em face de ____________",
    que num objeto de contrato parece erro de preenchimento e não lacuna.
    """
    natureza = OBJETO_POR_AREA.get((area or "").strip().lower(), OBJETO_GENERICO)
    alvo = (empresa or "").strip()
    if alvo and alvo != LACUNA:
        return f"{natureza} em face de {alvo}"
    return natureza


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
        "caso.objeto": objeto_do_contrato(
            getattr(caso, "area", None), detalhes_json.get("empresa")
        ),
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


class _Paginado(canvas.Canvas):
    """
    Canvas que escreve "página 2 de 5" — com o total certo.

    O reportlab desenha uma página por vez e só sabe quantas foram no fim, e é
    por isso que "de M" exige este malabarismo: guardar o estado de cada
    página, contar, e só então desenhar o rodapé em todas.

    Num contrato o total não é enfeite. "Página 2" sozinho não denuncia que a
    folha 3 sumiu; "página 2 de 5" denuncia. É a mesma razão de os contratos em
    papel serem rubricados folha a folha.
    """

    def __init__(self, *args, cabecalho: str = "", **kwargs):
        super().__init__(*args, **kwargs)
        self._paginas = []
        self._cabecalho = cabecalho

    def showPage(self):
        self._paginas.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._paginas)
        for estado in self._paginas:
            self.__dict__.update(estado)
            self._rodape(total)
            super().showPage()
        super().save()

    def _rodape(self, total: int) -> None:
        self.saveState()
        self.setFont("Times-Roman", 8)
        self.setFillColor(colors.HexColor("#666666"))

        # O cabeçalho só a partir da segunda folha: na primeira ele brigaria
        # com o título do contrato, que já diz de quem é o documento.
        if self._cabecalho and self._pageNumber > 1:
            self.drawString(2.5 * cm, A4[1] - 1.5 * cm, self._cabecalho)
            self.setStrokeColor(colors.HexColor("#dddddd"))
            self.setLineWidth(0.4)
            self.line(2.5 * cm, A4[1] - 1.7 * cm, A4[0] - 2.5 * cm, A4[1] - 1.7 * cm)

        self.drawCentredString(
            A4[0] / 2, 1.3 * cm, f"página {self._pageNumber} de {total}"
        )
        self.restoreState()


def _folha_de_auditoria(
    assinatura: Dict[str, str], desenho: Optional[bytes] = None
) -> list:
    """
    A página que sustenta a assinatura.

    Uma assinatura eletrônica não se prova pelo rabisco — se prova pelo
    registro: quem digitou o nome, quando, de qual endereço, em qual aparelho,
    e o hash do texto que estava na tela naquele instante. Sem esta folha, o
    PDF assinado é um PDF com um nome escrito embaixo.
    """
    base = getSampleStyleSheet()
    titulo = ParagraphStyle(
        "TituloAuditoria", parent=base["Heading2"], fontName="Times-Bold",
        fontSize=12, alignment=TA_CENTER, spaceAfter=16,
    )
    nota = ParagraphStyle(
        "NotaAuditoria", parent=base["Normal"], fontName="Times-Roman",
        fontSize=8.5, leading=12, alignment=TA_JUSTIFY,
        textColor=colors.HexColor("#444444"), spaceBefore=14,
    )
    celula = ParagraphStyle(
        "CelulaAuditoria", parent=base["Normal"], fontName="Times-Roman",
        fontSize=9, leading=12,
    )

    rotulos = [
        ("Assinado por", "nome"),
        ("Data e hora", "quando"),
        ("Endereço IP", "ip"),
        ("Dispositivo", "dispositivo"),
        ("Identificador do documento", "contrato_id"),
        ("Impressão digital do texto (SHA-256)", "hash"),
    ]
    linhas = [
        [
            Paragraph(f"<b>{rotulo}</b>", celula),
            Paragraph(_para_html(str(assinatura.get(chave) or LACUNA)), celula),
        ]
        for rotulo, chave in rotulos
    ]

    tabela = Table(linhas, colWidths=[5.5 * cm, 10.5 * cm])
    tabela.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LINEBELOW", (0, 0), (-1, -2), 0.25, colors.HexColor("#cccccc")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#999999")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    partes = [PageBreak(), Paragraph("COMPROVANTE DE ASSINATURA ELETRÔNICA", titulo)]

    # A assinatura em cima da tabela, e não depois dela.
    #
    # É o que a pessoa procura quando abre o comprovante: ver a própria
    # assinatura. Os dados técnicos importam num litígio; o rabisco importa
    # nos primeiros dois segundos, e é ele que faz o documento parecer o que é.
    imagem = _imagem_da_assinatura(desenho) if desenho else None
    if imagem is not None:
        imagem.hAlign = "CENTER"
        assinado_por = ParagraphStyle(
            "AssinadoPor", parent=base["Normal"], fontName="Times-Roman",
            fontSize=10, alignment=TA_CENTER, textColor=colors.HexColor("#444444"),
            spaceBefore=4, spaceAfter=18,
        )
        partes.extend([
            Spacer(1, 6),
            imagem,
            # A régua sob o rabisco é o que o faz ler como assinatura em vez
            # de figura solta no meio da página.
            Table(
                [[""]],
                colWidths=[LARGURA_DA_ASSINATURA],
                rowHeights=[1],
                style=TableStyle([
                    ("LINEABOVE", (0, 0), (-1, 0), 0.6, colors.HexColor("#333333")),
                ]),
                hAlign="CENTER",
            ),
            Paragraph(
                _para_html(str(assinatura.get("nome") or LACUNA)), assinado_por
            ),
        ])

    partes.extend([
        tabela,
        Paragraph(
            "Assinatura eletrônica coletada por meio de link individual e com "
            "prazo de validade, enviado ao número de WhatsApp cadastrado do "
            "signatário. A impressão digital acima identifica o texto exato "
            "aceito no ato: qualquer alteração posterior no documento produz "
            "impressão diferente. Registro nos termos do art. 10, §2º, da "
            "Medida Provisória nº 2.200-2/2001 e da Lei nº 14.063/2020.",
            nota,
        ),
    ])
    return partes


def em_pdf(
    corpo: str,
    titulo: str = "Contrato",
    assinatura: Optional[Dict[str, str]] = None,
    cabecalho: str = "",
    rabisco: Optional[bytes] = None,
) -> bytes:
    """
    O texto virando página A4.

    Linha começando com `#` é título centralizado; o resto é parágrafo
    justificado, que é como contrato se lê. Markdown de verdade seria uma
    dependência a mais para dois casos.

    Com `assinatura`, ganha ao final a folha de auditoria — e é essa versão
    que fica guardada no banco.
    """
    buffer = BytesIO()
    documento = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title=titulo,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.2 * cm,
    )

    base = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle(
        "TituloContrato",
        parent=base["Heading1"],
        fontName="Times-Bold",
        fontSize=13.5,
        leading=18,
        alignment=TA_CENTER,
        spaceAfter=22,
    )
    estilo_corpo = ParagraphStyle(
        "CorpoContrato",
        parent=base["Normal"],
        fontName="Times-Roman",
        fontSize=11.5,
        leading=16.5,
        alignment=TA_JUSTIFY,
        spaceAfter=11,
    )
    # A cláusula ganha ar em cima e fica junto do que vem depois. Sem o
    # `keepWithNext`, "CLÁUSULA 4ª — DOS HONORÁRIOS" cai sozinha no pé da
    # página e o texto dela começa na seguinte — que é feio e, num contrato,
    # ainda por cima esconde a cláusula que mais importa.
    estilo_clausula = ParagraphStyle(
        "ClausulaContrato",
        parent=estilo_corpo,
        fontName="Times-Bold",
        alignment=TA_LEFT,
        spaceBefore=16,
        spaceAfter=7,
        keepWithNext=1,
    )
    # As linhas de assinatura não são parágrafo: centradas e sem justificar,
    # senão o traço e o nome saem esticados de margem a margem.
    estilo_assinatura = ParagraphStyle(
        "LinhaDeAssinatura",
        parent=estilo_corpo,
        alignment=TA_CENTER,
        spaceAfter=3,
    )

    # A imagem vai **na primeira** linha de traços, e só nela: no modelo
    # padrão a primeira é a do CONTRATANTE, que é quem assinou aqui. A segunda
    # é a do advogado, e pôr o rabisco do cliente nela seria falsificar quem
    # assinou o quê.
    desenho = _imagem_da_assinatura(rabisco) if rabisco else None
    ja_desenhou = False

    partes = []
    for linha in corpo.split("\n"):
        texto = linha.strip()
        if not texto:
            partes.append(Spacer(1, 9))
            continue

        if texto.startswith("#"):
            partes.append(
                Paragraph(_para_html(texto.lstrip("#").strip()), estilo_titulo)
            )
        elif _e_clausula(texto):
            partes.append(Paragraph(_para_html(texto), estilo_clausula))
        elif _e_assinatura(texto):
            if desenho is not None and not ja_desenhou:
                # `KeepTogether` para o rabisco não ficar numa folha e a linha
                # na seguinte — que é o jeito mais rápido de um documento
                # parecer adulterado.
                partes.append(
                    KeepTogether(
                        [desenho, Paragraph(_para_html(texto), estilo_assinatura)]
                    )
                )
                ja_desenhou = True
            else:
                partes.append(Paragraph(_para_html(texto), estilo_assinatura))
        else:
            partes.append(Paragraph(_para_html(texto), estilo_corpo))

    if assinatura:
        partes.extend(_folha_de_auditoria(assinatura, desenho=rabisco))

    documento.build(
        partes,
        canvasmaker=lambda *a, **k: _Paginado(*a, cabecalho=cabecalho, **k),
    )
    pdf = buffer.getvalue()
    buffer.close()
    logger.info(f"📄 Contrato gerado: {len(pdf)} bytes")
    return pdf


# "CLÁUSULA 1ª — DO OBJETO", com ou sem negrito à volta. O `^` e o limite de
# tamanho evitam casar com uma menção a "cláusula" no meio de um parágrafo.
_CLAUSULA = re.compile(r"^\**\s*(CL[ÁA]USULA|PAR[ÁA]GRAFO)\b", re.IGNORECASE)

# A linha de traços onde se assina, e as duas ou três que vêm logo abaixo dela.
_TRACOS = re.compile(r"^_{6,}\s*$")


# Largura da assinatura na página. Ela é redimensionada mantendo proporção:
# um rabisco feito num celular estreito e outro num tablet larguíssimo têm que
# sair do mesmo tamanho no papel, senão o documento parece montado.
LARGURA_DA_ASSINATURA = 6.5 * cm
ALTURA_MAXIMA_DA_ASSINATURA = 2.2 * cm


def _imagem_da_assinatura(png: bytes) -> Optional[Image]:
    """
    O PNG virando um elemento da página, na proporção certa.

    Devolve `None` se o arquivo não for uma imagem legível: um contrato não
    pode deixar de ser gerado porque o `<canvas>` de alguém produziu algo
    estranho — sem a imagem ele ainda vale, e a trilha de prova continua
    inteira.
    """
    if not png:
        return None
    try:
        from reportlab.lib.utils import ImageReader

        leitor = ImageReader(BytesIO(png))
        largura_px, altura_px = leitor.getSize()
        if not largura_px or not altura_px:
            return None

        largura = LARGURA_DA_ASSINATURA
        altura = largura * (altura_px / largura_px)
        if altura > ALTURA_MAXIMA_DA_ASSINATURA:
            altura = ALTURA_MAXIMA_DA_ASSINATURA
            largura = altura * (largura_px / altura_px)

        imagem = Image(BytesIO(png), width=largura, height=altura)
        imagem.hAlign = "LEFT"
        return imagem
    except Exception as e:
        logger.warning(f"⚠️ Assinatura desenhada ilegível, seguindo sem ela: {e}")
        return None


def _e_clausula(texto: str) -> bool:
    return bool(_CLAUSULA.match(texto)) and len(texto) < 120


def _e_assinatura(texto: str) -> bool:
    """
    Se a linha faz parte de um bloco de assinatura.

    Só o traço é reconhecido aqui; o nome e o "CONTRATANTE" abaixo dele
    continuam parágrafos comuns, e é isso que se quer — centrá-los exigiria
    saber onde o bloco termina, e errar isso centraria o resto do contrato.
    """
    return bool(_TRACOS.match(texto))


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
