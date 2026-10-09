"""Environment-driven settings. No hard-coded machine IPs."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LOGSHIELD_",
        env_file=(REPO_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bind_host: str = "0.0.0.0"
    bind_port: int = 8000
    server_host: str = "127.0.0.1"
    server_port: int = 8000
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    database_url: str = "sqlite:///./data/logshield.db"
    correlation_window_seconds: int = 300
    weight_rule: float = 0.30
    weight_ml: float = 0.30
    weight_correlation: float = 0.25
    weight_behavioral: float = 0.15
    ml_model_label: str = "prototype Isolation Forest anomaly detector"
    implementation_phase: int = Field(default=13, description="Highest completed implementation phase")

    @computed_field
    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @computed_field
    @property
    def public_base_url(self) -> str:
        return f"http://{self.server_host}:{self.server_port}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
