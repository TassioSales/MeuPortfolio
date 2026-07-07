from pydantic import BaseModel, EmailStr
from datetime import datetime


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    current_role: str
    target_role: str
    experience_years: int = 0
    known_skills: list[str] = []


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserProfile(BaseModel):
    id: int
    email: str
    name: str
    current_role: str
    target_role: str
    experience_years: int
    known_skills: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}
