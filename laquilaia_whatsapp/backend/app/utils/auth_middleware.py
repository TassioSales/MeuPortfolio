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

# `auto_error=False` porque o erro é nosso, não do FastAPI.
#
# Com o padrão (`True`), requisição **sem** cabeçalho `Authorization` era
# recusada pelo próprio FastAPI com **403**. E 403 quer dizer "eu sei quem você
# é e você não pode"; o certo aqui é 401, "você não está autenticado".
#
# A diferença não era acadêmica: o cookie do access token dura 30 minutos e o
# browser o apaga ao expirar, então a partir daí as chamadas saíam sem
# cabeçalho nenhum. O cliente HTTP do front renova a sessão quando vê 401 — em
# 403 ele não tenta. O usuário tinha refresh token válido por sete dias no
# bolso e era deslogado meia hora depois de entrar, porque ninguém o usou.
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session),
) -> str:
    """
    Quem está falando, e se ainda pode falar.

    O token diz quem é; o **banco** diz se a conta continua valendo. Só o token
    não basta: ele vale 30 minutos, e quem foi desativado no minuto seguinte à
    emissão continuaria entrando durante meia hora. Para revogar acesso — o
    funcionário que saiu hoje, a conta comprometida — meia hora é uma
    eternidade.

    É a mesma razão pela qual `require_admin` lê o papel do banco: privilégio e
    permanência não podem viver num papel que já foi impresso.
    """
    token = credentials.credentials if credentials else None

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

    resultado = await db.execute(select(User).where(User.id == user_id))
    usuario = resultado.scalars().first()

    if usuario is None or usuario.status != "ativo":
        # 401 e não 403: a sessão deixou de valer, e o painel trata 401
        # tentando renovar — a renovação também vai falhar, e a pessoa cai no
        # login, que é onde ela deve cair.
        logger.warning(f"⚠️ Token de conta inativa ou removida: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Conta inativa",
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
