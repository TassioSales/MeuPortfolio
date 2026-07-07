from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from loguru import logger
import uuid

from models.database import get_db, Usuario, UserRoleEnum
from models.schemas import RegisterRequest, LoginRequest, TokenResponse, RefreshRequest, UsuarioOut
from models.auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_token, get_current_user,
)

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, db: Session = Depends(get_db)):
    try:
        if db.query(Usuario).filter(Usuario.email == body.email).first():
            raise HTTPException(status_code=409, detail="Email já cadastrado")

        user = Usuario(
            id=uuid.uuid4(),
            email=body.email,
            password_hash=hash_password(body.password),
            nome=body.nome,
            role=UserRoleEnum.usuario,
        )
        db.add(user)
        db.commit()

        token_data = {"sub": str(user.id), "email": user.email, "role": user.role.value}
        return TokenResponse(
            access_token=create_access_token(token_data),
            refresh_token=create_refresh_token(token_data),
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"register error: {e}")
        raise HTTPException(status_code=500, detail="Erro ao criar conta")


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: Session = Depends(get_db)):
    try:
        user = db.query(Usuario).filter(Usuario.email == body.email).first()
        if not user or not verify_password(body.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Email ou senha incorretos")

        token_data = {"sub": str(user.id), "email": user.email, "role": user.role.value}
        return TokenResponse(
            access_token=create_access_token(token_data),
            refresh_token=create_refresh_token(token_data),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"login error: {e}")
        raise HTTPException(status_code=500, detail="Erro ao fazer login")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Refresh token inválido")

    user_id = payload.get("sub")
    user = db.query(Usuario).filter(Usuario.id == uuid.UUID(user_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")

    token_data = {"sub": str(user.id), "email": user.email, "role": user.role.value}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.get("/me", response_model=UsuarioOut)
async def me(current_user: dict = Depends(get_current_user)):
    return UsuarioOut(**{k: v for k, v in current_user.items() if k != "password_hash"})
