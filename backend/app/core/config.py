from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SmartOCR API"
    api_prefix: str = "/api"
    database_url: str = "postgresql+asyncpg://smartocr:smartocr@localhost:5432/smartocr"
    jwt_secret: str = "change-me-before-production"
    jwt_expire_minutes: int = 60 * 24 * 7
    google_client_id: str = ""
    super_admin_email: str = "admin@example.com"
    allow_dev_login: bool = False
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173", "http://localhost:8080"]
    upload_dir: Path = Path("uploads")
    max_upload_mb: int = 20
    ocr_det_model_dir: str = ""
    ocr_rec_model_dir: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
