from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Глобальные настройки."""

    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@db:5432/excel_crud"
    DATABASE_URL_ASYNC: str = "postgresql+asyncpg://postgres:postgres@db:5432/excel_crud"
    MAX_ROWS_PER_BATCH: int = Field(default=10000, ge=5000)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


try:
    settings = Settings()
except ValidationError as e:
    raise SystemExit(f"Ошибка конфигурации:\n{e}")
