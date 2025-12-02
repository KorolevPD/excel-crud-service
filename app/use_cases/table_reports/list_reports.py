from typing import Any, List
import logging

from app.clients.db.table_report_model import TableReport
from app.services.table_report_crud_service import TableReportService

logger = logging.getLogger(__name__)


class ListReportUseCase:
    def __init__(self, service: TableReportService):
        """
        Инициализирует use-case получения списка отчетов.
        Args:
            service (TableReportService): Сервис табличных отчётов.
        Returns:
            None
        Raises:
            None
        """
        self.service = service

    async def execute(self, data: dict[str, Any]) -> List[TableReport]:
        """
        Возвращает список отчётов по заданным фильтрам.
        Args:
            data (dict[str, Any]): Параметры фильтрации.
        Returns:
            List[TableReport]: Список найденных отчётов.
        Raises:
            Exception: Ошибка получения списка отчётов.
        """
        logger.info(
            "Получение списка отчетов.",
            extra={
                "data": data,
            }
        )

        try:
            items = await self.service.repo.list_reports(**data)
        except Exception as e:
            logger.error(
                "Ошибка получения списка отчетов.",
                extra={
                    "data": data,
                    "error_type": type(e).__name__,
                },
            )
            raise

        logger.info(
            "Отчеты получены.",
            extra={
                "reports_count": len(items),
            }
        )
        return items
