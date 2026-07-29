"""Auth API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, EmailStr

from core.database import get_db
from core.exceptions import AuthenticationError, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from modules.auth.infrastructure.repositories import SQLAlchemyUserRepository, SQLAlchemySessionRepository
from modules.auth.application.use_cases import (
    RegisterUseCase, LoginUseCase, LogoutUseCase, GetCurrentUserUseCase,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# ── DTOs ────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str = ""

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    token: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    avatar_url: str | None = None
    is_active: bool


# ── Routes ──────────────────────────────────────────────────────────────────

@router.post("/register", response_model=AuthResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    user_repo = SQLAlchemyUserRepository(db)
    session_repo = SQLAlchemySessionRepository(db)
    use_case = RegisterUseCase(user_repo)
    user = await use_case.execute(body.email, body.password, body.full_name)

    login_uc = LoginUseCase(user_repo, session_repo)
    _, session = await login_uc.execute(body.email, body.password)

    return AuthResponse(
        user_id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        token=session.token,
    )


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user_repo = SQLAlchemyUserRepository(db)
    session_repo = SQLAlchemySessionRepository(db)
    use_case = LoginUseCase(user_repo, session_repo)
    user, session = await use_case.execute(body.email, body.password)

    return AuthResponse(
        user_id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        token=session.token,
    )


@router.post("/logout")
async def logout(authorization: str = Header(""), db: AsyncSession = Depends(get_db)):
    token = authorization.replace("Bearer ", "")
    session_repo = SQLAlchemySessionRepository(db)
    use_case = LogoutUseCase(session_repo)
    await use_case.execute(token)
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def get_me(authorization: str = Header(""), db: AsyncSession = Depends(get_db)):
    token = authorization.replace("Bearer ", "")
    user_repo = SQLAlchemyUserRepository(db)
    session_repo = SQLAlchemySessionRepository(db)
    use_case = GetCurrentUserUseCase(user_repo, session_repo)
    user = await use_case.execute(token)
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
    )
