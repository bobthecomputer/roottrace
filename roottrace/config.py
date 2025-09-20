from __future__ import annotations

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables or .env files."""

    model_config = SettingsConfigDict(env_file=(".env", ".env.local"), env_prefix="ROOTTRACE_")

    data_dir: Path = Path("./artifacts")
    proof_dir: Path = Path("./proofs")
    log_dir: Path = Path("./audit-logs")
    db_path: Path = Path("./roottrace.db")
    retention_days: int = 30
    timezone: str = "UTC"
    enable_network_fetch: bool = False
    legal_note: str | None = None
    scraper_platform: str | None = None
    scraper_tool: str | None = None
    scraper_cookies_path: Path | None = None
    scraper_rate_qps: float = 0.2
    scraper_max_items: int = 100

    @field_validator("data_dir", "proof_dir", "log_dir", mode="after")
    @classmethod
    def ensure_directory(cls, value: Path) -> Path:
        value.mkdir(parents=True, exist_ok=True)
        return value

    @field_validator("retention_days")
    @classmethod
    def validate_retention(cls, value: int) -> int:
        if value <= 0:
            msg = "retention_days must be positive"
            raise ValueError(msg)
        return value


settings = Settings()


def build_sqlite_url(path: Path | str) -> str:
    """Return a SQLAlchemy compatible SQLite URL."""

    absolute = path.resolve() if isinstance(path, Path) else Path(path).resolve()
    if absolute.suffix == ".db":
        return f"sqlite+aiosqlite:///{absolute}"
    return f"sqlite:///{absolute}"


__all__ = ["Settings", "build_sqlite_url", "settings"]
