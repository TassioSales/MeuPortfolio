"""
De que estado vem o telefone.

Não há campo de endereço no cadastro, e perguntar o estado seria mais uma
pergunta antes de ouvir o caso. O DDD já está no número desde o primeiro
contato.

O que estes casos protegem é o silêncio: número de fora, DDD que não existe e
número truncado precisam devolver `None`, não um estado chutado. O escritório
move orçamento de campanha com base nessa tela.
"""

import pytest

from app.utils.ddd import DDD_POR_UF, UF_POR_DDD, uf_do_telefone


class TestOsFormatosQueChegam:
    @pytest.mark.parametrize(
        "numero,esperado",
        [
            ("5561999887766", "DF"),          # como a Evolution entrega
            ("+55 (61) 99988-7766", "DF"),    # colado do WhatsApp
            ("61999887766", "DF"),            # sem o código do país
            ("556133334444", "DF"),           # fixo, oito dígitos
            ("5511984479999", "SP"),
            ("5571988887777", "BA"),
        ],
    )
    def test_le_o_estado(self, numero, esperado):
        assert uf_do_telefone(numero) == esperado


class TestOSilencio:
    @pytest.mark.parametrize(
        "numero",
        [
            None,
            "",
            "12345",                 # curto demais
            "5500999887766",         # DDD 00 não existe
            "5523999887766",         # 23 não é DDD em uso
            "351912345678",          # Portugal
            "5561999887766999",      # longo demais
            "abcdefg",
        ],
    )
    def test_devolve_none_em_vez_de_chutar(self, numero):
        """
        Um estado errado é pior que "não sei": ninguém desconfia de um dado
        que parece certo, e a campanha muda de praça por causa dele.
        """
        assert uf_do_telefone(numero) is None


class TestATabela:
    def test_cobre_as_27_unidades_federativas(self):
        assert len(DDD_POR_UF) == 27

    def test_nenhum_ddd_em_dois_estados(self):
        """
        Um DDD duplicado passaria despercebido — o `dict` invertido ficaria
        com o último e a contagem de um dos estados sumiria em silêncio.
        """
        todos = [ddd for ddds in DDD_POR_UF.values() for ddd in ddds]
        assert len(todos) == len(set(todos))
        assert len(UF_POR_DDD) == len(todos)

    def test_todo_ddd_tem_dois_digitos(self):
        assert all(len(d) == 2 and d.isdigit() for d in UF_POR_DDD)
