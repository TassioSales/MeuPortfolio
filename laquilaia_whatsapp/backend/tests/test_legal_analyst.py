"""
Testes do parecer preliminar.

O ponto central é o isolamento: o parecer é insumo interno e não pode, em
nenhuma hipótese, vazar para a conversa com o cliente nem derrubar a
qualificação do lead quando falhar.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import settings
from app.db.models import Message
from app.services.legal_analyst import LegalAnalyst, legal_analyst


def _sessao_com_mensagens(mensagens):
    db = AsyncMock()
    resultado = MagicMock()
    resultado.scalars.return_value.all.return_value = mensagens
    db.execute = AsyncMock(return_value=resultado)
    return db


def _msg(remetente, conteudo):
    m = MagicMock(spec=Message)
    m.remetente = remetente
    m.conteudo = conteudo
    return m


class TestTranscricao:
    async def test_conversa_vira_transcricao_rotulada(self):
        db = _sessao_com_mensagens(
            [
                _msg("user", "fui demitido por justa causa"),
                _msg("assistant", "Quando foi?"),
                _msg("user", "faz dois meses"),
            ]
        )

        texto = await LegalAnalyst()._transcrever("conv-1", db)

        assert "CLIENTE: fui demitido por justa causa" in texto
        assert "ATENDIMENTO: Quando foi?" in texto
        # A ordem importa: um relato fora de ordem muda o caso.
        assert texto.index("justa causa") < texto.index("dois meses")

    async def test_conversa_vazia_nao_gera_parecer(self):
        db = _sessao_com_mensagens([])

        assert await legal_analyst.analisar("conv-vazia", db) is None


class TestIsolamento:
    async def test_desligado_devolve_none_sem_chamar_o_modelo(self):
        db = _sessao_com_mensagens([_msg("user", "oi")])

        with patch.object(settings, "analise_juridica_enabled", False):
            with patch(
                "app.services.llm_service.llm_service.analisar_com_prompt"
            ) as chamada:
                assert await legal_analyst.analisar("conv-1", db) is None
                chamada.assert_not_called()

    async def test_falha_do_modelo_nao_propaga(self):
        """
        Um parecer que falhou não pode derrubar a qualificação do lead.

        A análise é acessória: perder o insumo é aceitável, perder o lead —
        que já custou a conversa inteira — não.
        """
        db = _sessao_com_mensagens([_msg("user", "fui demitido")])

        with patch.object(settings, "analise_juridica_enabled", True), patch(
            "app.services.llm_service.llm_service.analisar_com_prompt",
            side_effect=RuntimeError("provedor fora do ar"),
        ):
            assert await legal_analyst.analisar("conv-1", db) is None

    async def test_parecer_gerado_volta_como_markdown(self):
        db = _sessao_com_mensagens([_msg("user", "fui demitido por justa causa")])
        parecer = "## Resumo\nCliente relata demissão por justa causa."

        with patch.object(settings, "analise_juridica_enabled", True), patch(
            "app.services.llm_service.llm_service.analisar_com_prompt",
            new=AsyncMock(return_value=(parecer, {"total_tokens": 400, "model": "x"})),
        ):
            assert await legal_analyst.analisar("conv-1", db) == parecer


class TestModeloDoParecer:
    """
    O parecer roda no modelo dele, não no do atendimento.

    São tarefas diferentes: o atendimento troca frases curtas no WhatsApp e o
    parecer é a peça que o advogado lê antes de decidir o caso. Como é uma
    chamada por lead qualificado, o modelo melhor sai barato aqui.
    """

    async def _analisar_capturando(self, **override):
        db = _sessao_com_mensagens([_msg("user", "fui demitido por justa causa")])
        chamada = AsyncMock(return_value=("## Resumo\nx", {"total_tokens": 1, "model": "m"}))

        with patch.object(settings, "analise_juridica_enabled", True), patch.multiple(
            settings, **override
        ), patch("app.services.llm_service.llm_service.analisar_com_prompt", new=chamada):
            await legal_analyst.analisar("conv-1", db)

        return chamada.call_args.kwargs

    async def test_usa_os_modelos_configurados_para_a_analise(self):
        kwargs = await self._analisar_capturando(
            analise_claude_model="claude-opus-5",
            analise_gemini_model="gemini-pro-latest",
        )

        assert kwargs["modelo_claude"] == "claude-opus-5"
        assert kwargs["modelo_gemini"] == "gemini-pro-latest"

    async def test_sem_configuracao_cai_no_modelo_do_atendimento(self):
        """
        Vazio precisa virar `None`, e não string vazia.

        String vazia chegaria como nome de modelo na URL do Gemini e daria 404
        — no exato momento em que o Claude falhou e a reserva era a única
        chance de o parecer sair.
        """
        kwargs = await self._analisar_capturando(
            analise_claude_model="", analise_gemini_model=""
        )

        assert kwargs["modelo_claude"] is None
        assert kwargs["modelo_gemini"] is None


class TestPromptDoAnalista:
    """O prompt é o produto aqui — estas travas descrevem o que ele promete."""

    def test_proibe_afirmar_fato_e_estimar_valor(self):
        from app.services.legal_analyst import PROMPT_ANALISTA

        assert "não tem os documentos" in PROMPT_ANALISTA
        assert "Não estime valor" in PROMPT_ANALISTA
        assert "Não prometa resultado" in PROMPT_ANALISTA

    def test_deixa_claro_que_o_leitor_e_o_advogado(self):
        from app.services.legal_analyst import PROMPT_ANALISTA

        assert "não o cliente" in PROMPT_ANALISTA

    def test_pede_as_secoes_que_o_painel_espera(self):
        from app.services.legal_analyst import PROMPT_ANALISTA

        for secao in (
            "## Resumo",
            "## Área e possíveis teses",
            "## Jurisprudência",
            "## Provas e ônus",
            "## Documentos a pedir",
            "## Prazos e urgência",
            "## Caminhos possíveis",
            "## Pontos fracos",
            "## Ficha",
        ):
            assert secao in PROMPT_ANALISTA

    def test_o_resumo_e_a_primeira_secao(self):
        """
        `caso_service._resumo_do_parecer` lê a primeira seção, qualquer que
        seja o título dela. Se outra seção subir para o topo, o resumo do caso
        no painel vira a lista de teses.
        """
        from app.services.legal_analyst import PROMPT_ANALISTA

        secoes = [l for l in PROMPT_ANALISTA.split("\n") if l.startswith("## ")]
        assert secoes[0] == "## Resumo"

    def test_manda_descrever_o_entendimento_quando_o_numero_e_incerto(self):
        """
        A trava que torna a seção de jurisprudência utilizável.

        Pedir súmula e tema a um modelo é convite para número inventado, e um
        número inventado num parecer não fica no parecer: vai para a petição.
        Descrever o entendimento sem o número é informação; o número errado é
        armadilha.
        """
        from app.services.legal_analyst import PROMPT_ANALISTA

        assert "(confirmar referência)" in PROMPT_ANALISTA
        assert "Citação inventada" in PROMPT_ANALISTA

    def test_pede_as_teses_todas_e_a_contraria(self):
        """O que separa o parecer fundo do raso: não parar na primeira tese."""
        from app.services.legal_analyst import PROMPT_ANALISTA

        assert "**todas** as teses" in PROMPT_ANALISTA
        assert "tese contrária" in PROMPT_ANALISTA

    def test_o_parecer_cabe_no_orcamento_de_saida(self):
        """
        Com 1500 tokens o parecer novo era cortado no meio.

        Medido contra a API real: 5.5k tokens de saída, dos quais ~3.4k de
        raciocínio. Ver `folga_de_raciocinio` no cliente do Gemini — o
        orçamento é compartilhado entre pensar e escrever.
        """
        assert LegalAnalyst.MAX_TOKENS >= 4000



    def test_proibe_inventar_ato_processual(self):
        """
        Trava vinda de um erro real do modelo.

        No primeiro parecer gerado de verdade, o texto afirmava que "o cliente
        ajuizou a pretensão cerca de 2 meses após o desligamento" — o cliente
        só havia procurado o escritório. Um advogado lendo rápido age sobre um
        processo que não existe.
        """
        from app.services.legal_analyst import PROMPT_ANALISTA

        assert "não foi dito não aconteceu" in PROMPT_ANALISTA
        assert "Procurar o escritório não é ajuizar" in PROMPT_ANALISTA


class TestContextoCompleto:
    def test_le_a_conversa_inteira_e_nao_as_ultimas_cinco(self):
        """
        O atendimento usa 5 mensagens de contexto; a análise não pode.

        Uma triagem passa fácil de 5 turnos, e o relato do caso está no
        começo — analisar só o fim é analisar a coleta de contato.
        """
        assert LegalAnalyst.MAX_MENSAGENS >= 60
