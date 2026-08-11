"""Custom exceptions for L'Aquila AI Backend."""

from fastapi import HTTPException, status


class LaquailaException(Exception):
    """Base exception for L'Aquila AI."""

    def __init__(self, message: str, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class AuthenticationException(HTTPException):
    """Raised when authentication fails."""

    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationException(HTTPException):
    """Raised when user is not authorized to perform action."""

    def __init__(self, detail: str = "Not authorized to perform this action"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class NotFoundException(HTTPException):
    """Raised when resource is not found."""

    def __init__(self, resource: str = "Resource"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} not found",
        )


class InvalidCredentialsException(AuthenticationException):
    """Raised when login credentials are invalid."""

    def __init__(self):
        super().__init__("Invalid email or password")


class UserAlreadyExistsException(HTTPException):
    """Raised when trying to register with existing email."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )


class LLMException(LaquailaException):
    """Raised when LLM API call fails."""

    def __init__(self, message: str = "LLM API error"):
        super().__init__(message, "LLM_ERROR")


class WhatsAppException(LaquailaException):
    """Raised when WhatsApp API call fails."""

    def __init__(self, message: str = "WhatsApp API error"):
        super().__init__(message, "WHATSAPP_ERROR")


class DatabaseException(LaquailaException):
    """Raised when database operation fails."""

    def __init__(self, message: str = "Database error"):
        super().__init__(message, "DATABASE_ERROR")


class ValidationException(HTTPException):
    """Raised when validation fails."""

    def __init__(self, detail: str = "Validation error"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )
