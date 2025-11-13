from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TableReportCreateRequest(BaseModel):
    """Запрос на создание нового табличного отчета."""

    name: str = Field(min_length=1, max_length=255, description="Название отчета")
    user_id: str = Field(min_length=1, max_length=255, description="Идентификатор пользователя")
    columns_metadata: Dict[str, Any] = Field(description="Метаданные столбцов отчета (название и тип)")
    file_path: str = Field(pattern=r"(?i).*\.(xls|xlsx)$", description="Путь к загруженному файлу отчета")


class TableReportUpdateRequest(BaseModel):
    """Запрос на обновление существующего табличного отчета."""

    name: Optional[str] = Field(default=None, description="Новое имя отчета")
    mode: Optional[str] = Field(default=None, description="Режим обновления данных (replace, append)")
    unique_column: Optional[str] = Field(default=None, description="Название уникального столбца для строк")
    file_path: Optional[str] = Field(
        default=None, pattern=r"(?i).*\.(xls|xlsx)$", description="Путь к файлу для обновления данных"
    )


class TableReportResponse(BaseModel):
    """Ответ с основными метаданными отчета."""

    id: int = Field(description="Идентификатор отчета")
    name: str = Field(description="Название отчета")
    user_id: str = Field(description="Идентификатор пользователя")
    columns_metadata: Dict[str, Any] = Field(description="Метаданные столбцов")
    total_rows: int = Field(description="Количество строк в отчете")
    created_at: datetime = Field(description="Дата создания")
    updated_at: datetime = Field(description="Дата последнего обновления")


class TableReportRowResponse(BaseModel):
    """Ответ с одной строкой отчета."""

    id: int = Field(description="Идентификатор строки")
    report_id: int = Field(description="Идентификатор отчета")
    unique_value: str = Field(description="Уникальное значение строки")
    is_deleted: bool = Field(description="Признак удаления строки")
    values: Dict[str, Any] = Field(description="Значения по столбцам")


class TableReportDataResponse(BaseModel):
    """Ответ с данными отчета."""

    report: TableReportResponse = Field(description="Метаданные отчета")
    rows: List[TableReportRowResponse] = Field(description="Список строк с данными")


class TableReportQualityStatsResponse(BaseModel):
    """Ответ со статистикой качества данных."""

    total_rows: int = Field(description="Общее количество строк")
    empty_values_count: int = Field(description="Количество пустых значений")
    unique_values_count: int = Field(description="Количество уникальных значений")
    duplicate_values_count: int = Field(description="Количество дубликатов")
    completeness_percent: float = Field(description="Процент заполненности данных")


class TableReportListResponse(BaseModel):
    """Ответ со списком отчетов."""

    items: List[TableReportResponse] = Field(description="Список отчетов")
    total: int = Field(description="Общее количество отчетов")


class TableReportListQuery(BaseModel):
    """Параметры запроса списка отчетов."""

    user_id: Optional[str] = Field(default=None, description="Фильтр по пользователю")
    search: Optional[str] = Field(default=None, description="Поиск по названию")
    limit: int = Field(default=50, ge=1, le=500, description="Количество записей на странице")
    offset: int = Field(default=0, ge=0, description="Смещение для пагинации")
