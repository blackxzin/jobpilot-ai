"""Auth API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request, Response
from pydantic import BaseModel, EmailStr

from core.database import get_db
from core.exceptions import AuthenticationError, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
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


# ── LinkedIn OAuth ──────────────────────────────────────────────────────────

import secrets
import httpx

LINKEDIN_STATE_CACHE: dict[str, str] = {}  # state -> redirect_url (in-memory, ok for single instance)


@router.get("/linkedin/login")
async def linkedin_login(request: Request):
    """Redirect user to LinkedIn OAuth authorization page."""
    state = secrets.token_urlsafe(32)
    # Store state temporarily (in production, use Redis)
    LINKEDIN_STATE_CACHE[state] = str(request.query_params.get("redirect", "/"))

    auth_url = (
        f"https://www.linkedin.com/oauth/v2/authorization?"
        f"response_type=code&"
        f"client_id={settings.LINKEDIN_CLIENT_ID}&"
        f"redirect_uri={settings.LINKEDIN_REDIRECT_URI}&"
        f"state={state}&"
        f"scope=openid%20profile%20email"
    )
    return {"auth_url": auth_url}


@router.get("/linkedin/callback")
async def linkedin_callback(code: str = "", state: str = "", error: str = "", db: AsyncSession = Depends(get_db)):
    """Handle LinkedIn OAuth callback — exchange code for token, create/login user."""
    if error:
        raise AuthenticationError(f"LinkedIn OAuth error: {error}")

    if state not in LINKEDIN_STATE_CACHE:
        raise AuthenticationError("Invalid OAuth state. Try again.")
    del LINKEDIN_STATE_CACHE[state]  # one-time use

    # 1. Exchange authorization code for access token
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": settings.LINKEDIN_CLIENT_ID,
                "client_secret": settings.LINKEDIN_CLIENT_SECRET,
                "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if not token_resp.is_success:
            raise AuthenticationError("Failed to exchange LinkedIn code for token")

        token_data = token_resp.json()
        access_token = token_data.get("access_token")

        # 2. Fetch user profile from LinkedIn
        userinfo_resp = await client.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if not userinfo_resp.is_success:
            raise AuthenticationError("Failed to fetch LinkedIn profile")

        profile = userinfo_resp.json()

    # 3. Extract profile data
    linkedin_id = profile.get("sub", "")
    email = profile.get("email", f"linkedin_{linkedin_id[:8]}@linkedin.jobpilot")
    name = profile.get("name", email.split("@")[0])
    picture = profile.get("picture", "")

    # 4. Find or create user
    from core.models import UserModel
    from sqlalchemy import select
    from datetime import datetime, UTC, timedelta
    import uuid

    result = await db.execute(select(UserModel).where(UserModel.email == email))
    user_model = result.scalar_one_or_none()

    if not user_model:
        # Create new user from LinkedIn data
        user_model = UserModel(
            id=str(uuid.uuid4()),
            email=email,
            hashed_password="",  # OAuth users have no password
            full_name=name,
            avatar_url=picture or None,
            is_active=True,
        )
        db.add(user_model)
        await db.flush()

    # 5. Create session
    from core.security import generate_token
    session_token = generate_token()
    from core.models import SessionModel

    session = SessionModel(
        id=str(uuid.uuid4()),
        user_id=user_model.id,
        token=session_token,
        expires_at=datetime.now(UTC) + timedelta(days=7),  # 7 days
    )
    db.add(session)
    await db.commit()

    # 6. Redirect back to frontend with token
    frontend_url = "http://localhost:3000"
    redirect_url = f"{frontend_url}?token={session_token}"
    return Response(status_code=302, headers={"Location": redirect_url})
