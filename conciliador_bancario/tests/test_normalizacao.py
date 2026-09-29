import pytest

from core.normalizacao import extrair_documentos, normalizar, similaridade_nome, tokens_significativos


class TestNormalizar:
    @pytest.mark.parametrize(
        "entrada,esperado",
        [
            ("Padaria do João LTDA.", "PADARIA DO JOAO LTDA"),
            ("  TED   033  ", "TED 033"),
            ("Açaí & Cia", "ACAI CIA"),
            ("", ""),
            (None, ""),
        ],
    )
    def test_casos(self, entrada, esperado):
        assert normalizar(entrada) == esperado


class TestTokens:
    def test_descarta_ruido_bancario(self):
        assert tokens_significativos("TED RECEBIDA PADARIA JOAO") == frozenset({"PADARIA", "JOAO"})

    def test_descarta_sufixo_societario(self):
        assert "LTDA" not in tokens_significativos("MERCADO CENTRAL LTDA")

    def test_descarta_numero_solto(self):
        # Agência e conta aparecem no histórico e casariam entre clientes diferentes.
        assert tokens_significativos("PIX 0341 12345 MERCADO") == frozenset({"MERCADO"})

    def test_descarta_palavra_curta(self):
        assert tokens_significativos("PIX DE AB MERCADO") == frozenset({"MERCADO"})


class TestSimilaridade:
    def test_nome_inteiro_presente(self):
        assert similaridade_nome("PIX QRS PADARIA DO JOAO", "Padaria do João LTDA") == 1.0

    def test_nome_parcial(self):
        assert similaridade_nome("TED PADARIA", "Padaria do João") == pytest.approx(0.5)

    def test_nome_ausente(self):
        assert similaridade_nome("TED CLIENTE Y", "Padaria do João") == 0.0

    def test_sacado_vazio_nao_casa_com_nada(self):
        assert similaridade_nome("QUALQUER COISA", "") == 0.0

    def test_ruido_extra_no_historico_nao_penaliza(self):
        # Contenção, não Jaccard: o extrato sempre traz palavras que o nome do cliente não tem.
        muito_ruido = "TED 033 RECEBIDA BANCO AG 0001 CC 12345 PADARIA DO JOAO ONLINE"
        assert similaridade_nome(muito_ruido, "Padaria do João") == 1.0


class TestDocumentos:
    def test_extrai_sequencia_longa(self):
        assert extrair_documentos("LIQUIDACAO BOLETO 000123456") == frozenset({"123456"})

    def test_ignora_sequencia_curta(self):
        assert extrair_documentos("AG 0001 CC 123") == frozenset()

    def test_varios_documentos(self):
        assert extrair_documentos("BOLETO 111111 E 222222") == frozenset({"111111", "222222"})
