import logging
from typing import Any, Dict

from app.exceptions import NotFoundError
from app.services.table_report_crud_service import TableReportService

logger = logging.getLogger(__name__)


class GetQualityStatsUseCase:
    def __init__(self, service: TableReportService):
        self.service = service

    async def execute(self, report_id: int) -> Dict[str, Any]:
        logger.info(f"[GetQualityStats] Calculating stats for report {report_id}")

        report = await self.service.repo.get_by_id(report_id)
        if not report:
            raise NotFoundError("Отчёт не найден")

        stats = await self.service.calculate_quality_stats(
            report_id=report_id,
            new_rows=[],
            updated_rows=[],
            deleted_rows=[],
        )

        logger.info(f"[GetQualityStats] Stats computed: {stats}")
        return stats
