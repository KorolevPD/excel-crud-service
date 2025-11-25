from typing import Any, List
import logging

from app.clients.db.table_report_model import TableReport
from app.services.table_report_crud_service import TableReportService

logger = logging.getLogger(__name__)


class ListReportUseCase:
    def __init__(self, service: TableReportService):
        self.service = service

    async def execute(self, data: dict[str, Any]) -> List[TableReport]:
        logger.info("[ListReport] Получение списка отчетов}")

        try:
            items = await self.service.repo.list_reports(**data)
        except Exception as e:
            logger.error(f"Ошибка получения списка отчетов: {e}")
            raise

        logger.info("[ListReport] Отчеты получены")
        return items
