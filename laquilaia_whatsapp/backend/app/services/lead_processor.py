"""Lead processor for extracting qualifications from Claude responses."""

import json
import re
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Lead, LeadDetails, LeadTimeline, Conversation, KanbanCard, KanbanColumn, Agent
from app.utils.logger import logger
from app.services.caso_service import registrar_caso
from app.services.legal_analyst import legal_analyst
from app.utils.exceptions import ValidationException


class LeadProcessor:
    """Processes AI responses to extract lead qualification data."""

    # JSON schema expected from Claude for lead qualification
    QUALIFICATION_SCHEMA = {
        "nome_cliente": str,
        "email": str,
        "score_qualificacao": int,  # 0-100
        "inconsistencias": str,
        "problemas_detectados": str,
        "recomendacoes": str,
        "status_proposto": str,  # qualificado, nao_qualificado, com_duvidas
    }

    # Kanban column mapping
    COLUMN_MAPPING = {
        "novo": "Novo Lead",
        "em_qualificacao": "Em Qualificação",
        "qualificado": "Lead Qualificado",
        "agendado": "Agendado",
        "arquivado": "Arquivado",
    }

    async def process_response(
        self,
        response_text: str,
        phone_number: str,
        conversation_id: str,
        agent_id: str,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Process Claude response and extract lead data.

        Attempts to extract JSON from response for lead qualification.
        If found, creates/updates Lead and moves in Kanban.

        Args:
            response_text: Full Claude response text
            phone_number: Customer phone number
            conversation_id: Conversation ID
            agent_id: Agent ID
            db: Database session

        Returns:
            Dict with processing result {
                "success": bool,
                "lead_id": str (if qualified),
                "qualification_data": dict,
                "message": str
            }
        """
        try:
            # Try to extract JSON from response
            qualification_data = self._extract_json(response_text)

            if qualification_data is None:
                logger.debug(f"⏭️ No qualification data in response for {phone_number}")
                return {
                    "success": False,
                    "reason": "no_qualification_data",
                    "message": "Resposta não contém dados de qualificação",
                }

            # Validate JSON schema
            if not self._validate_schema(qualification_data):
                logger.warning(f"⚠️ Invalid qualification schema for {phone_number}")
                return {
                    "success": False,
                    "reason": "invalid_schema",
                    "message": "Dados de qualificação com formato inválido",
                }

            # Get or create Lead
            lead = await self._get_or_create_lead(
                phone_number, conversation_id, db
            )

            # Update Lead with qualifications
            await self._update_lead(lead, qualification_data, db)

            # Create/update LeadDetails
            await self._update_lead_details(lead, qualification_data, db)

            # O parecer para o escritório. Vem depois dos detalhes porque
            # grava no mesmo registro, e antes do commit para entrar na mesma
            # transação — um lead qualificado sem análise é aceitável, um
            # commit pela metade não.
            await self._gerar_analise(lead, conversation_id, agent_id, db)

            # Add to timeline
            await self._add_timeline(lead, qualification_data, db, agent_id)

            # Move in Kanban
            status_proposto = qualification_data.get("status_proposto", "em_qualificacao")
            await self._move_in_kanban(lead, agent_id, status_proposto, db)

            await db.commit()

            logger.info(
                f"✅ Lead processed: {phone_number} "
                f"(score: {qualification_data.get('score_qualificacao', 0)})"
            )

            return {
                "success": True,
                "lead_id": lead.id,
                "qualification_data": qualification_data,
                "message": "Lead qualificado com sucesso",
            }

        except Exception as e:
            logger.error(f"❌ Error processing lead: {e}")
            await db.rollback()
            raise ValidationException(f"Failed to process lead: {str(e)}")

    # O mesmo padrão usado para extrair, reaproveitado para limpar.
    BLOCO_JSON = re.compile(r"```json\s*[\s\S]*?\s*```", re.IGNORECASE)

    @classmethod
    def texto_para_o_cliente(cls, response_text: str) -> str:
        """
        A resposta sem o bloco de qualificação.

        O prompt documentado manda o modelo anexar um bloco ```json com nome,
        e-mail, score e recomendações internas — e esse texto era enviado
        inteiro ao WhatsApp. O cliente recebia o próprio dossiê, incluindo o
        score que a empresa deu a ele e as objeções detectadas.

        Só o bloco cercado é removido. JSON solto no meio da frase fica: pode
        ser conteúdo legítimo da conversa, e recortar por chaves soltas
        arriscaria comer a resposta.
        """
        return cls.BLOCO_JSON.sub("", response_text).strip()

    def _extract_json(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from Claude response.

        Looks for JSON block in response (```json...``` or bare JSON).

        Args:
            response_text: Claude response text

        Returns:
            Parsed JSON dict or None if not found
        """
        try:
            # Try markdown code block first
            json_match = re.search(
                r"```json\s*([\s\S]*?)\s*```",
                response_text,
                re.IGNORECASE
            )

            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find bare JSON object
                json_match = re.search(
                    r"\{[\s\S]*\}",
                    response_text
                )
                if json_match:
                    json_str = json_match.group(0)
                else:
                    return None

            # Parse JSON
            data = json.loads(json_str)
            return data

        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ Failed to parse JSON from response: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error extracting JSON: {e}")
            return None

    def _validate_schema(self, data: Dict[str, Any]) -> bool:
        """
        Validate qualification data against schema.

        Required fields:
        - nome_cliente: string
        - score_qualificacao: int (0-100)
        - status_proposto: string (qualificado, nao_qualificado, com_duvidas)

        Args:
            data: Qualification data dict

        Returns:
            True if valid, False otherwise
        """
        try:
            # Check required fields
            if "nome_cliente" not in data:
                logger.warning("Missing required field: nome_cliente")
                return False

            if "score_qualificacao" not in data:
                logger.warning("Missing required field: score_qualificacao")
                return False

            # Validate score range
            score = data.get("score_qualificacao")
            if not isinstance(score, (int, float)) or score < 0 or score > 100:
                logger.warning(f"Invalid score: {score}")
                return False

            # Validate status
            status = data.get("status_proposto", "em_qualificacao")
            # "em_qualificacao" é o default acima e precisa constar aqui, senão
            # todo payload que omite `status_proposto` seria rejeitado.
            valid_statuses = [
                "em_qualificacao",
                "qualificado",
                "nao_qualificado",
                "com_duvidas",
            ]
            if status not in valid_statuses:
                logger.warning(f"Invalid status: {status}")
                return False

            return True

        except Exception as e:
            logger.error(f"❌ Schema validation error: {e}")
            return False

    async def _get_or_create_lead(
        self,
        phone_number: str,
        conversation_id: str,
        db: AsyncSession,
    ) -> Lead:
        """Get existing lead or create new one."""
        result = await db.execute(
            select(Lead).where(Lead.phone_number == phone_number)
        )
        lead = result.scalars().first()

        if lead:
            logger.debug(f"📝 Using existing lead for {phone_number}")
            return lead

        logger.debug(f"🆕 Creating new lead for {phone_number}")
        lead = Lead(
            phone_number=phone_number,
            conversation_id=conversation_id,
            status_funil="novo",
        )
        db.add(lead)
        await db.flush()
        return lead

    async def _update_lead(
        self,
        lead: Lead,
        qualification_data: Dict[str, Any],
        db: AsyncSession,
    ) -> None:
        """Update lead with qualification info."""
        lead.nome = qualification_data.get("nome_cliente", lead.nome)
        lead.email = qualification_data.get("email", lead.email)

        status = qualification_data.get("status_proposto", "em_qualificacao")
        lead.status_funil = status

        lead.data_atualizacao = datetime.utcnow()

    async def _update_lead_details(
        self,
        lead: Lead,
        qualification_data: Dict[str, Any],
        db: AsyncSession,
    ) -> None:
        """Create or update LeadDetails."""
        # A busca é explícita porque `lead.lead_details` é relacionamento com
        # carga preguiçosa: no SQLAlchemy async, tocar um atributo que ainda
        # não veio do banco exige IO onde o greenlet não alcança, e o erro é
        # `greenlet_spawn has not been called`. Um lead recém-criado nunca tem
        # o relacionamento carregado, então este era o caminho garantido.
        resultado = await db.execute(
            select(LeadDetails).where(LeadDetails.lead_id == lead.id)
        )
        details = resultado.scalars().first()

        if details is None:
            details = LeadDetails(lead_id=lead.id)
            db.add(details)
            await db.flush()

        details.score_qualificacao = qualification_data.get("score_qualificacao", 0)
        details.inconsistencias = qualification_data.get("inconsistencias", "")
        details.problemas_detectados = qualification_data.get("problemas_detectados", "")
        details.dados_json = json.dumps(qualification_data)
        details.data_atualizacao = datetime.utcnow()

    async def _gerar_analise(
        self,
        lead,
        conversation_id: str,
        agent_id: str,
        db: AsyncSession,
    ) -> None:
        """
        Guarda o parecer preliminar, se houver.

        Silencioso quando não houver: o analista devolve `None` tanto com a
        função desligada quanto quando a chamada falha, e nenhum dos dois é
        motivo para reprovar a qualificação.
        """
        resultado = await db.execute(
            select(LeadDetails).where(LeadDetails.lead_id == lead.id)
        )
        details = resultado.scalars().first()
        if details is None:
            return

        # Um parecer por caso, não por mensagem.
        #
        # O modelo repete o bloco de qualificação em toda resposta depois de
        # fechar a triagem, e sem esta guarda cada "obrigado" do cliente
        # geraria um parecer novo — outra chamada paga, e o advogado abrindo o
        # lead para reler o mesmo texto. Refazer a análise de um caso já
        # analisado é decisão de quem atende, pelo painel.
        if details.analise_preliminar:
            logger.debug(f"⏭️ Lead {lead.id} já tem parecer; não vou refazer")
            return

        parecer = await legal_analyst.analisar(conversation_id, db)
        if not parecer:
            return

        details.analise_preliminar = parecer

        # O mesmo parecer arquiva o caso. A ficha diz de que área ele é e
        # quem é a parte — o contato pode estar trazendo assunto de terceiro.
        await registrar_caso(lead, parecer, details.score_qualificacao or 0, db)

    async def _add_timeline(
        self,
        lead: Lead,
        qualification_data: Dict[str, Any],
        db: AsyncSession,
        agent_id: str,
    ) -> None:
        """Add timeline entry for status change."""
        new_status = qualification_data.get("status_proposto", "em_qualificacao")

        # Get agent ID (in this case, it's the user who qualifies)
        # We'll use agent_id as reference to who triggered the qualification
        timeline = LeadTimeline(
            lead_id=lead.id,
            status_anterior=lead.status_funil,
            status_novo=new_status,
            motivo=f"Qualificação automática por Claude (score: {qualification_data.get('score_qualificacao')})",
            timestamp=datetime.utcnow(),
        )
        db.add(timeline)
        await db.flush()

    async def _move_in_kanban(
        self,
        lead: Lead,
        agent_id: str,
        status: str,
        db: AsyncSession,
    ) -> None:
        """Move lead card in Kanban based on qualification."""
        try:
            # Get agent's kanban columns
            result = await db.execute(
                select(KanbanColumn).where(
                    (KanbanColumn.agent_id == agent_id) &
                    (KanbanColumn.nome.like(f"%{self.COLUMN_MAPPING.get(status, 'Em Qualificação')}%"))
                )
            )
            column = result.scalars().first()

            if not column:
                logger.warning(f"⚠️ Kanban column not found for status {status}")
                return

            # Mesmo motivo de `_update_lead_details`: `lead.kanban_card` é
            # relacionamento preguiçoso e não pode ser tocado direto aqui.
            resultado = await db.execute(
                select(KanbanCard).where(KanbanCard.lead_id == lead.id)
            )
            card_atual = resultado.scalars().first()
            if card_atual is not None:
                await db.delete(card_atual)
                # O flush é necessário antes de inserir o novo: a tabela tem
                # unicidade por lead, e o DELETE só vai ao banco no commit.
                await db.flush()

            # Create new card in target column
            max_order = 0
            result = await db.execute(
                select(KanbanCard).where(KanbanCard.column_id == column.id)
            )
            cards = result.scalars().all()
            if cards:
                max_order = max(card.ordem for card in cards)

            card = KanbanCard(
                column_id=column.id,
                lead_id=lead.id,
                ordem=max_order + 1,
            )
            db.add(card)
            await db.flush()

            logger.info(f"✅ Moved lead {lead.phone_number} to column {column.nome}")

        except Exception as e:
            logger.warning(f"⚠️ Failed to move lead in Kanban: {e}")


lead_processor = LeadProcessor()
