import logging
from typing import Any, Dict

from app.clients.db.table_report_model import TableReport
from app.exceptions import NotFoundError
from app.services.table_report_crud_service import TableReportService

logger = logging.getLogger(__name__)


class GetTableReportUseCase:
    def __init__(self, service: TableReportService):
        self.service = service

    async def execute(self, report_id: int) -> TableReport:
        logger.info(f"Получение отчета id={report_id}")

        report = await self.service.get_report(report_id)
        if not report:
            logger.error(f"Отчет id={report_id} не найден")
            raise NotFoundError("Отчёт не найден")

        return report


class GetTableReportDataUseCase:
    def __init__(self, service: TableReportService):
        self.service = service

    async def execute(
        self, report_id: int, as_format: str = "json", limit: int = 50, offset: int = 0
    ) -> bytes | Dict[str, Any]:
        logger.info(f"Получение отчета id={report_id}")

        report = await self.service.get_report(report_id)
        if not report:
            logger.error(f"Отчет id={report_id} не найден")
            raise NotFoundError("Отчёт не найден")

        if as_format == "json":
            return await self.service.get_report_as_json(report.id, limit, offset)

        if as_format == "excel":
            return await self.service.get_report_as_excel(report_id)

        logger.error(f"Неизвестный формат: {as_format}")
        raise ValueError("Формат не поддерживается")
