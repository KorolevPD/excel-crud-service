from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


class ControllerBase(DeclarativeBase):
    """Базовый класс для всех моделей контроллера."""

    metadata = MetaData(schema="controller")
