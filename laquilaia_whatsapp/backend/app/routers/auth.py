"""Authentication routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db_session
from app.db.models import User
from app.models.schemas import UserCreate, UserLogin, UserResponse, TokenResponse
from app.services.auth_service import auth_service
from app.utils.auth_middleware import get_current_user
from app.utils.exceptions import UserAlreadyExistsException, InvalidCredentialsException
from app.utils.logger import logger

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["auth"],
)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """Register a new user."""
    try:
        # Check if user already exists
        result = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        existing_user = result.scalars().first()

        if existing_user:
            logger.warning(f"⚠️ Registration attempt with existing email: {user_data.email}")
            raise UserAlreadyExistsException()

        # Create new user
        hashed_password = auth_service.hash_password(user_data.senha)

        new_user = User(
            email=user_data.email,
            nome=user_data.nome,
            senha_hash=hashed_password,
            status="ativo",
        )

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        logger.info(f"✅ New user registered: {user_data.email}")

        return UserResponse(
            id=new_user.id,
            email=new_user.email,
            nome=new_user.nome,
            status=new_user.status,
            data_criacao=new_user.data_criacao,
        )

    except UserAlreadyExistsException:
        raise
    except Exception as e:
        logger.error(f"❌ Registration error: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error during registration",
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db_session),
):
    """Login user and return access and refresh tokens."""
    try:
        # Find user by email
        result = await db.execute(
            select(User).where(User.email == credentials.email)
        )
        user = result.scalars().first()

        # Verify user exists and password is correct
        if not user or not auth_service.verify_password(credentials.senha, user.senha_hash):
            logger.warning(f"⚠️ Failed login attempt: {credentials.email}")
            raise InvalidCredentialsException()

        # Verify user is active
        if user.status != "ativo":
            logger.warning(f"⚠️ Login attempt by inactive user: {credentials.email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is not active",
            )

        # Create tokens
        access_token, refresh_token = auth_service.create_tokens(user.id)

        logger.info(f"✅ User logged in: {credentials.email}")

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        )

    except (InvalidCredentialsException, HTTPException):
        raise
    except Exception as e:
        logger.error(f"❌ Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error during login",
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_data: dict,
):
    """Refresh access token using a valid refresh token."""
    try:
        refresh_token = token_data.get("refresh_token")

        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token is required",
            )

        # Verify and decode refresh token
        new_access_token = auth_service.refresh_access_token(refresh_token)

        if not new_access_token:
            logger.warning("⚠️ Invalid refresh token attempt")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        logger.info("✅ Access token refreshed")

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error during token refresh",
        )


@router.get("/me", response_model=UserResponse)
async def get_me(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Return the profile of the user owning the current access token."""
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()

        if not user:
            logger.warning(f"⚠️ Token valid but user not found: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return UserResponse(
            id=user.id,
            email=user.email,
            nome=user.nome,
            status=user.status,
            data_criacao=user.data_criacao,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching current user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching current user",
        )


@router.post("/verify-token")
async def verify_token(
    token_data: dict,
):
    """Verify if a token is valid."""
    try:
        token = token_data.get("token")

        if not token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token is required",
            )

        user_id = auth_service.verify_token(token)

        if not user_id:
            return {
                "valid": False,
                "user_id": None,
                "message": "Token is invalid or expired",
            }

        return {
            "valid": True,
            "user_id": user_id,
            "message": "Token is valid",
        }

    except Exception as e:
        logger.error(f"❌ Token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error during token verification",
        )


# Import settings for token expiry
from app.config import settings
