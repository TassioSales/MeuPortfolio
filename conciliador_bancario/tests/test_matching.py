from decimal import Decimal

import pytest

from core.matching import conciliar
from core.modelos import Estrategia, Situacao
from core.regras import Regras


class TestDocumento:
    def test_casa_pelo_numero_no_historico(self, credito, titulo):
        r = conciliar(
            [credito("L1", 10, "1500.00", "LIQUIDACAO BOLETO 000998877")],
            [titulo("T1", 10, "1500.00", "Outro Nome Qualquer", documento="998877")],
        )
        assert len(r.conciliacoes) == 1
        assert r.conciliacoes[0].estrategia is Estrategia.DOCUMENTO
        # O nome não bate e mesmo assim casou: o documento é prova mais forte que o nome.
        assert r.conciliacoes[0].confianca == pytest.approx(0.99)

    def test_documento_ambiguo_nao_casa(self, credito, titulo):
        r = conciliar(
            [credito("L1", 10, "100.00", "BOLETO 998877")],
            [titulo("T1", 10, "100.00", "A", documento="998877"), titulo("T2", 10, "100.00", "B", documento="998877")],
        )
        assert r.conciliacoes == ()

    def test_documento_certo_valor_muito_diferente_nao_casa(self, credito, titulo):
        r = conciliar(
            [credito("L1", 10, "100.00", "BOLETO 998877")],
            [titulo("T1", 10, "5000.00", "A", documento="998877")],
        )
        assert r.conciliacoes == ()


class TestValorEData:
    def test_candidato_unico_casa(self, credito, titulo):
        r = conciliar([credito("L1", 10, "900.00", "TED RECEBIDA")], [titulo("T1", 12, "900.00", "Cliente X")])
        assert r.conciliacoes[0].estrategia is Estrategia.VALOR_DATA
        assert r.conciliacoes[0].situacao is Situacao.CONCILIADO

    def test_dois_titulos_do_mesmo_valor_sem_nome_nao_casa(self, credito, titulo):
        # Escolher um dos dois seria adivinhação, e adivinhação aqui vira erro contábil.
        r = conciliar(
            [credito("L1", 10, "900.00", "DEPOSITO")],
            [titulo("T1", 10, "900.00", "Cliente X"), titulo("T2", 11, "900.00", "Cliente Y")],
        )
        assert r.conciliacoes == ()
        assert r.lancamentos_sem_par == ("L1",)

    def test_fora_da_janela_nao_casa(self, credito, titulo):
        r = conciliar([credito("L1", 20, "900.00", "TED")], [titulo("T1", 1, "900.00", "Cliente X")])
        assert r.conciliacoes == ()

    def test_data_mais_distante_reduz_confianca(self, credito, titulo):
        perto = conciliar([credito("L1", 10, "900.00", "TED")], [titulo("T1", 10, "900.00", "X")])
        longe = conciliar([credito("L1", 15, "900.00", "TED")], [titulo("T1", 10, "900.00", "X")])
        assert longe.conciliacoes[0].confianca < perto.conciliacoes[0].confianca


class TestValorENome:
    def test_desempata_pelo_nome(self, credito, titulo):
        r = conciliar(
            [credito("L1", 10, "900.00", "PIX MERCADO CENTRAL")],
            [titulo("T1", 10, "900.00", "Padaria do João"), titulo("T2", 10, "900.00", "Mercado Central")],
        )
        assert len(r.conciliacoes) == 1
        assert r.conciliacoes[0].titulos == ("T2",)
        assert r.conciliacoes[0].estrategia is Estrategia.VALOR_NOME

    def test_nome_fraco_nao_casa(self, credito, titulo):
        r = conciliar(
            [credito("L1", 10, "900.00", "PIX ALGUEM")],
            [titulo("T1", 10, "900.00", "Padaria do João"), titulo("T2", 10, "900.00", "Mercado Central")],
        )
        assert r.conciliacoes == ()


class TestUmParaMuitos:
    def test_um_deposito_quita_tres_boletos(self, credito, titulo):
        r = conciliar(
            [credito("L1", 10, "600.00", "PIX MERCADO CENTRAL")],
            [
                titulo("T1", 9, "100.00", "Mercado Central"),
                titulo("T2", 10, "200.00", "Mercado Central"),
                titulo("T3", 11, "300.00", "Mercado Central"),
            ],
        )
        assert len(r.conciliacoes) == 1
        assert r.conciliacoes[0].estrategia is Estrategia.UM_PARA_MUITOS
        assert set(r.conciliacoes[0].titulos) == {"T1", "T2", "T3"}
        assert r.titulos_sem_par == ()

    def test_nao_combina_titulos_de_clientes_diferentes(self, credito, titulo):
        r = conciliar(
            [credito("L1", 10, "600.00", "PIX MERCADO CENTRAL")],
            [titulo("T1", 10, "100.00", "Mercado Central"), titulo("T2", 10, "500.00", "Padaria do João")],
        )
        assert r.conciliacoes == ()

    def test_respeita_o_limite_de_parcelas(self, credito, titulo):
        titulos = [titulo(f"T{i}", 10, "100.00", "Mercado Central") for i in range(1, 6)]
        r = conciliar([credito("L1", 10, "500.00", "PIX MERCADO CENTRAL")], titulos, Regras(max_titulos_combinados=4))
        assert r.conciliacoes == ()

    def test_com_o_limite_maior_encontra(self, credito, titulo):
        titulos = [titulo(f"T{i}", 10, "100.00", "Mercado Central") for i in range(1, 6)]
        r = conciliar([credito("L1", 10, "500.00", "PIX MERCADO CENTRAL")], titulos, Regras(max_titulos_combinados=5))
        assert len(r.conciliacoes[0].titulos) == 5


class TestMuitosParaUm:
    def test_entrada_mais_parcela(self, credito, titulo):
        r = conciliar(
            [credito("L1", 9, "400.00", "PIX PADARIA DO JOAO"), credito("L2", 11, "600.00", "PIX PADARIA DO JOAO")],
            [titulo("T1", 10, "1000.00", "Padaria do João")],
        )
        assert len(r.conciliacoes) == 1
        assert r.conciliacoes[0].estrategia is Estrategia.MUITOS_PARA_UM
        assert set(r.conciliacoes[0].lancamentos) == {"L1", "L2"}


class TestTolerancia:
    def test_tarifa_bancaria_vira_divergencia_nao_conciliado(self, credito, titulo):
        r = conciliar([credito("L1", 10, "996.50", "TED MERCADO CENTRAL")], [titulo("T1", 10, "1000.00", "Mercado Central")])
        assert r.conciliacoes[0].estrategia is Estrategia.TOLERANCIA
        assert r.conciliacoes[0].situacao is Situacao.DIVERGENTE
        assert r.conciliacoes[0].diferenca == Decimal("-3.50")

    def test_diferenca_grande_nao_entra_na_tolerancia(self, credito, titulo):
        r = conciliar([credito("L1", 10, "500.00", "TED MERCADO CENTRAL")], [titulo("T1", 10, "1000.00", "Mercado Central")])
        assert r.conciliacoes == ()


class TestApelidoAprendido:
    def test_desfaz_ambiguidade_que_o_nome_nao_resolve(self, credito, titulo):
        # Histórico opaco, dois títulos do mesmo valor: sem o apelido não há como escolher.
        descricao = "CRED TEF 0002 CONTA 44"
        lancamentos = [credito("L1", 10, "750.00", descricao)]
        titulos = [titulo("T1", 10, "750.00", "Distribuidora Alfa"), titulo("T2", 10, "750.00", "Comercial Beta")]

        sem = conciliar(lancamentos, titulos)
        assert sem.conciliacoes == ()

        com = conciliar(lancamentos, titulos, apelidos={descricao: "DISTRIBUIDORA ALFA"})
        assert com.conciliacoes[0].estrategia is Estrategia.APELIDO
        assert com.conciliacoes[0].titulos == ("T1",)

    def test_apelido_nao_atropela_a_janela_de_data(self, credito, titulo):
        descricao = "CRED TEF 0002"
        r = conciliar(
            [credito("L1", 28, "750.00", descricao)],
            [titulo("T1", 1, "750.00", "Distribuidora Alfa")],
            apelidos={descricao: "DISTRIBUIDORA ALFA"},
        )
        assert r.conciliacoes == ()


class TestInvariantes:
    def test_nenhum_titulo_e_quitado_duas_vezes(self, credito, titulo):
        r = conciliar(
            [credito(f"L{i}", 10, "100.00", "PIX MERCADO CENTRAL") for i in range(1, 4)],
            [titulo("T1", 10, "100.00", "Mercado Central")],
        )
        usados = [t for c in r.conciliacoes for t in c.titulos]
        assert len(usados) == len(set(usados))

    def test_nenhum_lancamento_e_usado_duas_vezes(self, credito, titulo):
        r = conciliar(
            [credito("L1", 10, "100.00", "PIX MERCADO CENTRAL")],
            [titulo(f"T{i}", 10, "100.00", "Mercado Central") for i in range(1, 4)],
        )
        usados = [l for c in r.conciliacoes for l in c.lancamentos]
        assert len(usados) == len(set(usados))

    def test_determinismo_a_ordem_da_entrada_nao_muda_a_saida(self, credito, titulo):
        lancamentos = [credito(f"L{i}", 10, f"{i}00.00", f"PIX CLIENTE {i}") for i in range(1, 6)]
        titulos = [titulo(f"T{i}", 10, f"{i}00.00", f"Cliente {i}") for i in range(1, 6)]
        direto = conciliar(lancamentos, titulos)
        invertido = conciliar(list(reversed(lancamentos)), list(reversed(titulos)))
        assert [(c.lancamentos, c.titulos) for c in direto.conciliacoes] == [
            (c.lancamentos, c.titulos) for c in invertido.conciliacoes
        ]

    def test_entrada_vazia(self):
        r = conciliar([], [])
        assert r.conciliacoes == () and r.lancamentos_sem_par == () and r.titulos_sem_par == ()

    def test_documento_vence_valor_e_data(self, credito, titulo):
        # T2 casaria por valor e data; o documento manda no T1, e T2 sobra.
        r = conciliar(
            [credito("L1", 10, "100.00", "BOLETO 555555")],
            [titulo("T1", 12, "100.00", "Nome Distinto", documento="555555"), titulo("T2", 10, "100.00", "Outro")],
        )
        assert r.conciliacoes[0].titulos == ("T1",)
        assert r.titulos_sem_par == ("T2",)


class TestCandidatos:
    def test_oferece_sugestao_para_o_que_sobrou(self, credito, titulo):
        r = conciliar([credito("L1", 10, "1000.00", "PIX MERCADO CENTRAL")], [titulo("T1", 10, "1400.00", "Mercado Central")])
        assert r.conciliacoes == ()
        assert r.candidatos["L1"][0].titulo == "T1"
        assert "nome" in r.candidatos["L1"][0].motivo

    def test_nao_sugere_o_que_nao_tem_nada_a_ver(self, credito, titulo):
        r = conciliar([credito("L1", 1, "10.00", "PIX ALFA")], [titulo("T1", 28, "90000.00", "Beta")])
        assert r.candidatos.get("L1") is None
