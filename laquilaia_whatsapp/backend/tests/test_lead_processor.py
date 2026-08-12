"""Tests for lead processor."""

import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime
from app.services.lead_processor import lead_processor
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
            nome="Lead Qualificado",
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
                            lead_processor, "_gerar_analise"
                        ) as mock_analise:
                            # O parecer é acessório e tem teste próprio; aqui
                            # ele só não pode atrapalhar o fluxo principal.
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
        """Test mapping for novo status."""
        assert "Novo" in lead_processor.COLUMN_MAPPING["novo"]

    def test_column_mapping_qualificado(self):
        """Test mapping for qualificado status."""
        assert "Qualificado" in lead_processor.COLUMN_MAPPING["qualificado"]

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
