from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, computed_field


class TableReportCreateRequest(BaseModel):
    """Запрос на создание нового табличного отчета."""

    name: str = Field(min_length=1, max_length=255, description="Название отчета.")
    user_id: str = Field(min_length=1, max_length=255, description="ID пользователя")
    unique_column: str = Field(min_length=1, max_length=100, description="Имя колонки для уникального ключа")

    model_config = {
        "json_schema_extra": {"examples": [{"name": "Отчет №1", "user_id": "user_123", "unique_column": "id_column"}]}
    }


class TableReportUpdateRequest(BaseModel):
    """Запрос на обновление существующего табличного отчета."""

    update_mode: Literal["replace", "append"] = Field(description="Режим обновления данных (replace, append)")
    unique_column: str = Field(description="Название уникального столбца для строк")


class TableReportGetDataRequest(BaseModel):
    """Запрос на создание нового табличного отчета."""

    report_id: int
    as_format: Literal["json", "excel"]
    limit: int = Field(50)
    offset: int = Field(0)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "report_id": 1,
                    "as_format": "json",
                    "limit": 5,
                    "offset": 0,
                }
            ]
        }
    }


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

    limit: int = Field(default=50, ge=1, le=500, description="Количество записей на странице")
    offset: int = Field(default=0, ge=0, description="Смещение для пагинации")
    report: TableReportResponse = Field(description="Метаданные отчета")
    rows: List[TableReportRowResponse] = Field(description="Список строк с данными")


class TableReportQualityStatsResponse(BaseModel):
    """Ответ со статистикой качества данных."""

    rows: Dict[str, int]
    empty_values: Dict[str, Any]
    unique_values: Dict[str, Any]


class TableReportListResponse(BaseModel):
    """Ответ со списком отчетов."""

    items: List[TableReportResponse] = Field(description="Список отчетов")

    @computed_field  # type: ignore
    @property
    def total(self) -> int:
        return len(self.items)


class TableReportListQuery(BaseModel):
    """Параметры запроса списка отчетов."""

    user_id: Optional[str] = Field(default=None, description="Фильтр по пользователю")
    limit: int = Field(default=50, ge=1, le=500, description="Количество записей на странице")
    offset: int = Field(default=0, ge=0, description="Смещение для пагинации")
