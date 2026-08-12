"""Authentication middleware for JWT validation."""

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session
from app.db.models import User
from app.services.auth_service import auth_service
from app.utils.logger import logger
from typing import Optional

from sqlalchemy import select

security = HTTPBearer()



async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """
    Dependency to extract and verify JWT token from request headers.
    Returns the user_id if token is valid, otherwise raises HTTPException.
    """
    token = credentials.credentials

    if not token:
        logger.warning("⚠️ Request without token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = auth_service.verify_token(token)

    if not user_id:
        logger.warning("⚠️ Invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[str]:
    """
    Optional dependency to extract JWT token from request headers.
    Returns the user_id if token is valid, None if not provided or invalid.
    """
    if not credentials:
        return None

    token = credentials.credentials

    if not token:
        return None

    user_id = auth_service.verify_token(token)
    return user_id


async def require_admin(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> str:
    """
    Só o administrador passa.

    O papel é lido do banco a cada requisição, e não do token: um token
    emitido antes de o papel mudar continuaria valendo por 30 minutos, e
    rebaixar alguém precisa fazer efeito na hora.

    Responde **404, não 403**, seguindo o que já vale para agente de outro
    dono: dizer "existe, mas você não pode" entrega a existência da rota a
    quem não deveria enxergá-la.
    """
    resultado = await db.execute(select(User).where(User.id == user_id))
    usuario = resultado.scalars().first()

    if usuario is None or usuario.papel != "admin":
        logger.warning(f"⚠️ Acesso administrativo negado para {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )

    return user_id
