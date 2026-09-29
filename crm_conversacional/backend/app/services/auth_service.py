"""Authentication service for user management and JWT tokens."""

from datetime import datetime, timedelta
from typing import Optional, Tuple
from passlib.context import CryptContext
from jose import JWTError, jwt
from app.config import settings
from app.utils.exceptions import InvalidCredentialsException, UserAlreadyExistsException
from app.utils.logger import logger

# Password hashing context
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


class AuthService:
    """Service for handling authentication operations."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(
        user_id: str,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Create a JWT access token."""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.access_token_expire_minutes
            )

        to_encode = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access",
        }

        encoded_jwt = jwt.encode(
            to_encode,
            settings.secret_key,
            algorithm=settings.algorithm,
        )

        return encoded_jwt

    @staticmethod
    def create_refresh_token(user_id: str) -> str:
        """Create a JWT refresh token (7 days expiry)."""
        expire = datetime.utcnow() + timedelta(days=7)

        to_encode = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh",
        }

        encoded_jwt = jwt.encode(
            to_encode,
            settings.secret_key,
            algorithm=settings.algorithm,
        )

        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Optional[str]:
        """Verify and decode a JWT token. Returns user_id or None if invalid."""
        try:
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.algorithm],
            )
            user_id: str = payload.get("sub")

            if user_id is None:
                logger.warning("⚠️ Token missing 'sub' claim")
                return None

            return user_id

        except JWTError as e:
            logger.warning(f"⚠️ Invalid token: {e}")
            return None

    @staticmethod
    def create_tokens(user_id: str) -> Tuple[str, str]:
        """Create both access and refresh tokens."""
        access_token = AuthService.create_access_token(user_id)
        refresh_token = AuthService.create_refresh_token(user_id)
        return access_token, refresh_token

    @staticmethod
    def refresh_access_token(refresh_token: str) -> Optional[str]:
        """Create a new access token from a valid refresh token."""
        try:
            payload = jwt.decode(
                refresh_token,
                settings.secret_key,
                algorithms=[settings.algorithm],
            )

            # Verify it's a refresh token
            if payload.get("type") != "refresh":
                logger.warning("⚠️ Token is not a refresh token")
                return None

            user_id: str = payload.get("sub")

            if user_id is None:
                logger.warning("⚠️ Refresh token missing 'sub' claim")
                return None

            # Create new access token
            new_access_token = AuthService.create_access_token(user_id)
            return new_access_token

        except JWTError as e:
            logger.warning(f"⚠️ Invalid refresh token: {e}")
            return None


auth_service = AuthService()
