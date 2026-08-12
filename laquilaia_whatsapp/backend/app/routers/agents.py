"""Agent management routes."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db_session
from app.models.schemas import AgentCreate, AgentUpdate, AgentResponse
from app.services.agent_service import agent_service
from app.utils.auth_middleware import get_current_user, require_admin
from app.utils.exceptions import NotFoundException, ValidationException
from app.utils.logger import logger
from typing import List

router = APIRouter(
    prefix="/api/v1/agents",
    tags=["agents"],
)


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate,
    user_id: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new agent."""
    try:
        return await agent_service.create_agent(user_id, agent_data, db)
    except ValidationException as e:
        logger.warning(f"⚠️ Validation error: {e.detail}")
        raise
    # Erros HTTP deliberados (404, 400, 403...) precisam subir intactos:
    # o catch-all abaixo os transformaria em 500.
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating agent",
        )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get agent by ID."""
    try:
        return await agent_service.get_agent(agent_id, user_id, db)
    except NotFoundException as e:
        logger.warning(f"⚠️ {e.detail}")
        raise
    # Erros HTTP deliberados (404, 400, 403...) precisam subir intactos:
    # o catch-all abaixo os transformaria em 500.
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting agent",
        )


@router.get("", response_model=List[AgentResponse])
async def list_agents(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    # Sem o alias, o parâmetro sombreia o módulo `status` do FastAPI e o
    # `status.HTTP_500_...` do except abaixo estoura AttributeError.
    status_filter: str = Query(None, alias="status"),
):
    """List all agents for the current user."""
    try:
        return await agent_service.list_agents(
            user_id, db, skip=skip, limit=limit, status=status_filter
        )
    # Erros HTTP deliberados (404, 400, 403...) precisam subir intactos:
    # o catch-all abaixo os transformaria em 500.
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error listing agents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listing agents",
        )


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    agent_data: AgentUpdate,
    user_id: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """Update agent by ID."""
    try:
        return await agent_service.update_agent(agent_id, user_id, agent_data, db)
    except NotFoundException as e:
        logger.warning(f"⚠️ {e.detail}")
        raise
    except ValidationException as e:
        logger.warning(f"⚠️ Validation error: {e.detail}")
        raise
    # Erros HTTP deliberados (404, 400, 403...) precisam subir intactos:
    # o catch-all abaixo os transformaria em 500.
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating agent",
        )


@router.delete("/{agent_id}", status_code=status.HTTP_200_OK)
async def delete_agent(
    agent_id: str,
    user_id: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """Delete agent by ID."""
    try:
        return await agent_service.delete_agent(agent_id, user_id, db)
    except NotFoundException as e:
        logger.warning(f"⚠️ {e.detail}")
        raise
    # Erros HTTP deliberados (404, 400, 403...) precisam subir intactos:
    # o catch-all abaixo os transformaria em 500.
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting agent",
        )


@router.post("/{agent_id}/variables", status_code=status.HTTP_201_CREATED)
async def add_agent_variable(
    agent_id: str,
    variable_data: dict,
    user_id: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """Add a variable to an agent."""
    try:
        return await agent_service.add_variable(agent_id, user_id, variable_data, db)
    except NotFoundException as e:
        logger.warning(f"⚠️ {e.detail}")
        raise
    # Erros HTTP deliberados (404, 400, 403...) precisam subir intactos:
    # o catch-all abaixo os transformaria em 500.
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error adding variable: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error adding variable",
        )


@router.get("/{agent_id}/variables", response_model=List[dict])
async def get_agent_variables(
    agent_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get all variables for an agent."""
    try:
        return await agent_service.get_variables(agent_id, user_id, db)
    except NotFoundException as e:
        logger.warning(f"⚠️ {e.detail}")
        raise
    # Erros HTTP deliberados (404, 400, 403...) precisam subir intactos:
    # o catch-all abaixo os transformaria em 500.
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting variables: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting variables",
        )
