"""Tests for lead processor."""

import asyncio
import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime
from app.services.lead_processor import _TAREFAS, lead_processor
from app.services.legal_analyst import legal_analyst
from sqlalchemy import select
from app.db.models import Lead, LeadDetails, LeadTimeline, KanbanCard, KanbanColumn
from sqlalchemy.ext.asyncio import AsyncSession


class TestLeadProcessorJSONExtraction:
    """Test JSON extraction from Claude responses."""

    def test_extract_json_from_markdown_code_block(self):
        """Test extracting JSON from ```json``` block."""
        response = """
        Aqui está a qualificação do cliente:

        ```json
        {
            "nome_cliente": "João Silva",
            "email": "joao@example.com",
            "score_qualificacao": 85,
            "status_proposto": "qualificado"
        }
        ```

        O cliente parece ser qualificado.
        """

        data = lead_processor._extract_json(response)

        assert data is not None
        assert data["nome_cliente"] == "João Silva"
        assert data["score_qualificacao"] == 85

    def test_extract_json_bare_object(self):
        """Test extracting bare JSON object without code block."""
        response = """Resultado: {"nome_cliente": "Maria", "score_qualificacao": 75}"""

        data = lead_processor._extract_json(response)

        assert data is not None
        assert data["nome_cliente"] == "Maria"

    def test_extract_json_not_found(self):
        """Test when no JSON in response."""
        response = "O cliente não forneceu informações suficientes para qualificação."

        data = lead_processor._extract_json(response)

        assert data is None

    def test_extract_json_invalid(self):
        """Test extracting invalid JSON."""
        response = """```json
        {
            "nome_cliente": "João",
            "score": 85,  # Invalid JSON (comments)
        }
        ```"""

        data = lead_processor._extract_json(response)

        assert data is None


class TestLeadProcessorSchemaValidation:
    """Test qualification data schema validation."""

    def test_validate_valid_schema(self):
        """Test validation of valid schema."""
        data = {
            "nome_cliente": "João",
            "score_qualificacao": 80,
            "status_proposto": "qualificado",
        }

        result = lead_processor._validate_schema(data)

        assert result is True

    def test_validate_missing_nome_cliente(self):
        """Test validation fails without nome_cliente."""
        data = {
            "score_qualificacao": 80,
            "status_proposto": "qualificado",
        }

        result = lead_processor._validate_schema(data)

        assert result is False

    def test_validate_missing_score(self):
        """Test validation fails without score."""
        data = {
            "nome_cliente": "João",
            "status_proposto": "qualificado",
        }

        result = lead_processor._validate_schema(data)

        assert result is False

    def test_validate_invalid_score_range(self):
        """Test validation fails with invalid score (>100)."""
        data = {
            "nome_cliente": "João",
            "score_qualificacao": 150,
            "status_proposto": "qualificado",
        }

        result = lead_processor._validate_schema(data)

        assert result is False

    def test_validate_invalid_status(self):
        """Test validation fails with invalid status."""
        data = {
            "nome_cliente": "João",
            "score_qualificacao": 80,
            "status_proposto": "invalido",
        }

        result = lead_processor._validate_schema(data)

        assert result is False

    def test_validate_with_defaults(self):
        """Test validation with default status."""
        data = {
            "nome_cliente": "João",
            "score_qualificacao": 80,
            # status_proposto defaults to em_qualificacao
        }

        result = lead_processor._validate_schema(data)

        assert result is True


class TestLeadProcessorLeadManagement:
    """Test lead creation and updates."""

    @pytest.mark.asyncio
    async def test_get_or_create_new_lead(self):
        """Test creating new lead."""
        db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        lead = await lead_processor._get_or_create_lead(
            "5561999887234",
            "conv-123",
            db
        )

        assert lead.phone_number == "5561999887234"
        assert lead.conversation_id == "conv-123"
        assert lead.status_funil == "novo"

    @pytest.mark.asyncio
    async def test_get_existing_lead(self):
        """Test retrieving existing lead."""
        existing_lead = Lead(
            id="lead-123",
            phone_number="5561999887234",
            conversation_id="conv-123",
        )

        db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = existing_lead
        db.execute = AsyncMock(return_value=mock_result)

        lead = await lead_processor._get_or_create_lead(
            "5561999887234",
            "conv-456",
            db
        )

        assert lead.id == "lead-123"
        assert lead.phone_number == "5561999887234"

    @pytest.mark.asyncio
    async def test_update_lead(self):
        """Test updating lead with qualification data."""
        lead = Lead(
            id="lead-123",
            phone_number="5561999887234",
            conversation_id="conv-123",
        )

        db = AsyncMock(spec=AsyncSession)

        qualification = {
            "nome_cliente": "João Silva",
            "email": "joao@example.com",
            "status_proposto": "qualificado",
            "score_qualificacao": 85,
        }

        await lead_processor._update_lead(lead, qualification, db)

        assert lead.nome == "João Silva"
        assert lead.email == "joao@example.com"
        assert lead.status_funil == "qualificado"

    @pytest.mark.asyncio
    async def test_update_lead_details(self):
        """
        Cria o LeadDetails buscando por consulta, não pelo relacionamento.

        O acesso a `lead.lead_details` estourava
        `greenlet_spawn has not been called` no runtime async — e este teste
        não pegava porque o mock respondia ao atributo sem tocar no banco. O
        `result.scalars()` precisa ser `MagicMock`: no SQLAlchemy real ele é
        síncrono, e com `AsyncMock` vira corrotina.
        """
        lead = Lead(
            id="lead-123",
            phone_number="5561999887234",
            conversation_id="conv-123",
        )

        db = AsyncMock(spec=AsyncSession)
        db.flush = AsyncMock()
        sem_detalhes = MagicMock()
        sem_detalhes.scalars.return_value.first.return_value = None
        db.execute = AsyncMock(return_value=sem_detalhes)

        qualification = {
            "nome_cliente": "João",
            "email": "joao@example.com",
            "score_qualificacao": 85,
            "inconsistencias": "Faltou email",
            "problemas_detectados": "Telefone com dúvida",
        }

        await lead_processor._update_lead_details(lead, qualification, db)

        db.execute.assert_awaited_once()
        assert db.add.called
        criado = db.add.call_args[0][0]
        assert criado.lead_id == "lead-123"
        assert criado.score_qualificacao == 85


class TestLeadProcessorTimeline:
    """Test lead timeline tracking."""

    @pytest.mark.asyncio
    async def test_add_timeline_entry(self):
        """Test adding timeline entry for status change."""
        lead = Lead(
            id="lead-123",
            phone_number="5561999887234",
            status_funil="novo",
        )

        db = AsyncMock(spec=AsyncSession)
        db.flush = AsyncMock()

        qualification = {
            "nome_cliente": "João",
            "status_proposto": "qualificado",
            "score_qualificacao": 85,
        }

        await lead_processor._add_timeline(lead, qualification, db, "agent-123")

        # Verify db.add was called with LeadTimeline
        assert db.add.called


class TestLeadProcessorKanban:
    """Test Kanban integration."""

    @pytest.mark.asyncio
    async def test_move_in_kanban_new_card(self):
        """Test moving lead to Kanban column."""
        lead = Lead(
            id="lead-123",
            phone_number="5561999887234",
            kanban_card=None,
        )

        column = KanbanColumn(
            id="col-123",
            agent_id="agent-123",
            nome="Viabilidade",
            ordem=1,
        )

        db = AsyncMock(spec=AsyncSession)

        # Mock column query
        col_result = MagicMock()
        col_result.scalars.return_value.first.return_value = column

        # Mock cards query
        cards_result = MagicMock()
        cards_result.scalars.return_value.all.return_value = []

        async def mock_execute(query):
            # `str(query)` é o SQL renderizado, então o que aparece é o nome da
            # tabela ("kanban_columns"), não o da classe ("KanbanColumn").
            sql = str(query)
            if "kanban_columns" in sql:
                return col_result
            elif "kanban_cards" in sql:
                return cards_result
            return MagicMock()

        db.execute = mock_execute
        db.flush = AsyncMock()

        await lead_processor._move_in_kanban(
            lead, "agent-123", "qualificado", db
        )

        assert db.add.called


class TestLeadProcessorFullFlow:
    """Test complete lead processing flow."""

    @pytest.mark.asyncio
    async def test_process_response_with_qualification(self):
        """Test full processing of Claude response with qualification."""
        response = """
        O cliente João Silva é altamente qualificado.

        ```json
        {
            "nome_cliente": "João Silva",
            "email": "joao@example.com",
            "score_qualificacao": 90,
            "status_proposto": "qualificado",
            "inconsistencias": "Nenhuma",
            "problemas_detectados": "Nenhum",
            "recomendacoes": "Contatar imediatamente"
        }
        ```
        """

        db = AsyncMock(spec=AsyncSession)
        db.commit = AsyncMock()

        with patch.object(lead_processor, "_get_or_create_lead") as mock_get:
            with patch.object(lead_processor, "_update_lead") as mock_update:
                with patch.object(lead_processor, "_update_lead_details") as mock_details:
                    with patch.object(lead_processor, "_add_timeline") as mock_timeline:
                        with patch.object(
                            lead_processor, "_move_in_kanban"
                        ) as mock_kanban, patch.object(
                            lead_processor, "_agendar_analise"
                        ) as mock_analise:
                            # O parecer é acessório e tem teste próprio; aqui
                            # ele só não pode atrapalhar o fluxo principal.
                            #
                            # É `_agendar_analise` que se troca, e não
                            # `_gerar_analise`: o agendamento larga uma tarefa
                            # com sessão própria, e uma tarefa que ninguém
                            # espera ainda está com a transação aberta quando o
                            # teardown roda `TRUNCATE` — que fica esperando por
                            # ela. O sintoma é a suíte inteira travar.
                            lead = Lead(
                                id="lead-123",
                                phone_number="5561999887234",
                            )
                            mock_get.return_value = lead

                            result = await lead_processor.process_response(
                                response,
                                "5561999887234",
                                "conv-123",
                                "agent-123",
                                db
                            )

                            assert result["success"] is True
                            assert result["lead_id"] == "lead-123"
                            assert mock_get.called
                            assert mock_update.called
                            assert mock_details.called
                            assert mock_timeline.called
                            assert mock_kanban.called

    @pytest.mark.asyncio
    async def test_process_response_without_qualification(self):
        """Test processing response without qualification data."""
        response = "O cliente foi educado mas não deixou informações de contato."

        db = AsyncMock(spec=AsyncSession)

        result = await lead_processor.process_response(
            response,
            "5561999887234",
            "conv-123",
            "agent-123",
            db
        )

        assert result["success"] is False
        assert result["reason"] == "no_qualification_data"

    @pytest.mark.asyncio
    async def test_process_response_invalid_schema(self):
        """Test processing response with invalid schema."""
        response = """
        ```json
        {
            "nome": "João",
            "score": 150
        }
        ```
        """

        db = AsyncMock(spec=AsyncSession)

        result = await lead_processor.process_response(
            response,
            "5561999887234",
            "conv-123",
            "agent-123",
            db
        )

        assert result["success"] is False
        assert result["reason"] == "invalid_schema"


class TestLeadProcessorStatusMapping:
    """Test status to Kanban column mapping."""

    def test_column_mapping_novo(self):
        """Lead que acabou de chegar cai no primeiro contato."""
        assert lead_processor.COLUMN_MAPPING["novo"] == "Closer"

    def test_column_mapping_qualificado(self):
        """Qualificado pela IA quer dizer: alguém precisa medir a viabilidade."""
        assert lead_processor.COLUMN_MAPPING["qualificado"] == "Viabilidade"

    def test_nao_qualificado_vai_para_o_arquivo(self):
        """
        Estava fora do mapa, e o `.get(status, ...)` mandava para a coluna de
        trabalho tudo que a triagem tinha recusado por não ser da área. A
        coluna que o escritório abre todo dia enchia de caso já descartado.
        """
        assert lead_processor.COLUMN_MAPPING["nao_qualificado"] == "Arquivado"

    def test_com_duvidas_volta_para_o_primeiro_contato(self):
        """
        A IA não conseguiu decidir. Quem decide então é gente — e gente decide
        no primeiro contato, não no meio da entrevista.
        """
        assert lead_processor.COLUMN_MAPPING["com_duvidas"] == "Closer"

    def test_todo_veredito_da_ia_tem_coluna(self):
        """
        Os três vereditos que o prompt pode devolver, mais o default do
        processador. Um deles faltando volta a cair no `.get(..., "Entrevista")`
        — que é silencioso, e foi assim que `nao_qualificado` passou meses
        indo para a coluna errada.
        """
        for veredito in ("qualificado", "nao_qualificado", "com_duvidas", "em_qualificacao"):
            assert veredito in lead_processor.COLUMN_MAPPING, veredito

    def test_column_mapping_all_statuses(self):
        """Test all status mappings exist."""
        expected_statuses = [
            "novo", "em_qualificacao", "qualificado", "agendado", "arquivado"
        ]

        for status in expected_statuses:
            assert status in lead_processor.COLUMN_MAPPING


class TestTextoParaOCliente:
    """
    O bloco de qualificação não pode chegar ao cliente.

    O prompt documentado manda o modelo anexar um JSON com nome, e-mail,
    score e objeções detectadas — e esse texto era enviado inteiro pelo
    WhatsApp. O cliente recebia o próprio dossiê, com a nota que a empresa
    deu a ele.
    """

    def test_remove_o_bloco_json(self):
        resposta = (
            "Perfeito, Roberto! Consigo te ajudar.\n\n"
            "```json\n"
            '{"nome_cliente": "Roberto", "score_qualificacao": 95,\n'
            ' "problemas_detectados": "Cliente ansioso, pode pressionar preço"}\n'
            "```"
        )

        limpo = lead_processor.texto_para_o_cliente(resposta)

        assert "Perfeito, Roberto!" in limpo
        assert "score_qualificacao" not in limpo
        assert "pode pressionar preço" not in limpo
        assert "```" not in limpo

    def test_resposta_sem_bloco_fica_intacta(self):
        resposta = "Bom dia! Como posso ajudar?"
        assert lead_processor.texto_para_o_cliente(resposta) == resposta

    def test_json_solto_na_frase_nao_e_recortado(self):
        """
        Só o bloco cercado sai.

        Recortar por chaves soltas comeria conteúdo legítimo — uma resposta
        que cite um exemplo de configuração, por exemplo.
        """
        resposta = 'Use o formato {"chave": "valor"} no arquivo de config.'
        assert lead_processor.texto_para_o_cliente(resposta) == resposta

    def test_o_json_extraido_continua_disponivel(self):
        """A limpeza é só do texto: o processador ainda enxerga os dados."""
        resposta = (
            "Ótimo!\n```json\n"
            '{"nome_cliente": "Ana", "score_qualificacao": 70}\n```'
        )

        assert lead_processor._extract_json(resposta)["nome_cliente"] == "Ana"
        assert "Ana" not in lead_processor.texto_para_o_cliente(resposta)


class TestParecerEmSegundoPlano:
    """
    O parecer sai da requisição que o pediu.

    Ele leva ~2 minutos no Opus 5. Rodando dentro do webhook, a Evolution
    ficava esses dois minutos esperando o `200` — e webhook que demora é
    webhook que ela reentrega por timeout, o que significa responder duas vezes
    ao mesmo cliente e qualificar o mesmo lead de novo.
    """

    RESPOSTA = """Registrado.

```json
{
    "nome_cliente": "Marcos Andrade",
    "email": "marcos@example.com",
    "score_qualificacao": 90,
    "status_proposto": "qualificado",
    "inconsistencias": "",
    "problemas_detectados": "",
    "recomendacoes": "Ligar hoje"
}
```
"""

    async def _cenario(self, db, sufixo: str):
        """Dono, agente e conversa de verdade — a tarefa abre sessão própria."""
        from app.db.models import Agent, Conversation, User
        from app.services.kanban_defaults import criar_colunas_padrao

        db.add(
            User(
                id=f"parecer-user-{sufixo}",
                email=f"parecer-{sufixo}@example.com",
                nome="Dono",
                senha_hash="x",
                status="ativo",
            )
        )
        await db.flush()
        db.add(
            Agent(
                id=f"parecer-agent-{sufixo}",
                user_id=f"parecer-user-{sufixo}",
                nome="Triagem",
                system_prompt="x",
                temperatura=0.7,
                max_tokens=1024,
                status="ativo",
            )
        )
        conversa = Conversation(
            id=f"parecer-conv-{sufixo}",
            agent_id=f"parecer-agent-{sufixo}",
            phone_number=f"55619000{sufixo}",
            status="ativa",
        )
        db.add(conversa)
        await db.commit()
        await criar_colunas_padrao(f"parecer-agent-{sufixo}", db)
        await db.commit()
        return conversa

    @pytest.mark.asyncio
    async def test_a_requisicao_nao_espera_o_parecer(self):
        import time

        from app.db.database import AsyncSessionLocal

        DEMORA = 0.6

        async def parecer_lento(*_a, **_kw):
            await asyncio.sleep(DEMORA)
            return "## Resumo\nx\n\n## Ficha\nÁrea: trabalhista\nTitular: o próprio contato\n"

        async with AsyncSessionLocal() as db:
            conversa = await self._cenario(db, "01")

            with patch.object(legal_analyst, "analisar", side_effect=parecer_lento):
                inicio = time.monotonic()
                resultado = await lead_processor.process_response(
                    self.RESPOSTA,
                    conversa.phone_number,
                    conversa.id,
                    conversa.agent_id,
                    db,
                )
                decorrido = time.monotonic() - inicio

                assert resultado["success"] is True
                assert decorrido < DEMORA / 2, (
                    f"a qualificação levou {decorrido:.2f}s, perto dos "
                    f"{DEMORA:.2f}s do parecer: ele ainda está na requisição"
                )

                # E o parecer chega depois, sozinho.
                await asyncio.gather(*_TAREFAS)

        async with AsyncSessionLocal() as outra:
            detalhe = (
                await outra.execute(
                    select(LeadDetails).join(
                        Lead, Lead.id == LeadDetails.lead_id
                    ).where(Lead.phone_number == conversa.phone_number)
                )
            ).scalars().first()
            assert detalhe is not None
            assert "## Ficha" in (detalhe.analise_preliminar or "")

    @pytest.mark.asyncio
    async def test_duas_qualificacoes_seguidas_nao_geram_dois_pareceres(self):
        """
        O modelo repete o bloco de qualificação na mensagem seguinte ao
        fechamento — foi o que aconteceu numa das triagens reais. A guarda no
        banco só vale depois que o parecer existe; enquanto ele está sendo
        escrito, ainda não existe.
        """
        from app.db.database import AsyncSessionLocal

        chamadas = 0

        async def parecer(*_a, **_kw):
            nonlocal chamadas
            chamadas += 1
            await asyncio.sleep(0.2)
            return "## Resumo\nx\n\n## Ficha\nÁrea: familia\nTitular: o próprio contato\n"

        async with AsyncSessionLocal() as db:
            conversa = await self._cenario(db, "02")

            with patch.object(legal_analyst, "analisar", side_effect=parecer):
                for _ in range(2):
                    await lead_processor.process_response(
                        self.RESPOSTA,
                        conversa.phone_number,
                        conversa.id,
                        conversa.agent_id,
                        db,
                    )

                await asyncio.gather(*_TAREFAS)

        assert chamadas == 1
