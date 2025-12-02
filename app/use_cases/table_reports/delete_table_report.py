import logging
from typing import Dict

from app.services.table_report_crud_service import TableReportService

logger = logging.getLogger(__name__)


class DeleteTableReportUseCase:
    def __init__(self, service: TableReportService):
        """
        Инициализирует use-case удаления отчета.
        Args:
            service (TableReportService): Сервис табличных отчётов.
        Returns:
            None
        Raises:
            None
        """
        self.service = service

    async def execute(self, report_id: int) -> Dict[str, str]:
        """
        Удаляет отчёт по идентификатору.
        Args:
            report_id (int): Идентификатор отчёта.
        Returns:
            Dict[str, str]: Статус удаления.
        Raises:
            None
        """
        logger.info(
            "Удаление отчета.",
            extra={
                "report_id": report_id,
            }
        )

        await self.service.repo.delete(report_id)

        logger.info(
            "Отчет удален.",
            extra={
                "report_id": report_id,
            }
        )
        return {"status": "deleted"}
