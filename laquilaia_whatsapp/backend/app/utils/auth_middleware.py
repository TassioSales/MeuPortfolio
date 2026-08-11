"""Authentication middleware for JWT validation."""

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from app.services.auth_service import auth_service
from app.utils.logger import logger
from typing import Optional

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthCredentials = Depends(security),
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
    credentials: Optional[HTTPAuthCredentials] = Depends(security),
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
