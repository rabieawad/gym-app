"""All configuration comes from environment variables (or backend/.env in development)."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent

DEFAULT_SECRET = "dev-only-change-me-dev-only-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    app_name: str = "Ironhouse"
    # "production" makes the app refuse to start with the default SECRET_KEY.
    environment: str = "development"
    secret_key: str = DEFAULT_SECRET
    access_token_expire_minutes: int = 60 * 24 * 7  # one week
    # SQLite by default. For Postgres use e.g. postgresql+psycopg://user:pass@host/dbname
    database_url: str = f"sqlite:///{BACKEND_DIR / 'data' / 'gym.db'}"
    # The backend serves the static frontend from this folder (set to "" to disable).
    frontend_dir: str = str(ROOT_DIR / "frontend")
    # Comma-separated list. Only needed if the frontend is hosted on another origin.
    cors_origins: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
