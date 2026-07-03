from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db, get_read_db
from core.security import hash_password, verify_password, create_access_token, get_current_user
from models.user import User
from schemas.user import RegisterRequest, LoginRequest, TokenResponse, UserProfile
from services.roadmap_service import generate_and_save_roadmap

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        name=data.name,
        current_role=data.current_role,
        target_role=data.target_role,
        experience_years=data.experience_years,
        known_skills=data.known_skills,
    )
    db.add(user)
    await db.flush()
    user_id = user.id
    await db.commit()

    # Geração de roadmap em background — resposta imediata ao usuário
    background_tasks.add_task(
        generate_and_save_roadmap,
        user_id,
        data.current_role,
        data.target_role,
        data.experience_years,
        data.known_skills,
    )

    return TokenResponse(access_token=create_access_token(user_id))


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_read_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserProfile)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
