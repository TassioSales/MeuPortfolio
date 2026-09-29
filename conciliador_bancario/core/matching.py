"""O motor de conciliação.

Sete estratégias em cascata, da evidência mais forte para a mais fraca. Cada lançamento e cada
título é consumido no máximo uma vez, e uma estratégia só enxerga o que as anteriores deixaram.

A ordem não é arbitrária. Número de documento no histórico é prova quase direta; valor igual na
janela de data é forte quando o candidato é único; combinação de títulos é útil mas admite mais
de uma resposta certa; tolerância é a mais fraca porque aceita diferença. Rodar na ordem inversa
faria a estratégia fraca consumir um título que a forte casaria melhor.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from itertools import combinations

from core.modelos import Candidato, Conciliacao, Estrategia, Lancamento, Resultado, Situacao, Titulo
from core.normalizacao import extrair_documentos, normalizar, similaridade_nome
from core.regras import Regras

# Confiança base de cada estratégia. O valor final ainda é ajustado pela evidência encontrada.
CONFIANCA_BASE: dict[Estrategia, float] = {
    Estrategia.DOCUMENTO: 0.99,
    Estrategia.APELIDO: 0.93,
    Estrategia.VALOR_DATA: 0.90,
    Estrategia.VALOR_NOME: 0.85,
    Estrategia.UM_PARA_MUITOS: 0.80,
    Estrategia.MUITOS_PARA_UM: 0.75,
    Estrategia.TOLERANCIA: 0.60,
}


class _Estado:
    """Controla o que já foi consumido, para nenhum título ser quitado duas vezes."""

    def __init__(self, lancamentos: list[Lancamento], titulos: list[Titulo]) -> None:
        self.lancamentos = {l.id: l for l in lancamentos}
        self.titulos = {t.id: t for t in titulos}
        self.lancamentos_livres = {l.id for l in lancamentos}
        self.titulos_livres = {t.id for t in titulos}
        self.conciliacoes: list[Conciliacao] = []

    def consumir(self, conciliacao: Conciliacao) -> None:
        self.lancamentos_livres.difference_update(conciliacao.lancamentos)
        self.titulos_livres.difference_update(conciliacao.titulos)
        self.conciliacoes.append(conciliacao)

    def livres_ordenados(self) -> tuple[list[Lancamento], list[Titulo]]:
        """Sempre na mesma ordem: a mesma entrada precisa produzir a mesma saída."""
        lancamentos = sorted((self.lancamentos[i] for i in self.lancamentos_livres), key=lambda l: (l.data, l.id))
        titulos = sorted((self.titulos[i] for i in self.titulos_livres), key=lambda t: (t.vencimento, t.id))
        return lancamentos, titulos


def _na_janela(lancamento: Lancamento, titulo: Titulo, regras: Regras) -> bool:
    return abs((lancamento.data - titulo.vencimento).days) <= regras.janela_dias


def _penalidade_data(lancamento: Lancamento, titulo: Titulo, regras: Regras) -> float:
    """Quanto mais longe do vencimento, menos confiança — sem nunca zerar dentro da janela."""
    if regras.janela_dias == 0:
        return 0.0
    distancia = abs((lancamento.data - titulo.vencimento).days)
    return 0.05 * (distancia / regras.janela_dias)


def _situacao(diferenca: Decimal) -> Situacao:
    return Situacao.CONCILIADO if diferenca == 0 else Situacao.DIVERGENTE


def _extrato_nomeia_outro(lancamento: Lancamento, candidato: Titulo, titulos: list[Titulo], regras: Regras) -> bool:
    """O histórico identifica um cliente, e não é o dono deste título.

    Sem esta checagem, um crédito de valor redondo com "PIX RECEBIDO FLORICULTURA JARDIM" no
    histórico casava com o título de outra empresa só por ser o único daquele valor na janela —
    o extrato dizia de quem era o dinheiro e o motor não lia.
    """
    if similaridade_nome(lancamento.descricao, candidato.sacado) > 0:
        return False
    return any(
        similaridade_nome(lancamento.descricao, outro.sacado) >= regras.min_similaridade_nome
        for outro in titulos
        if normalizar(outro.sacado) != normalizar(candidato.sacado)
    )


def _por_documento(estado: _Estado, regras: Regras) -> None:
    lancamentos, titulos = estado.livres_ordenados()
    por_documento: dict[str, list[Titulo]] = defaultdict(list)
    for titulo in titulos:
        documento = normalizar(titulo.documento).lstrip("0")
        if documento:
            por_documento[documento].append(titulo)

    for lancamento in lancamentos:
        if lancamento.id not in estado.lancamentos_livres:
            continue
        for documento in sorted(extrair_documentos(lancamento.descricao)):
            candidatos = [t for t in por_documento.get(documento, []) if t.id in estado.titulos_livres]
            if len(candidatos) != 1:
                continue
            titulo = candidatos[0]
            diferenca = lancamento.valor - titulo.valor
            if diferenca != 0 and not regras.dentro_da_tolerancia(titulo.valor, lancamento.valor):
                continue
            estado.consumir(
                Conciliacao(
                    lancamentos=(lancamento.id,),
                    titulos=(titulo.id,),
                    estrategia=Estrategia.DOCUMENTO,
                    confianca=CONFIANCA_BASE[Estrategia.DOCUMENTO],
                    situacao=_situacao(diferenca),
                    diferenca=diferenca,
                    motivo=f"documento {documento} aparece no histórico e identifica o título {titulo.id}",
                )
            )
            break


def _por_apelido(estado: _Estado, regras: Regras, apelidos: dict[str, str]) -> None:
    """Usa o que um humano já corrigiu antes: histórico conhecido aponta para um sacado."""
    if not apelidos:
        return
    lancamentos, titulos = estado.livres_ordenados()
    for lancamento in lancamentos:
        if lancamento.id not in estado.lancamentos_livres:
            continue
        sacado = apelidos.get(normalizar(lancamento.descricao))
        if not sacado:
            continue
        candidatos = [
            t
            for t in titulos
            if t.id in estado.titulos_livres
            and normalizar(t.sacado) == sacado
            and _na_janela(lancamento, t, regras)
            and (t.valor == lancamento.valor or regras.dentro_da_tolerancia(t.valor, lancamento.valor))
        ]
        if len(candidatos) != 1:
            continue
        titulo = candidatos[0]
        diferenca = lancamento.valor - titulo.valor
        estado.consumir(
            Conciliacao(
                lancamentos=(lancamento.id,),
                titulos=(titulo.id,),
                estrategia=Estrategia.APELIDO,
                confianca=CONFIANCA_BASE[Estrategia.APELIDO] - _penalidade_data(lancamento, titulo, regras),
                situacao=_situacao(diferenca),
                diferenca=diferenca,
                motivo=f"histórico já foi associado a {sacado} por uma correção anterior",
            )
        )


def _um_para_um(estado: _Estado, regras: Regras, estrategia: Estrategia) -> None:
    """Valor idêntico na janela. Com nome, aceita vários candidatos; sem nome, exige candidato único."""
    exige_nome = estrategia is Estrategia.VALOR_NOME
    lancamentos, titulos = estado.livres_ordenados()

    for lancamento in lancamentos:
        if lancamento.id not in estado.lancamentos_livres:
            continue
        candidatos = [
            t
            for t in titulos
            if t.id in estado.titulos_livres and t.valor == lancamento.valor and _na_janela(lancamento, t, regras)
        ]
        if not candidatos:
            continue

        if exige_nome:
            pontuados = [
                (similaridade_nome(lancamento.descricao, t.sacado), t)
                for t in candidatos
            ]
            pontuados = [(s, t) for s, t in pontuados if s >= regras.min_similaridade_nome]
            if not pontuados:
                continue
            pontuados.sort(key=lambda par: (-par[0], par[1].vencimento, par[1].id))
            similaridade, titulo = pontuados[0]
            motivo = f"valor idêntico e {similaridade:.0%} do nome de {titulo.sacado} no histórico"
            confianca = CONFIANCA_BASE[estrategia] * (0.7 + 0.3 * similaridade)
        else:
            # Sem nome como prova, dois títulos do mesmo valor na janela são ambíguos: casar um
            # deles seria adivinhação, e adivinhação em conciliação vira erro contábil.
            if len(candidatos) != 1:
                continue
            titulo = candidatos[0]
            if _extrato_nomeia_outro(lancamento, titulo, titulos, regras):
                continue
            motivo = f"valor idêntico e único título aberto de {titulo.sacado} na janela"
            confianca = CONFIANCA_BASE[estrategia]

        estado.consumir(
            Conciliacao(
                lancamentos=(lancamento.id,),
                titulos=(titulo.id,),
                estrategia=estrategia,
                confianca=confianca - _penalidade_data(lancamento, titulo, regras),
                situacao=Situacao.CONCILIADO,
                diferenca=Decimal("0"),
                motivo=motivo,
            )
        )


def _agrupar_por_sacado(titulos: list[Titulo], livres: set[str]) -> dict[str, list[Titulo]]:
    grupos: dict[str, list[Titulo]] = defaultdict(list)
    for titulo in titulos:
        if titulo.id in livres:
            grupos[normalizar(titulo.sacado)].append(titulo)
    return grupos


def _um_para_muitos(estado: _Estado, regras: Regras) -> None:
    """Um depósito que quita vários títulos do mesmo cliente.

    A busca por combinação só acontece dentro dos títulos de um sacado que o histórico já aponta,
    e com no máximo `max_titulos_combinados` parcelas. Sem esses dois cortes, a soma de
    subconjuntos cresce rápido demais e ainda passa a casar títulos de clientes diferentes por
    coincidência de valor.
    """
    lancamentos, titulos = estado.livres_ordenados()
    grupos = _agrupar_por_sacado(titulos, estado.titulos_livres)

    for lancamento in lancamentos:
        if lancamento.id not in estado.lancamentos_livres:
            continue

        for sacado, do_sacado in sorted(grupos.items()):
            similaridade = similaridade_nome(lancamento.descricao, sacado)
            if similaridade < regras.min_similaridade_nome:
                continue

            elegiveis = [
                t
                for t in do_sacado
                if t.id in estado.titulos_livres
                and t.valor <= lancamento.valor
                and _na_janela(lancamento, t, regras)
            ]
            if len(elegiveis) < 2:
                continue
            elegiveis = elegiveis[: regras.max_titulos_por_sacado_na_combinacao]

            # Todos os subconjuntos que fecham a conta, não o primeiro. Quando dois fecham, a
            # resposta certa é desconhecida, e escolher um seria o mesmo chute que a estratégia
            # de valor e data já recusa quando há dois títulos iguais.
            achados = [
                grupo
                for tamanho in range(2, min(regras.max_titulos_combinados, len(elegiveis)) + 1)
                for grupo in combinations(elegiveis, tamanho)
                if sum((t.valor for t in grupo), Decimal("0")) == lancamento.valor
            ]
            if len(achados) != 1:
                continue
            achado = achados[0]

            estado.consumir(
                Conciliacao(
                    lancamentos=(lancamento.id,),
                    titulos=tuple(t.id for t in achado),
                    estrategia=Estrategia.UM_PARA_MUITOS,
                    confianca=CONFIANCA_BASE[Estrategia.UM_PARA_MUITOS] * (0.7 + 0.3 * similaridade),
                    situacao=Situacao.CONCILIADO,
                    diferenca=Decimal("0"),
                    motivo=f"crédito igual à soma de {len(achado)} títulos de {sacado}",
                )
            )
            break


def _muitos_para_um(estado: _Estado, regras: Regras) -> None:
    """Vários créditos que somam um título — entrada mais parcela, ou pagamento dividido."""
    lancamentos, titulos = estado.livres_ordenados()

    for titulo in titulos:
        if titulo.id not in estado.titulos_livres:
            continue
        elegiveis = [
            l
            for l in lancamentos
            if l.id in estado.lancamentos_livres
            and l.valor < titulo.valor
            and _na_janela(l, titulo, regras)
            and similaridade_nome(l.descricao, titulo.sacado) >= regras.min_similaridade_nome
        ]
        if len(elegiveis) < 2:
            continue
        elegiveis = elegiveis[: regras.max_titulos_por_sacado_na_combinacao]

        achados = [
            grupo
            for tamanho in range(2, min(regras.max_titulos_combinados, len(elegiveis)) + 1)
            for grupo in combinations(elegiveis, tamanho)
            if sum((l.valor for l in grupo), Decimal("0")) == titulo.valor
        ]
        if len(achados) != 1:
            continue
        achado = achados[0]

        estado.consumir(
            Conciliacao(
                lancamentos=tuple(l.id for l in achado),
                titulos=(titulo.id,),
                estrategia=Estrategia.MUITOS_PARA_UM,
                confianca=CONFIANCA_BASE[Estrategia.MUITOS_PARA_UM],
                situacao=Situacao.CONCILIADO,
                diferenca=Decimal("0"),
                motivo=f"{len(achado)} créditos somam o título {titulo.id} de {titulo.sacado}",
            )
        )


def _por_tolerancia(estado: _Estado, regras: Regras) -> None:
    """Sobra com diferença pequena: tarifa bancária ou desconto. Nunca vira conciliado."""
    lancamentos, titulos = estado.livres_ordenados()

    for lancamento in lancamentos:
        if lancamento.id not in estado.lancamentos_livres:
            continue
        candidatos = [
            t
            for t in titulos
            if t.id in estado.titulos_livres
            and _na_janela(lancamento, t, regras)
            and regras.dentro_da_tolerancia(t.valor, lancamento.valor)
            and similaridade_nome(lancamento.descricao, t.sacado) >= regras.min_similaridade_nome
        ]
        if len(candidatos) != 1:
            continue
        titulo = candidatos[0]
        diferenca = lancamento.valor - titulo.valor
        estado.consumir(
            Conciliacao(
                lancamentos=(lancamento.id,),
                titulos=(titulo.id,),
                estrategia=Estrategia.TOLERANCIA,
                confianca=CONFIANCA_BASE[Estrategia.TOLERANCIA],
                situacao=Situacao.DIVERGENTE,
                diferenca=diferenca,
                motivo=f"diferença de {diferenca:+} cabe na tolerância; confira tarifa ou desconto",
            )
        )


def _candidatos_para_revisao(estado: _Estado, regras: Regras) -> dict[str, tuple[Candidato, ...]]:
    """Para o que não casou, oferece os títulos mais parecidos em vez de devolver lista vazia.

    Uma linha sobrando sem explicação obriga a pessoa a procurar do zero, que é exatamente o
    trabalho manual que a ferramenta existe para evitar.
    """
    lancamentos, titulos = estado.livres_ordenados()
    resultado: dict[str, tuple[Candidato, ...]] = {}

    for lancamento in lancamentos:
        pontuados: list[Candidato] = []
        for titulo in titulos:
            similaridade = similaridade_nome(lancamento.descricao, titulo.sacado)
            distancia = abs((lancamento.data - titulo.vencimento).days)
            proximidade_valor = 1.0 - min(
                1.0, float(abs(lancamento.valor - titulo.valor) / max(titulo.valor, Decimal("0.01")))
            )
            nota = 0.5 * similaridade + 0.35 * proximidade_valor + 0.15 * max(0.0, 1 - distancia / 30)
            if nota < 0.35:
                continue
            razoes = []
            if similaridade > 0:
                razoes.append(f"{similaridade:.0%} do nome")
            if proximidade_valor > 0.9:
                razoes.append("valor próximo")
            if distancia <= regras.janela_dias:
                razoes.append("dentro da janela de data")
            pontuados.append(Candidato(titulo=titulo.id, confianca=round(nota, 3), motivo=", ".join(razoes) or "parcial"))

        pontuados.sort(key=lambda c: (-c.confianca, c.titulo))
        if pontuados:
            resultado[lancamento.id] = tuple(pontuados[:5])

    return resultado


def conciliar(
    lancamentos: list[Lancamento],
    titulos: list[Titulo],
    regras: Regras | None = None,
    apelidos: dict[str, str] | None = None,
) -> Resultado:
    """Concilia extrato contra contas a receber.

    `apelidos` mapeia histórico normalizado para sacado normalizado, alimentado pelas correções
    que um humano já fez. É o único ponto em que a ferramenta usa o passado: o resto é
    determinístico e depende só das entradas desta execução.
    """
    regras = regras or Regras()
    estado = _Estado(lancamentos, titulos)

    _por_documento(estado, regras)
    _por_apelido(estado, regras, apelidos or {})
    _um_para_um(estado, regras, Estrategia.VALOR_DATA)
    _um_para_um(estado, regras, Estrategia.VALOR_NOME)
    _um_para_muitos(estado, regras)
    _muitos_para_um(estado, regras)
    _por_tolerancia(estado, regras)

    return Resultado(
        conciliacoes=tuple(estado.conciliacoes),
        lancamentos_sem_par=tuple(sorted(estado.lancamentos_livres)),
        titulos_sem_par=tuple(sorted(estado.titulos_livres)),
        candidatos=_candidatos_para_revisao(estado, regras),
    )
