"""Auth API routes."""
from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, Header, Request, Response
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.exceptions import AuthenticationError, ConfigurationError
from core.models import SessionModel, UserModel
from core.rate_limit import enforce_rate_limit
from core.security import generate_token
from modules.auth.api.dependencies import extract_bearer_token, get_current_user
from modules.auth.application.use_cases import (
    SESSION_TTL,
    LoginUseCase,
    LogoutUseCase,
    RegisterUseCase,
)
from modules.auth.domain.entities import User
from modules.auth.infrastructure.repositories import SQLAlchemySessionRepository, SQLAlchemyUserRepository

router = APIRouter(prefix="/auth", tags=["auth"])

# LinkedIn's token endpoint is a third party; without a deadline a hung
# response holds an HTTP worker open indefinitely.
OAUTH_HTTP_TIMEOUT_SECONDS = 15.0


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
async def register(body: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    await enforce_rate_limit(
        request,
        "register",
        settings.RATE_LIMIT_REGISTER_ATTEMPTS,
        settings.RATE_LIMIT_WINDOW_SECONDS,
    )
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
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    await enforce_rate_limit(
        request, "login", settings.RATE_LIMIT_LOGIN_ATTEMPTS, settings.RATE_LIMIT_WINDOW_SECONDS
    )
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


@router.post("/demo", response_model=AuthResponse)
async def demo_login(request: Request, db: AsyncSession = Depends(get_db)):
    """Sign in to the shared demo account.

    Exists so the UI never has to embed the demo password in client-side code,
    and so the whole flow is a no-op unless DEMO_MODE is explicitly enabled.
    """
    if not settings.DEMO_MODE:
        raise ConfigurationError("O modo demonstração não está habilitado nesta instância.")

    await enforce_rate_limit(
        request, "demo", settings.RATE_LIMIT_LOGIN_ATTEMPTS, settings.RATE_LIMIT_WINDOW_SECONDS
    )

    # Seeding is idempotent, so a restarted or freshly migrated database still
    # serves a populated demo rather than a 401.
    from core.demo import seed_demo_data

    await seed_demo_data()

    user_repo = SQLAlchemyUserRepository(db)
    session_repo = SQLAlchemySessionRepository(db)
    user, session = await LoginUseCase(user_repo, session_repo).execute(
        settings.DEMO_EMAIL, settings.DEMO_PASSWORD
    )
    return AuthResponse(
        user_id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        token=session.token,
    )


@router.post("/logout")
async def logout(authorization: str = Header(""), db: AsyncSession = Depends(get_db)):
    use_case = LogoutUseCase(SQLAlchemySessionRepository(db))
    await use_case.execute(extract_bearer_token(authorization))
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
    )


# ── LinkedIn OAuth ──────────────────────────────────────────────────────────

# state -> (redirect_url, issued_at). In-memory: fine for a single instance,
# move to Redis when running more than one backend replica.
OAUTH_STATE_TTL = timedelta(minutes=10)
MAX_PENDING_STATES = 1000
LINKEDIN_STATE_CACHE: dict[str, tuple[str, datetime]] = {}


def _purge_expired_states(now: datetime) -> None:
    """Drop expired states so the cache cannot grow without bound."""
    for key in [k for k, (_, issued) in LINKEDIN_STATE_CACHE.items() if now - issued > OAUTH_STATE_TTL]:
        LINKEDIN_STATE_CACHE.pop(key, None)


@router.get("/linkedin/login")
async def linkedin_login(request: Request):
    """Redirect user to LinkedIn OAuth authorization page."""
    if not settings.LINKEDIN_CLIENT_ID or not settings.LINKEDIN_CLIENT_SECRET:
        raise ConfigurationError(
            "LinkedIn OAuth is not configured. Set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET."
        )

    now = datetime.now(UTC)
    _purge_expired_states(now)
    if len(LINKEDIN_STATE_CACHE) >= MAX_PENDING_STATES:
        raise AuthenticationError("Too many pending OAuth flows. Try again shortly.")

    state = secrets.token_urlsafe(32)
    LINKEDIN_STATE_CACHE[state] = (str(request.query_params.get("redirect", "/")), now)

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
async def linkedin_callback(
    request: Request,
    code: str = "",
    state: str = "",
    error: str = "",
    db: AsyncSession = Depends(get_db),
):
    """Handle LinkedIn OAuth callback — exchange code for token, create/login user."""
    await enforce_rate_limit(
        request, "oauth", settings.RATE_LIMIT_LOGIN_ATTEMPTS, settings.RATE_LIMIT_WINDOW_SECONDS
    )
    if error:
        raise AuthenticationError(f"LinkedIn OAuth error: {error}")

    now = datetime.now(UTC)
    _purge_expired_states(now)
    entry = LINKEDIN_STATE_CACHE.pop(state, None)  # one-time use
    if entry is None:
        raise AuthenticationError("Invalid or expired OAuth state. Try again.")
    if not code:
        raise AuthenticationError("Missing OAuth authorization code")

    # 1. Exchange authorization code for access token
    async with httpx.AsyncClient(timeout=OAUTH_HTTP_TIMEOUT_SECONDS) as client:
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
    session_token = generate_token()
    session = SessionModel(
        id=str(uuid.uuid4()),
        user_id=user_model.id,
        token=session_token,
        expires_at=now + SESSION_TTL,
    )
    db.add(session)
    await db.flush()

    # 6. Redirect back to frontend with token
    redirect_url = f"{settings.FRONTEND_URL.rstrip('/')}?token={session_token}"
    return Response(status_code=302, headers={"Location": redirect_url})
