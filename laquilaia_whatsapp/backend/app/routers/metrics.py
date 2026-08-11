"""Metrics routes for dashboard data endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db_session
from app.services.metrics_service import metrics_service
from app.utils.logger import logger
from app.utils.exceptions import NotFoundException, ValidationException
from pydantic import BaseModel, Field

router = APIRouter(
    prefix="/api/v1",
    tags=["metrics"],
)


# ========== PYDANTIC MODELS ==========

class PeriodStatsResponse(BaseModel):
    """Period statistics response."""
    agent_id: str
    periodo: str
    data_inicio: str
    data_fim: str
    total_atendimentos: int
    taxa_qualificacao: float
    tempo_medio_min: float
    leads_qualificados: int
    total_leads: int
    timestamp: str

    class Config:
        from_attributes = True


class QualificationRateResponse(BaseModel):
    """Qualification rate response."""
    taxa_qualificacao: float
    leads_qualificados: int
    total_leads: int
    periodo: str
    trend: float
    status: str
    timestamp: str

    class Config:
        from_attributes = True


class ResponseTimeMetricsResponse(BaseModel):
    """Response time metrics."""
    tempo_medio_seg: float
    p50_seg: float
    p95_seg: float
    min_seg: float
    max_seg: float
    total_trocas: int
    timestamp: str

    class Config:
        from_attributes = True


class LeadDistributionResponse(BaseModel):
    """Lead distribution by status."""
    novo: int
    em_qualificacao: int
    qualificado: int
    agendado: int
    arquivado: int
    total: int

    class Config:
        from_attributes = True


class KPIResponse(BaseModel):
    """KPI response with comparison."""
    periodo_atual: dict
    periodo_anterior: dict
    variacao_percent: dict
    status: str
    alertas: list
    timestamp: str

    class Config:
        from_attributes = True


# ========== ENDPOINTS ==========

@router.get("/agents/{agent_id}/metrics", response_model=dict)
async def get_metrics_summary(
    agent_id: str,
    period: str = Query("day", regex="^(day|week|month)$"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get metrics summary for an agent.

    Returns aggregated statistics for the specified period.

    Args:
        agent_id: Agent ID
        period: "day", "week", or "month"
        db: Database session

    Returns:
        Dict with total_atendimentos, taxa_qualificacao, tempo_medio_min, etc
    """
    try:
        stats = await metrics_service.calculate_period_stats(
            agent_id, db, period, use_cache=True
        )

        qual_rate = await metrics_service.get_qualification_rate(
            agent_id, db, period, use_cache=True
        )

        distribution = await metrics_service.get_lead_distribution(
            agent_id, db, use_cache=True
        )

        logger.info(f"✅ Metrics summary retrieved for {agent_id}")

        return {
            "agent_id": agent_id,
            "periodo": period,
            "atendimentos_totais": stats["total_atendimentos"],
            "taxa_qualificacao": qual_rate["taxa_qualificacao"],
            "tempo_medio_resposta_seg": stats["tempo_medio_min"] * 60,
            "leads_por_status": distribution,
            "timestamp": stats["timestamp"],
        }

    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    # Erros HTTP deliberados (404, 400, 403...) precisam subir intactos:
    # o catch-all abaixo os transformaria em 500.
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting metrics summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metrics",
        )


@router.get("/agents/{agent_id}/metrics/period", response_model=PeriodStatsResponse)
async def get_period_stats(
    agent_id: str,
    period: str = Query("day"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get detailed statistics for a period.

    Args:
        agent_id: Agent ID
        period: "day", "week", "month", or "custom"
        start_date: Start date (required for custom period, ISO 8601)
        end_date: End date (required for custom period, ISO 8601)
        db: Database session

    Returns:
        Detailed period statistics
    """
    try:
        stats = await metrics_service.calculate_period_stats(
            agent_id, db, period, start_date, end_date, use_cache=True
        )
        logger.info(f"✅ Period stats retrieved: {period}")
        return PeriodStatsResponse(**stats)

    except NotFoundException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    # Erros HTTP deliberados (404, 400, 403...) precisam subir intactos:
    # o catch-all abaixo os transformaria em 500.
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting period stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve period stats",
        )


@router.get("/agents/{agent_id}/metrics/qualification-rate", response_model=QualificationRateResponse)
async def get_qualification_metrics(
    agent_id: str,
    period: str = Query("day"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get qualification rate with trend analysis.

    Args:
        agent_id: Agent ID
        period: "day", "week", or "month"
        db: Database session

    Returns:
        Qualification rate with trend and status
    """
    try:
        data = await metrics_service.get_qualification_rate(
            agent_id, db, period, use_cache=True
        )
        logger.info(f"✅ Qualification rate retrieved: {data['taxa_qualificacao']}%")
        return QualificationRateResponse(**data)

    except NotFoundException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    # Erros HTTP deliberados (404, 400, 403...) precisam subir intactos:
    # o catch-all abaixo os transformaria em 500.
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting qualification metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve qualification metrics",
        )


@router.get("/agents/{agent_id}/metrics/response-time", response_model=ResponseTimeMetricsResponse)
async def get_response_time_metrics(
    agent_id: str,
    period: str = Query("day"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get average response time metrics.

    Calculates time between user and agent messages, excluding gaps > 30 minutes.

    Args:
        agent_id: Agent ID
        period: "day", "week", or "month"
        db: Database session

    Returns:
        Response time statistics with percentiles
    """
    try:
        data = await metrics_service.get_avg_response_time(
            agent_id, db, period, use_cache=True
        )
        logger.info(f"✅ Response time metrics retrieved: {data['tempo_medio_seg']}s avg")
        return ResponseTimeMetricsResponse(**data)

    except NotFoundException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    # Erros HTTP deliberados (404, 400, 403...) precisam subir intactos:
    # o catch-all abaixo os transformaria em 500.
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting response time: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve response time metrics",
        )


@router.get("/agents/{agent_id}/metrics/lead-distribution", response_model=LeadDistributionResponse)
async def get_lead_distribution(
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get current distribution of leads by funnel status.

    Args:
        agent_id: Agent ID
        db: Database session

    Returns:
        Counts for each status: novo, em_qualificacao, qualificado, agendado, arquivado
    """
    try:
        data = await metrics_service.get_lead_distribution(
            agent_id, db, use_cache=True
        )
        logger.info(f"✅ Lead distribution retrieved: {data['total']} total leads")
        return LeadDistributionResponse(**data)

    except NotFoundException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    # Erros HTTP deliberados (404, 400, 403...) precisam subir intactos:
    # o catch-all abaixo os transformaria em 500.
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting lead distribution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve lead distribution",
        )


@router.get("/agents/{agent_id}/metrics/kpis", response_model=KPIResponse)
async def get_kpis(
    agent_id: str,
    comparison: bool = Query(True),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get consolidated KPIs with comparison to previous period.

    Args:
        agent_id: Agent ID
        comparison: Whether to include comparison (default True)
        db: Database session

    Returns:
        KPIs with current/previous period data and variation percentages
    """
    try:
        data = await metrics_service.get_kpis(
            agent_id, db, use_cache=True
        )
        logger.info(f"✅ KPIs retrieved for {agent_id}")
        return KPIResponse(**data)

    except NotFoundException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    # Erros HTTP deliberados (404, 400, 403...) precisam subir intactos:
    # o catch-all abaixo os transformaria em 500.
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting KPIs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve KPIs",
        )
