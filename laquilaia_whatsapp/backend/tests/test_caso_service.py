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

    def test_parecer_sem_ficha_nao_quebra(self):
        area, titular = ler_ficha("## Resumo\nCaso confuso, faltam dados.")

        assert (area, titular) == (None, None)

    def test_parecer_vazio_nao_quebra(self):
        assert ler_ficha("") == (None, None)


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

    async def test_sem_parecer_nao_abre_caso(self):
        db = _db()

        assert await registrar_caso(_lead(), None, 0, db) is None
        assert not db.add.called

    async def test_parecer_sem_area_nao_abre_caso(self):
        """Registro sem área seria um caso que ninguém consegue classificar."""
        db = _db()

        assert await registrar_caso(_lead(), "## Resumo\nSem ficha.", 50, db) is None
        assert not db.add.called
