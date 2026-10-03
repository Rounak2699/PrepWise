import os
from dataclasses import dataclass, field


def _list(name: str, default: str) -> list[str]:
    return [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]


@dataclass(frozen=True)
class Settings:
    app_env: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./placement.db"))
    jwt_secret: str = field(default_factory=lambda: os.getenv("JWT_SECRET", "dev-only-change-me"))
    jwt_expire_minutes: int = field(default_factory=lambda: int(os.getenv("JWT_EXPIRE_MINUTES", "1440")))
    cors_origins: list[str] = field(default_factory=lambda: _list("CORS_ORIGINS", "http://localhost:5173"))
    timezone: str = field(default_factory=lambda: os.getenv("APP_TIMEZONE", "Asia/Kolkata"))
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    ai_model: str = field(default_factory=lambda: os.getenv("AI_MODEL", "claude-sonnet-5"))
    ai_timeout_seconds: float = field(default_factory=lambda: float(os.getenv("AI_TIMEOUT_SECONDS", "15")))
    default_question_count: int = 12
    seconds_per_question: int = 75
    recent_window_days: int = 7
    submit_grace_seconds: int = 5


settings = Settings()

if settings.app_env == "production" and settings.jwt_secret == "dev-only-change-me":
    raise RuntimeError("JWT_SECRET must be set when APP_ENV=production")
