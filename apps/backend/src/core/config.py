"""
JobPilot AI — Application Configuration

Uses pydantic-settings for type-safe configuration from environment variables.
All settings are validated at startup.
"""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET_KEY = "change-me-in-production"


class Settings(BaseSettings):
    # ── Application ──────────────────────────────────
    APP_NAME: str = "JobPilot AI"
    APP_ENV: str = "development"  # development, staging, production
    DEBUG: bool = True
    SECRET_KEY: str = DEFAULT_SECRET_KEY
    API_V1_PREFIX: str = "/api/v1"
    FRONTEND_URL: str = "http://localhost:3000"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    # ── Database ──────────────────────────────────────
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "jobpilot"
    POSTGRES_USER: str = "jobpilot"
    POSTGRES_PASSWORD: str = "jobpilot_secret"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # ── Redis ─────────────────────────────────────────
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://redis:6379/0"

    # ── LLM Providers ─────────────────────────────────
    OPENAI_API_KEY: str = ""
    NVIDIA_NIM_ENDPOINT: str = "https://integrate.api.nvidia.com/v1"
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    # Separate from the chat keys: embeddings are billed and rate-limited on
    # their own, and semantic search works locally when this is unset.
    EMBEDDING_API_KEY: str = ""
    # Hard ceiling for a single LLM call. Without it a slow provider keeps an
    # HTTP worker and a DB session busy indefinitely.
    LLM_TIMEOUT_SECONDS: float = 60.0
    # 0 keeps a single failed call bounded to LLM_TIMEOUT_SECONDS; this is a
    # synchronous HTTP request, so doubling the wait for a retry is worse UX
    # than just surfacing the error and letting the user try again.
    LLM_MAX_RETRIES: int = 0

    # ── Celery ────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/1"

    # ── Email ─────────────────────────────────────────
    EMAIL_PROVIDER: str = "resend"
    EMAIL_API_KEY: str = ""
    EMAIL_FROM: str = "noreply@jobpilot.ai"

    # ── Notifications ─────────────────────────────────
    DISCORD_WEBHOOK_URL: str = ""
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # ── Monitoring ────────────────────────────────────
    SENTRY_DSN: str = ""
    LOG_LEVEL: str = "INFO"

    # ── LinkedIn OAuth ────────────────────────────────
    LINKEDIN_CLIENT_ID: str = ""
    LINKEDIN_CLIENT_SECRET: str = ""
    LINKEDIN_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/linkedin/callback"

    # ── Rate limiting ────────────────────────────────
    RATE_LIMIT_ENABLED: bool = True
    # Windows are per client IP. Login is the password-guessing surface;
    # register is the account-enumeration surface.
    RATE_LIMIT_WINDOW_SECONDS: int = 300
    RATE_LIMIT_LOGIN_ATTEMPTS: int = 10
    RATE_LIMIT_REGISTER_ATTEMPTS: int = 5

    # ── Demo ─────────────────────────────────────────
    # Seeds a ready-to-explore account so the app can be demonstrated with no
    # API keys, no job-board access and no manual data entry.
    DEMO_MODE: bool = False
    DEMO_EMAIL: str = "demo@jobpilot.ai"
    DEMO_PASSWORD: str = "jobpilot-demo"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() in ("production", "prod")

    @model_validator(mode="after")
    def _reject_insecure_production(self) -> "Settings":
        """Refuse to boot a production instance with the shipped defaults.

        SECRET_KEY derives the Fernet key that encrypts every stored LLM API
        key. Left at its default, those keys are decryptable by anyone holding
        a copy of this repository.
        """
        if self.is_production:
            if self.SECRET_KEY == DEFAULT_SECRET_KEY or len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "SECRET_KEY must be set to a unique value of at least 32 characters "
                    "when APP_ENV=production. Generate one with: "
                    "python -c 'import secrets; print(secrets.token_urlsafe(48))'"
                )
            if self.DEBUG:
                raise ValueError("DEBUG must be false when APP_ENV=production")
            if self.DEMO_MODE:
                raise ValueError("DEMO_MODE must be false when APP_ENV=production")
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


settings = get_settings()
