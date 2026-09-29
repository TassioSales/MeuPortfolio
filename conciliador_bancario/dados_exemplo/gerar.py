"""Gera extrato e contas a receber sintéticos, com gabarito, para medir o motor.

Os casos difíceis estão aqui de propósito e nas proporções que aparecem no fechamento de um mês
real: pagamento exato é maioria, mas o que dá trabalho são a tarifa descontada, o depósito único
que quita vários boletos, o pagamento dividido e o histórico opaco em que o banco não diz de quem
é o dinheiro. Sem esses casos no gerador, qualquer motor parece bom.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from core.modelos import Lancamento, Titulo

EMPRESAS = [
    "Padaria do João", "Mercado Central", "Distribuidora Alfa", "Comercial Beta LTDA",
    "Auto Peças Silva", "Farmácia Vida", "Restaurante Sabor", "Papelaria Escreve Bem",
    "Oficina do Carlos", "Casa de Carnes Boi Forte", "Floricultura Jardim", "Pet Shop Amigo",
    "Lavanderia Limpa Tudo", "Ótica Visão Clara", "Sorveteria Gelato", "Livraria Página Viva",
]

PREFIXOS = ["PIX RECEBIDO", "TED 033 RECEBIDA", "DOC CREDITO", "CRED TEF", "LIQUIDACAO BOLETO"]
OPACOS = ["CRED TEF 0002 CONTA 44", "TED 001 AG 0341 CC 98765", "DEPOSITO ONLINE AVULSO"]

# Metade dos títulos recebe valor redondo. Sem isso o gerador é fácil demais: valor sorteado ao
# centavo é quase sempre único, e a estratégia de valor exato acertaria tudo sem mérito. Na
# prática mensalidade, plano e serviço padrão repetem o mesmo número entre clientes, e é aí que a
# conciliação precisa de outra evidência além do valor.
VALORES_REDONDOS = [
    Decimal(v) for v in ("50.00", "100.00", "150.00", "200.00", "250.00", "300.00", "500.00", "750.00", "1000.00", "1500.00")
]


def _valor(rng: random.Random, minimo: int, maximo: int) -> Decimal:
    if rng.random() < 0.5:
        return rng.choice(VALORES_REDONDOS)
    return Decimal(rng.randrange(minimo, maximo)) / 100


@dataclass
class Cenario:
    titulos: list[Titulo] = field(default_factory=list)
    lancamentos: list[Lancamento] = field(default_factory=list)
    # gabarito: para cada conjunto de lançamentos, o conjunto de títulos que ele quita
    gabarito: list[tuple[frozenset[str], frozenset[str]]] = field(default_factory=list)


def gerar(quantidade_titulos: int = 200, semente: int = 42) -> Cenario:
    rng = random.Random(semente)
    base = date(2026, 3, 1)
    cenario = Cenario()
    proximo_lancamento = 0

    def novo_id() -> str:
        nonlocal proximo_lancamento
        proximo_lancamento += 1
        return f"L{proximo_lancamento:05d}"

    indice_titulo = 0
    while indice_titulo < quantidade_titulos:
        empresa = rng.choice(EMPRESAS)
        vencimento = base + timedelta(days=rng.randint(0, 27))
        sorteio = rng.random()

        # 12%: um depósito quita de 2 a 3 boletos do mesmo cliente
        if sorteio < 0.12 and indice_titulo + 3 <= quantidade_titulos:
            quantos = rng.choice([2, 3])
            grupo = []
            for _ in range(quantos):
                indice_titulo += 1
                grupo.append(
                    Titulo(
                        id=f"T{indice_titulo:05d}",
                        vencimento=vencimento,
                        valor=_valor(rng, 5_000, 200_000),
                        sacado=empresa,
                        documento=f"{rng.randrange(100000, 999999)}",
                    )
                )
            cenario.titulos.extend(grupo)
            id_lancamento = novo_id()
            cenario.lancamentos.append(
                Lancamento(
                    id=id_lancamento,
                    data=vencimento + timedelta(days=rng.randint(0, 3)),
                    valor=sum((t.valor for t in grupo), Decimal("0")),
                    descricao=f"{rng.choice(PREFIXOS)} {empresa.upper()}",
                )
            )
            cenario.gabarito.append((frozenset({id_lancamento}), frozenset(t.id for t in grupo)))
            continue

        indice_titulo += 1
        titulo = Titulo(
            id=f"T{indice_titulo:05d}",
            vencimento=vencimento,
            valor=_valor(rng, 5_000, 500_000),
            sacado=empresa,
            documento=f"{rng.randrange(100000, 999999)}",
        )
        cenario.titulos.append(titulo)

        # 8% dos títulos simplesmente não são pagos no período
        if sorteio > 0.92:
            continue

        pago_em = titulo.vencimento + timedelta(days=rng.randint(-1, 4))

        # 7%: pagamento dividido em dois créditos
        if 0.12 <= sorteio < 0.19:
            metade = (titulo.valor / 2).quantize(Decimal("0.01"))
            ids = []
            for valor, atraso in ((metade, 0), (titulo.valor - metade, rng.randint(1, 3))):
                id_lancamento = novo_id()
                ids.append(id_lancamento)
                cenario.lancamentos.append(
                    Lancamento(
                        id=id_lancamento,
                        data=pago_em + timedelta(days=atraso),
                        valor=valor,
                        descricao=f"PIX RECEBIDO {empresa.upper()}",
                    )
                )
            cenario.gabarito.append((frozenset(ids), frozenset({titulo.id})))
            continue

        # 9%: o banco desconta tarifa e o valor chega a menos
        if 0.19 <= sorteio < 0.28:
            valor = titulo.valor - Decimal(rng.choice(["1.90", "3.50", "5.00"]))
            descricao = f"{rng.choice(PREFIXOS)} {empresa.upper()}"
        # 10%: histórico opaco, mas o número do documento aparece
        elif 0.28 <= sorteio < 0.38:
            valor = titulo.valor
            descricao = f"LIQUIDACAO BOLETO {titulo.documento}"
        # 8%: histórico opaco e sem documento — o caso que só um humano resolve
        elif 0.38 <= sorteio < 0.46:
            valor = titulo.valor
            descricao = rng.choice(OPACOS)
        else:
            valor = titulo.valor
            descricao = f"{rng.choice(PREFIXOS)} {empresa.upper()}"

        id_lancamento = novo_id()
        cenario.lancamentos.append(Lancamento(id=id_lancamento, data=pago_em, valor=valor, descricao=descricao))
        cenario.gabarito.append((frozenset({id_lancamento}), frozenset({titulo.id})))

    # Créditos que não são pagamento de título: estorno, aporte, transferência entre contas
    # próprias. Existem em todo extrato e o motor precisa deixá-los em paz.
    for _ in range(max(3, quantidade_titulos // 25)):
        cenario.lancamentos.append(
            Lancamento(
                id=novo_id(),
                data=base + timedelta(days=rng.randint(0, 27)),
                valor=Decimal(rng.randrange(1_000, 80_000)) / 100,
                descricao=rng.choice(["ESTORNO TARIFA", "TRANSF ENTRE CONTAS PROPRIAS", "APORTE SOCIO"]),
            )
        )

    rng.shuffle(cenario.lancamentos)
    return cenario


def para_ofx(lancamentos: list[Lancamento]) -> str:
    """Escreve o cenário como OFX, para exercitar o leitor de ponta a ponta."""
    linhas = ["OFXHEADER:100", "<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS><BANKTRANLIST>"]
    for l in lancamentos:
        linhas.append(
            f"<STMTTRN><TRNTYPE>CREDIT<DTPOSTED>{l.data:%Y%m%d}120000[-3:BRT]"
            f"<TRNAMT>{l.valor}<FITID>{l.id}<MEMO>{l.descricao}</STMTTRN>"
        )
    linhas.append("</BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>")
    return "\n".join(linhas)


def para_csv(titulos: list[Titulo]) -> str:
    linhas = ["id,vencimento,valor,sacado,documento"]
    linhas.extend(f"{t.id},{t.vencimento:%Y-%m-%d},{t.valor},{t.sacado},{t.documento}" for t in titulos)
    return "\n".join(linhas)
