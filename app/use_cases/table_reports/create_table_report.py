import logging

from app.clients.db.table_report_model import TableReport
from app.services.table_report_crud_service import TableReportService

logger = logging.getLogger(__name__)


class CreateTableReportUseCase:
    def __init__(self, service: TableReportService):
        self.service = service

    async def execute(self, file_path: str, name: str, user_id: str, unique_column: str) -> TableReport:
        logger.info(f"[CreateTableReport] Creating report '{name}'")

        try:
            report = await self.service.create_report_from_excel(file_path, name, user_id, unique_column)
        except Exception as e:
            logger.error(f"Ошибка парсинга Excel: {e}")
            raise

        logger.info(f"[CreateTableReport] Report created ID={report.id}")
        return report
