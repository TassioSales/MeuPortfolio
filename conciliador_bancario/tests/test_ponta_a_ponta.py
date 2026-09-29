"""Percorre o caminho inteiro: gerar, escrever OFX e CSV, reler, conciliar e relatar.

Os testes de unidade passam com objetos montados na mão. Este é o que pega o erro que só aparece
quando um módulo escreve o que o outro lê.
"""

from decimal import Decimal

from core.importacao import ler_titulos_csv
from core.matching import conciliar
from core.modelos import Situacao
from core.ofx import ler_ofx
from core.relatorio import para_tabela, pendencias, resumir
from dados_exemplo.gerar import gerar, para_csv, para_ofx


def test_ciclo_completo_pelos_arquivos():
    cenario = gerar(60, semente=1)

    lancamentos = ler_ofx(para_ofx(cenario.lancamentos))
    titulos = ler_titulos_csv(para_csv(cenario.titulos))

    assert len(lancamentos) == len(cenario.lancamentos)
    assert len(titulos) == len(cenario.titulos)
    assert {l.id for l in lancamentos} == {l.id for l in cenario.lancamentos}

    resultado = conciliar(lancamentos, titulos)
    resumo = resumir(resultado, lancamentos, titulos)

    assert resumo.conciliados > 0
    assert resumo.cobertura > 0.7
    assert resumo.lancamentos == len(lancamentos)

    tabela = para_tabela(resultado, lancamentos, titulos)
    assert tabela.height == len(resultado.conciliacoes)
    assert set(tabela.columns) >= {"situacao", "estrategia", "confianca", "motivo", "diferenca"}
    # Divergência antes de conciliado: é o que alguém precisa olhar.
    if resumo.divergentes and resumo.conciliados:
        assert tabela["situacao"][0] == Situacao.DIVERGENTE.value

    assert pendencias(resultado, lancamentos, titulos).height == len(resultado.lancamentos_sem_par)


def test_nenhum_credito_avulso_e_conciliado():
    """Estorno e aporte não quitam título, e o motor não pode inventar par para eles."""
    cenario = gerar(80, semente=3)
    resultado = conciliar(cenario.lancamentos, cenario.titulos)

    avulsos = {
        l.id
        for l in cenario.lancamentos
        if any(marca in l.descricao for marca in ("ESTORNO", "CONTAS PROPRIAS", "APORTE"))
    }
    conciliados = {i for c in resultado.conciliacoes for i in c.lancamentos}
    assert avulsos - conciliados == avulsos


def test_relatorio_vazio_mantem_o_formato():
    resultado = conciliar([], [])
    assert para_tabela(resultado, [], []).height == 0
    assert "motivo" in para_tabela(resultado, [], []).columns
    assert pendencias(resultado, [], []).height == 0


def test_resumo_soma_o_que_ficou_em_aberto():
    cenario = gerar(40, semente=5)
    resultado = conciliar(cenario.lancamentos, cenario.titulos)
    resumo = resumir(resultado, cenario.lancamentos, cenario.titulos)

    esperado = sum(
        (t.valor for t in cenario.titulos if t.id in resultado.titulos_sem_par), Decimal("0")
    )
    assert resumo.valor_em_aberto == esperado


def test_apelido_aprendido_aumenta_a_cobertura():
    """O ganho do aprendizado precisa ser mensurável, não só existir."""
    cenario = gerar(120, semente=11)
    sem = conciliar(cenario.lancamentos, cenario.titulos)

    # Ensina os históricos opacos que sobraram, usando o gabarito como se fosse um humano.
    por_id_titulo = {t.id: t for t in cenario.titulos}
    por_id_lancamento = {l.id: l for l in cenario.lancamentos}
    apelidos = {}
    for ids_lancamento, ids_titulo in cenario.gabarito:
        (id_lancamento,) = tuple(ids_lancamento)[:1] or ("",)
        if id_lancamento in sem.lancamentos_sem_par:
            from core.normalizacao import normalizar

            apelidos[normalizar(por_id_lancamento[id_lancamento].descricao)] = normalizar(
                por_id_titulo[tuple(ids_titulo)[0]].sacado
            )

    com = conciliar(cenario.lancamentos, cenario.titulos, apelidos=apelidos)
    assert len(com.lancamentos_sem_par) < len(sem.lancamentos_sem_par)
