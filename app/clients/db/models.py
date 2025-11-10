from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData


class ControllerBase(DeclarativeBase):
    """Базовый класс для всех моделей контроллера."""

    metadata = MetaData(schema="controller")
