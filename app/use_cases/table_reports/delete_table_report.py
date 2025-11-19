import logging
from typing import Dict

from app.services.table_report_crud_service import TableReportService

logger = logging.getLogger(__name__)


class DeleteTableReportUseCase:
    def __init__(self, service: TableReportService):
        self.service = service

    async def execute(self, report_id: int) -> Dict[str, str]:
        logger.info(f"[DeleteTableReport] Deleting report id={report_id}")

        await self.service.repo.delete(report_id)

        logger.info(f"[DeleteTableReport] Report {report_id} soft-deleted")
        return {"status": "deleted"}
