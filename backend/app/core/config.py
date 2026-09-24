from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = (
        "mysql+pymysql://novaroute:local_dev_password@127.0.0.1:3306/novaroute?charset=utf8mb4"
    )
    frontend_url: str = "http://localhost:3000"
    allowed_origins: str = "http://localhost:3000"
    cookie_name: str = "novaroute_session"
    session_hours: int = 24
    cookie_secure: bool = False
    login_rate_limit: int = 20
    upload_rate_limit: int = 10
    ai_mode: Literal["live", "demo"] = "demo"
    openrouter_api_key: str = ""
    openrouter_model: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    ai_timeout_seconds: float = 30
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_cache_dir: Path = Path("model-cache")
    embedding_load_on_start: bool = False
    recommendation_min_score: float = 0.80
    upload_max_bytes: int = 5 * 1024 * 1024
    upload_max_pages: int = 10
    upload_max_text: int = 24000
    upload_private_dir: Path = Path("uploads")
    smtp_host: str = "127.0.0.1"
    smtp_port: int = 1025
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = False
    smtp_ssl: bool = False
    smtp_from: str = "NovaRoute <notifications@novaroute.test>"
    smtp_allow_real_recipients: bool = False

    @property
    def origins(self) -> list[str]:
        return [x.strip().rstrip("/") for x in self.allowed_origins.split(",")]

    @model_validator(mode="after")
    def secure_production(self):
        if any(origin == "*" or not origin.startswith(("http://", "https://")) for origin in self.origins):
            raise ValueError(
                "ALLOWED_ORIGINS must contain exact HTTP(S) origins; wildcard credentialed CORS is prohibited"
            )
        if self.environment == "production" and (not self.cookie_secure or self.ai_mode == "demo"):
            raise ValueError("Production requires COOKIE_SECURE=true and AI_MODE=live")
        return self


@lru_cache
def settings() -> Settings:
    return Settings()
