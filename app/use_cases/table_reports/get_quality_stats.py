import logging
from typing import Any, Dict

from app.services.table_report_crud_service import TableReportService

logger = logging.getLogger(__name__)


class GetQualityStatsUseCase:
    def __init__(self, service: TableReportService) -> None:
        """
        Инициализирует use-case расчёта статистики качества.
        Args:
            service (TableReportService): Сервис табличных отчётов.
        Returns:
            None
        Raises:
            None
        """
        self.service = service

    async def execute(self, report_id: int) -> Dict[str, Any]:
        """
        Выполняет расчет статистики качества для указанного отчёта.
        Args:
            report_id (int): Идентификатор отчёта для расчета статистики.
        Returns:
            Dict[str, Any]: Статистика качества, включая новые, обновленные и удалённые строки, пустые и уникальные
            значения по столбцам.
        Raises:
            NotFoundError: Если отчёт с указанным report_id не найден.
        """
        logger.info(
            "Расчет статистики качества.",
            extra={
                "report_id": report_id,
            }
        )

        stats = await self.service.calculate_quality_stats(report_id=report_id)

        logger.info(
            "Cтатистика качества расчитана.",
            extra={
                "report_id": report_id,
            }
        )
        return stats
