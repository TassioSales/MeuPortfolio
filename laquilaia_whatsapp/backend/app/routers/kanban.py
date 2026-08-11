"""Kanban routes for lead management."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.database import get_db_session
from app.db.models import Agent, KanbanColumn, KanbanCard, Lead, LeadDetails
from app.utils.logger import logger
from app.utils.exceptions import NotFoundException, ValidationException
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

router = APIRouter(
    prefix="/api/v1",
    tags=["kanban"],
)


# ========== PYDANTIC MODELS ==========

class LeadCardResponse(BaseModel):
    """Lead card for Kanban display."""
    id: str
    nome: str
    email: str | None
    phone_number: str
    score_qualificacao: int
    status_funil: str
    ordem: int

    class Config:
        from_attributes = True


class KanbanColumnResponse(BaseModel):
    """Kanban column with cards."""
    id: str
    nome: str
    ordem: int
    cor_hex: str
    cards: List[LeadCardResponse]

    class Config:
        from_attributes = True


class KanbanBoardResponse(BaseModel):
    """Complete Kanban board."""
    agent_id: str
    columns: List[KanbanColumnResponse]

    class Config:
        from_attributes = True


class MoveCardRequest(BaseModel):
    """Request to move card between columns."""
    lead_id: str = Field(..., description="Lead ID to move")
    target_column_id: str = Field(..., description="Target column ID")
    new_order: int = Field(default=0, description="New position in column")


class UpdateCardOrderRequest(BaseModel):
    """Request to update card order within column."""
    card_id: str = Field(..., description="Card ID")
    new_order: int = Field(..., description="New position")


# ========== ENDPOINTS ==========

@router.get("/agents/{agent_id}/kanban", response_model=KanbanBoardResponse)
async def get_kanban_board(
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get complete Kanban board for an agent.

    Returns all columns and their cards (leads) organized by column.

    Args:
        agent_id: Agent ID
        db: Database session

    Returns:
        KanbanBoardResponse with columns and cards
    """
    try:
        # Verify agent exists
        result = await db.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = result.scalars().first()

        if not agent:
            logger.warning(f"⚠️ Agent not found: {agent_id}")
            raise NotFoundException("Agent")

        # Get all columns for agent
        result = await db.execute(
            select(KanbanColumn)
            .where(KanbanColumn.agent_id == agent_id)
            .order_by(KanbanColumn.ordem)
        )
        columns = result.scalars().all()

        # Build response with cards for each column
        columns_data = []
        for column in columns:
            # Get cards for this column
            result = await db.execute(
                select(KanbanCard)
                .where(KanbanCard.column_id == column.id)
                .order_by(KanbanCard.ordem)
            )
            cards_in_column = result.scalars().all()

            # Build card data with lead info
            cards_data = []
            for card in cards_in_column:
                # Get lead and details
                lead_result = await db.execute(
                    select(Lead).where(Lead.id == card.lead_id)
                )
                lead = lead_result.scalars().first()

                if lead:
                    details_result = await db.execute(
                        select(LeadDetails).where(LeadDetails.lead_id == lead.id)
                    )
                    details = details_result.scalars().first()

                    cards_data.append(LeadCardResponse(
                        id=lead.id,
                        nome=lead.nome or "Sem nome",
                        email=lead.email,
                        phone_number=lead.phone_number,
                        score_qualificacao=details.score_qualificacao if details else 0,
                        status_funil=lead.status_funil,
                        ordem=card.ordem,
                    ))

            columns_data.append(KanbanColumnResponse(
                id=column.id,
                nome=column.nome,
                ordem=column.ordem,
                cor_hex=column.cor_hex,
                cards=cards_data,
            ))

        logger.info(f"✅ Kanban board retrieved for agent {agent_id}")

        return KanbanBoardResponse(
            agent_id=agent_id,
            columns=columns_data,
        )

    except NotFoundException:
        raise
    # Erros HTTP deliberados (404, 400, 403...) precisam subir intactos:
    # o catch-all abaixo os transformaria em 500.
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting Kanban board: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve Kanban board",
        )


@router.post("/agents/{agent_id}/kanban/move")
async def move_lead_card(
    agent_id: str,
    move_request: MoveCardRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Move lead card to different column.

    Updates lead status and moves card in Kanban.

    Args:
        agent_id: Agent ID
        move_request: Move operation details
        db: Database session

    Returns:
        Updated card position
    """
    try:
        # Verify agent exists
        result = await db.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = result.scalars().first()

        if not agent:
            raise NotFoundException("Agent")

        # Get target column
        result = await db.execute(
            select(KanbanColumn).where(
                (KanbanColumn.id == move_request.target_column_id) &
                (KanbanColumn.agent_id == agent_id)
            )
        )
        target_column = result.scalars().first()

        if not target_column:
            raise NotFoundException("Column")

        # Get current card
        result = await db.execute(
            select(KanbanCard).where(KanbanCard.lead_id == move_request.lead_id)
        )
        card = result.scalars().first()

        if not card:
            raise NotFoundException("Card")

        # Get lead
        result = await db.execute(
            select(Lead).where(Lead.id == move_request.lead_id)
        )
        lead = result.scalars().first()

        if not lead:
            raise NotFoundException("Lead")

        # Store old status for timeline
        old_status = lead.status_funil

        # Update lead status based on column
        status_map = {
            "Novo Lead": "novo",
            "Em Qualificação": "em_qualificacao",
            "Lead Qualificado": "qualificado",
            "Agendado": "agendado",
            "Arquivado": "arquivado",
        }
        lead.status_funil = status_map.get(target_column.nome, lead.status_funil)
        lead.data_atualizacao = datetime.utcnow()

        # Update card
        card.column_id = target_column.id
        card.ordem = move_request.new_order
        card.data_movimentacao = datetime.utcnow()

        await db.commit()

        logger.info(
            f"✅ Lead {move_request.lead_id} moved: "
            f"{old_status} → {lead.status_funil}"
        )

        return {
            "success": True,
            "lead_id": move_request.lead_id,
            "column_id": target_column.id,
            "order": move_request.new_order,
            "status_anterior": old_status,
            "status_novo": lead.status_funil,
        }

    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.detail,
        )
    # Erros HTTP deliberados (404, 400, 403...) precisam subir intactos:
    # o catch-all abaixo os transformaria em 500.
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error moving card: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to move card",
        )


@router.get("/agents/{agent_id}/kanban/columns")
async def list_kanban_columns(
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get all Kanban columns for an agent.

    Args:
        agent_id: Agent ID
        db: Database session

    Returns:
        List of columns
    """
    try:
        # Verify agent exists
        result = await db.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = result.scalars().first()

        if not agent:
            raise NotFoundException("Agent")

        # Get columns
        result = await db.execute(
            select(KanbanColumn)
            .where(KanbanColumn.agent_id == agent_id)
            .order_by(KanbanColumn.ordem)
        )
        columns = result.scalars().all()

        return {
            "success": True,
            "agent_id": agent_id,
            "columns": [
                {
                    "id": col.id,
                    "nome": col.nome,
                    "ordem": col.ordem,
                    "cor_hex": col.cor_hex,
                }
                for col in columns
            ],
        }

    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    # Erros HTTP deliberados (404, 400, 403...) precisam subir intactos:
    # o catch-all abaixo os transformaria em 500.
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error listing columns: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list columns",
        )


@router.post("/agents/{agent_id}/kanban/columns/init")
async def initialize_kanban_columns(
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Initialize default Kanban columns for agent.

    Creates standard funnel columns if not already present.

    Args:
        agent_id: Agent ID
        db: Database session

    Returns:
        Created columns
    """
    try:
        # Verify agent exists
        result = await db.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = result.scalars().first()

        if not agent:
            raise NotFoundException("Agent")

        # Check if columns already exist
        result = await db.execute(
            select(func.count(KanbanColumn.id)).where(
                KanbanColumn.agent_id == agent_id
            )
        )
        count = result.scalar()

        if count > 0:
            logger.info(f"⏭️ Columns already exist for agent {agent_id}")
            return {
                "success": False,
                "message": "Columns already initialized",
            }

        # Create default columns
        default_columns = [
            ("Novo Lead", 1, "#ef4444"),
            ("Em Qualificação", 2, "#f97316"),
            ("Lead Qualificado", 3, "#eab308"),
            ("Agendado", 4, "#22c55e"),
            ("Arquivado", 5, "#6b7280"),
        ]

        created_columns = []
        for nome, ordem, cor in default_columns:
            column = KanbanColumn(
                agent_id=agent_id,
                nome=nome,
                ordem=ordem,
                cor_hex=cor,
            )
            db.add(column)
            created_columns.append((nome, cor))

        await db.commit()

        logger.info(f"✅ Kanban columns initialized for agent {agent_id}")

        return {
            "success": True,
            "agent_id": agent_id,
            "columns": [
                {"nome": nome, "cor": cor}
                for nome, cor in created_columns
            ],
        }

    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    # Erros HTTP deliberados (404, 400, 403...) precisam subir intactos:
    # o catch-all abaixo os transformaria em 500.
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error initializing columns: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize columns",
        )


@router.get("/agents/{agent_id}/kanban/stats")
async def get_kanban_stats(
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get Kanban statistics.

    Returns count of leads per column and quality metrics.

    Args:
        agent_id: Agent ID
        db: Database session

    Returns:
        Stats with lead counts per column
    """
    try:
        # Verify agent exists
        result = await db.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = result.scalars().first()

        if not agent:
            raise NotFoundException("Agent")

        # Get columns with card counts
        result = await db.execute(
            select(KanbanColumn)
            .where(KanbanColumn.agent_id == agent_id)
            .order_by(KanbanColumn.ordem)
        )
        columns = result.scalars().all()

        stats = {
            "agent_id": agent_id,
            "total_leads": 0,
            "columns": [],
            "avg_qualification_score": 0,
        }

        total_score = 0
        qualified_count = 0

        for column in columns:
            # Count cards
            result = await db.execute(
                select(func.count(KanbanCard.id)).where(
                    KanbanCard.column_id == column.id
                )
            )
            card_count = result.scalar()

            stats["total_leads"] += card_count
            stats["columns"].append({
                "nome": column.nome,
                "card_count": card_count,
            })

            # Get avg score for qualified leads
            if "Qualificado" in column.nome or "Agendado" in column.nome:
                result = await db.execute(
                    select(func.avg(LeadDetails.score_qualificacao))
                    .select_from(LeadDetails)
                    .join(Lead)
                    .join(KanbanCard)
                    .where(KanbanCard.column_id == column.id)
                )
                avg_score = result.scalar()
                if avg_score:
                    total_score += avg_score
                    qualified_count += 1

        if qualified_count > 0:
            stats["avg_qualification_score"] = total_score / qualified_count

        logger.info(f"✅ Kanban stats retrieved for agent {agent_id}")

        return stats

    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    # Erros HTTP deliberados (404, 400, 403...) precisam subir intactos:
    # o catch-all abaixo os transformaria em 500.
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get stats",
        )
