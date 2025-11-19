import logging
from typing import Any, Dict

from app.exceptions import NotFoundError, ValidationError
from app.services.table_report_crud_service import TableReportService

logger = logging.getLogger(__name__)


class UpdateTableReportUseCase:
    def __init__(self, service: TableReportService):
        self.service = service

    async def execute(self, report_id: int, file_path: str, update_mode: str, unique_column: str) -> Dict[str, Any]:
        logger.info(f"Обновление отчета id={report_id}")

        report = await self.service.get_report(report_id)
        if not report:
            raise NotFoundError("Отчёт не найден")

        if update_mode not in ("replace", "append"):
            raise ValidationError("Режим должен быть replace или append")

        stats = await self.service.update_report_from_excel(report.id, file_path, update_mode, unique_column)

        logger.info("Отчет обновлен")
        return stats
