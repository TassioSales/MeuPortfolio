from decimal import Decimal

import pytest

from core.modelos import Conciliacao, Estrategia, Situacao
from core.persistencia import Repositorio


@pytest.fixture
def repo(tmp_path):
    return Repositorio(tmp_path / "t.db")


def conc(estrategia=Estrategia.VALOR_DATA):
    return Conciliacao(("L1",), ("T1",), estrategia, 0.9, Situacao.CONCILIADO, Decimal("0"), "x")


def test_aprende_apelido_quando_o_nome_nao_estava_no_historico(repo):
    repo.registrar(conc(), aceita=True, historico="CRED TEF 0002 CONTA 44", sacado="Distribuidora Alfa")
    assert repo.apelidos() == {"CRED TEF 0002 CONTA 44": "DISTRIBUIDORA ALFA"}


def test_nao_aprende_quando_o_nome_ja_aparecia(repo):
    # A similaridade já resolveria; gravar a regra seria peso morto.
    repo.registrar(conc(), aceita=True, historico="PIX DISTRIBUIDORA ALFA", sacado="Distribuidora Alfa")
    assert repo.apelidos() == {}


def test_nao_aprende_com_decisao_rejeitada(repo):
    repo.registrar(conc(), aceita=False, historico="CRED TEF 0002", sacado="Distribuidora Alfa")
    assert repo.apelidos() == {}


def test_reaprender_atualiza_em_vez_de_duplicar(repo):
    repo.registrar(conc(), aceita=True, historico="CRED TEF 0002", sacado="Alfa")
    repo.registrar(conc(), aceita=True, historico="CRED TEF 0002", sacado="Beta")
    assert repo.apelidos() == {"CRED TEF 0002": "BETA"}


def test_esquecer_apelido_errado(repo):
    repo.registrar(conc(), aceita=True, historico="CRED TEF 0002", sacado="Alfa")
    assert repo.esquecer("cred tef 0002") is True
    assert repo.apelidos() == {}


def test_esquecer_o_que_nao_existe(repo):
    assert repo.esquecer("NADA") is False


def test_registra_decisao_aceita_e_rejeitada(repo):
    repo.registrar(conc(), aceita=True)
    repo.registrar(conc(Estrategia.TOLERANCIA), aceita=False)
    historico = repo.historico_de_decisoes()
    assert len(historico) == 2
    assert {h["aceita"] for h in historico} == {0, 1}


def test_banco_novo_nao_quebra_ao_reabrir(tmp_path):
    caminho = tmp_path / "t.db"
    Repositorio(caminho).registrar(conc(), aceita=True, historico="X 0002", sacado="Alfa")
    assert Repositorio(caminho).apelidos() == {"X 0002": "ALFA"}
