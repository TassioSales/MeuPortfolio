from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from loguru import logger

from config import settings
from models.database import get_db, Usuario


bearer_scheme = HTTPBearer()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def _usuario_to_dict(u: Usuario) -> dict:
    return {
        "id": str(u.id),
        "email": u.email,
        "nome": u.nome,
        "foto_url": u.foto_url,
        "role": u.role.value if u.role else "usuario",
        "idioma_preferido": u.idioma_preferido,
        "qualidade_padrao": u.qualidade_padrao,
        "legendas_padrao": u.legendas_padrao,
        "criado_em": u.criado_em,
        "password_hash": u.password_hash,
    }


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> dict:
    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Token de acesso inválido")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token sem identificador")

    try:
        import uuid as _uuid
        u = db.query(Usuario).filter(Usuario.id == _uuid.UUID(user_id)).first()
        if not u:
            raise HTTPException(status_code=401, detail="Usuário não encontrado")
        return _usuario_to_dict(u)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_current_user error: {e}")
        raise HTTPException(status_code=401, detail="Usuário não encontrado")


async def get_current_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito a administradores")
    return current_user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db),
) -> Optional[dict]:
    if not credentials:
        return None
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None
