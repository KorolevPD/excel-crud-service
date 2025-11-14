from pydantic import ValidationError, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Глобальные настройки."""

    DATABASE_URL: str = ""
    DATABASE_URL_ASYNC: str = ""
    ENV: str = "dev"
    DEBUG: bool = True
    MAX_ROWS_PER_BATCH: int = Field(default=10000, ge=5000)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


try:
    settings = Settings()
except ValidationError as e:
    raise SystemExit(f"Ошибка конфигурации:\n{e}")
