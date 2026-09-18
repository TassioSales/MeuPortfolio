"""
Testes da separação entre contato e caso.

`Lead` era as duas coisas ao mesmo tempo. O teste real que motivou isto: um
cliente com caso trabalhista registrado voltou perguntando pelo divórcio da
irmã — dois casos, áreas diferentes, e um deles nem é dele.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.models import Caso, Lead
from app.services.caso_service import ler_ficha, registrar_caso


PARECER = """## Resumo
Cliente relata demissão por justa causa em maio, alegando estar amparado por
atestado médico enviado ao RH.

## Área e possíveis teses
Direito do Trabalho. Reversão com base no art. 482, alínea "i", da CLT.

## Ficha
Área: trabalhista
Titular: o próprio contato
"""

PARECER_DE_TERCEIRO = """## Resumo
O contato pergunta pelo divórcio da irmã, que tem dois filhos menores.

## Ficha
Área: familia
Titular: Marina Sales
"""


class TestLeituraDaFicha:
    def test_le_area_e_titular_proprio(self):
        area, titular = ler_ficha(PARECER)

        assert area == "trabalhista"
        # "o próprio contato" não vira nome: o titular é o lead.
        assert titular is None

    def test_le_titular_de_terceiro(self):
        area, titular = ler_ficha(PARECER_DE_TERCEIRO)

        assert area == "familia"
        assert titular == "Marina Sales"

    def test_area_com_explicacao_junto_ainda_e_reconhecida(self):
        """O modelo tende a explicar: "Área: trabalhista (reversão de justa causa)"."""
        area, _ = ler_ficha("## Ficha\nÁrea: trabalhista (reversão de justa causa)\n")

        assert area == "trabalhista"

    def test_acento_na_area_nao_atrapalha(self):
        area, _ = ler_ficha("## Ficha\nÁrea: Previdenciário\n")

        assert area == "previdenciario"

    def test_ficha_enfeitada_com_markdown_ainda_e_lida(self):
        """
        O prompt pede "Área: trabalhista" em linha limpa, mas pedir "exatamente
        neste formato" não impede um modelo de escrever `- **Área:**
        trabalhista` — é o que ele faz com listas o tempo todo.

        Quando não era lido, o caso não era arquivado e **ninguém ficava
        sabendo**: sem erro, só um lead sem caso. Depois que o gatilho do
        contrato passou a ler a viabilidade do caso, uma ficha enfeitada virou
        contrato que nunca sai.
        """
        variacoes = [
            "- **Área:** trabalhista\n- **Titular:** Maria da Silva",
            "**Área**: trabalhista\n**Titular**: Maria da Silva",
            "• Área: trabalhista\n• Titular: Maria da Silva",
            "* Área: trabalhista\n* Titular: Maria da Silva",
        ]
        for texto in variacoes:
            area, titular = ler_ficha(texto)
            assert area == "trabalhista", f"não leu a área em: {texto!r}"
            assert titular == "Maria da Silva", f"não leu o titular em: {texto!r}"

    def test_parecer_sem_ficha_nao_quebra(self):
        area, titular = ler_ficha("## Resumo\nCaso confuso, faltam dados.")

        assert (area, titular) == (None, None)

    def test_parecer_vazio_nao_quebra(self):
        assert ler_ficha("") == (None, None)


PORTE = """## Porte econômico
Verbas rescisórias sobre 4 anos e 3 meses de casa, mais horas extras.

Valor estimado: R$ 22.000 a R$ 41.500
Viabilidade: acima do piso
"""


class TestLeituraDoPorte:
    def test_le_a_faixa_e_o_veredito(self):
        from app.services.caso_service import ler_porte

        assert ler_porte(PORTE) == (22000, 41500, "acima_do_piso")

    def test_faixa_invertida_e_ordenada_em_vez_de_descartada(self):
        """
        Os dois números estão certos, só trocados de lugar. Descartar perderia
        a estimativa inteira por causa da ordem.
        """
        from app.services.caso_service import ler_porte

        piso, provavel, _ = ler_porte(
            "Valor estimado: R$ 40.000 a R$ 12.000\nViabilidade: acima do piso"
        )

        assert (piso, provavel) == (12000, 40000)

    def test_centavos_sao_descartados(self):
        """Centavo em estimativa preliminar é precisão que o número não tem."""
        from app.services.caso_service import ler_porte

        piso, provavel, _ = ler_porte("Valor estimado: R$ 8.500,00 a R$ 12.300,75")

        assert (piso, provavel) == (8500, 12300)

    def test_abaixo_do_piso_e_reconhecido(self):
        from app.services.caso_service import ler_porte

        assert ler_porte("Viabilidade: abaixo do piso")[2] == "abaixo_do_piso"

    def test_sem_dados_para_dimensionar(self):
        from app.services.caso_service import ler_porte

        assert ler_porte("Viabilidade: não dá para dimensionar")[2] == "indeterminado"

    def test_criminal_nao_se_aplica(self):
        from app.services.caso_service import ler_porte

        assert ler_porte("Viabilidade: não se aplica")[2] == "nao_se_aplica"

    def test_parecer_sem_a_secao_fica_indeterminado_e_nao_inviavel(self):
        """
        A diferença que importa: caso não dimensionado pede uma pergunta; caso
        inviável mandaria descartar. Confundir os dois joga fora caso bom.
        """
        from app.services.caso_service import ler_porte

        assert ler_porte("## Resumo\nCliente relata demissão.") == (
            None,
            None,
            "indeterminado",
        )

    def test_parecer_vazio_nao_quebra(self):
        from app.services.caso_service import ler_porte

        assert ler_porte("") == (None, None, "indeterminado")


def _db(caso_existente=None):
    db = AsyncMock()
    resultado = MagicMock()
    resultado.scalars.return_value.first.return_value = caso_existente
    db.execute = AsyncMock(return_value=resultado)
    db.flush = AsyncMock()
    return db


def _lead(nome=None):
    lead = MagicMock(spec=Lead)
    lead.id = "lead-1"
    lead.nome = nome
    return lead


class TestRegistroDoCaso:
    async def test_abre_caso_novo_com_area_titular_e_resumo(self):
        db = _db()

        caso = await registrar_caso(_lead(), PARECER_DE_TERCEIRO, 80, db)

        assert caso.area == "familia"
        assert caso.titular == "Marina Sales"
        assert "divórcio da irmã" in caso.resumo
        assert caso.score_qualificacao == 80
        assert db.add.called

    async def test_mesma_area_atualiza_em_vez_de_duplicar(self):
        """
        Dois relatos trabalhistas do mesmo contato são o mesmo caso.

        A área é o critério porque é o que o sistema reconhece sozinho —
        separar dois casos da mesma área é decisão do advogado.
        """
        existente = MagicMock(spec=Caso)
        existente.area = "trabalhista"
        db = _db(caso_existente=existente)

        caso = await registrar_caso(_lead(), PARECER, 90, db)

        assert caso is existente
        assert not db.add.called
        assert caso.score_qualificacao == 90

    async def test_titular_igual_ao_contato_nao_vira_caso_de_terceiro(self):
        """
        O modelo repete o nome em vez de escrever "o próprio contato".

        Aconteceu no primeiro parecer gerado com o prompt novo: a ficha voltou
        com "Titular: Jonas Ferreira da Silva", que é quem estava escrevendo.
        Guardar isso põe a tarja "de Jonas Ferreira da Silva" no caso do
        próprio Jonas — e a tarja existe para avisar que a parte é outra
        pessoa. Aparecendo sempre, ela deixa de avisar qualquer coisa.
        """
        parecer = "## Resumo\nDemissão por justa causa.\n\n## Ficha\nÁrea: trabalhista\nTitular: Jonas Ferreira da Silva\n"
        db = _db()

        caso = await registrar_caso(_lead(nome="Jonas Ferreira da Silva"), parecer, 70, db)

        assert caso.titular is None

    async def test_titular_de_outra_pessoa_continua_marcado(self):
        db = _db()

        caso = await registrar_caso(_lead(nome="Pedro Sales"), PARECER_DE_TERCEIRO, 70, db)

        assert caso.titular == "Marina Sales"

    async def test_o_porte_e_gravado_junto_com_o_caso(self):
        db = _db()

        caso = await registrar_caso(_lead(), PARECER + "\n" + PORTE, 80, db)

        assert (caso.valor_estimado_min, caso.valor_estimado_max) == (22000, 41500)
        assert caso.viabilidade == "acima_do_piso"

    async def test_sem_parecer_nao_abre_caso(self):
        db = _db()

        assert await registrar_caso(_lead(), None, 0, db) is None
        assert not db.add.called

    async def test_parecer_sem_area_nao_abre_caso(self):
        """Registro sem área seria um caso que ninguém consegue classificar."""
        db = _db()

        assert await registrar_caso(_lead(), "## Resumo\nSem ficha.", 50, db) is None
        assert not db.add.called
