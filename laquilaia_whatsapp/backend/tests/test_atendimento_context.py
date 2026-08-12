"""
Testes da memória entre atendimentos.

Quem já foi atendido e volta não pode ouvir "seu caso é sobre o quê?" outra
vez: para o cliente parece que o escritório esqueceu, e para o escritório o
mesmo caso chega duas vezes.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.models import Lead, LeadDetails
from app.services.atendimento_context import (
    MENSAGENS_DE_CONTEXTO,
    com_nota,
    nota_de_atendimento_anterior,
)


def _db(lead=None, detalhes=None, total_mensagens=0):
    """Sessão que responde às três consultas na ordem em que são feitas."""
    respostas = []

    r_lead = MagicMock()
    r_lead.scalars.return_value.first.return_value = lead
    respostas.append(r_lead)

    if lead is not None:
        r_det = MagicMock()
        r_det.scalars.return_value.first.return_value = detalhes
        respostas.append(r_det)

        r_total = MagicMock()
        r_total.scalar.return_value = total_mensagens
        respostas.append(r_total)

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=respostas)
    return db


def _lead(**kwargs):
    lead = MagicMock(spec=Lead)
    lead.id = kwargs.get("id", "lead-1")
    lead.nome = kwargs.get("nome", "Tássio Sales")
    lead.status_funil = kwargs.get("status_funil", "qualificado")
    lead.data_criacao = kwargs.get("data_criacao", datetime(2026, 8, 10, 9, 0))
    return lead


class TestPrimeiroContato:
    async def test_numero_desconhecido_nao_gera_nota(self):
        """Sem nota, o agente abre a triagem normalmente."""
        assert await nota_de_atendimento_anterior("5561999", "conv-1", _db()) is None


class TestRetorno:
    async def test_nota_traz_nome_situacao_e_a_instrucao(self):
        nota = await nota_de_atendimento_anterior(
            "5561999", "conv-1", _db(lead=_lead(), total_mensagens=12)
        )

        assert "Tássio Sales" in nota
        assert "qualificado" in nota
        assert "10/08/2026" in nota
        assert "12" in nota
        # A instrução é o que muda o comportamento; sem ela a nota é decoração.
        assert "Não recomece a triagem do zero" in nota

    async def test_nota_se_identifica_como_sistema(self):
        """
        O modelo precisa saber que aquilo não veio do cliente.

        A nota entra no papel de usuário — é o único canal disponível sem
        alterar o system prompt, que é do dono do agente —, e sem o rótulo o
        agente responderia a ela como se fosse mensagem de quem está do outro
        lado.
        """
        nota = await nota_de_atendimento_anterior(
            "5561999", "conv-1", _db(lead=_lead(), total_mensagens=3)
        )

        assert nota.startswith("[Nota do sistema")
        assert "não é mensagem do cliente" in nota

    async def test_leva_o_resumo_do_parecer_mas_nao_o_parecer_inteiro(self):
        """
        Só a primeira seção.

        O parecer traz teses, prazos e pontos fracos — material do advogado. Um
        agente com isso no contexto acaba repetindo tese para o cliente, que é
        exatamente o que o prompt de triagem proíbe.
        """
        detalhes = MagicMock(spec=LeadDetails)
        detalhes.analise_preliminar = (
            "## Resumo\nCliente relata demissão por justa causa em maio.\n\n"
            "## Área e possíveis teses\nReversão com base no art. 482 da CLT.\n\n"
            "## Pontos fracos\nPode haver faltas não cobertas por atestado."
        )

        nota = await nota_de_atendimento_anterior(
            "5561999", "conv-1", _db(lead=_lead(), detalhes=detalhes, total_mensagens=8)
        )

        assert "demissão por justa causa em maio" in nota
        assert "art. 482" not in nota
        assert "Pontos fracos" not in nota

    async def test_lead_sem_nome_nao_quebra(self):
        lead = _lead(nome=None)

        nota = await nota_de_atendimento_anterior(
            "5561999", "conv-1", _db(lead=lead, total_mensagens=1)
        )

        assert "sem nome registrado" in nota


class TestMontagemDoHistorico:
    def test_nota_vai_na_frente_do_historico(self):
        historico = [{"role": "user", "content": "oi"}]

        resultado = com_nota(historico, "[Nota do sistema] já atendido")

        assert resultado[0]["content"].startswith("[Nota do sistema]")
        assert resultado[1] == historico[0]

    def test_sem_nota_o_historico_passa_intacto(self):
        historico = [{"role": "user", "content": "oi"}]

        assert com_nota(historico, None) is historico


class TestJanelaDeContexto:
    def test_janela_cobre_uma_triagem_inteira(self):
        """
        Eram 5 mensagens, e uma triagem passa disso no terceiro par de
        perguntas — o relato do caso saía da janela antes de a conversa
        terminar, e o agente esquecia o que estava apurando.
        """
        assert MENSAGENS_DE_CONTEXTO >= 20
