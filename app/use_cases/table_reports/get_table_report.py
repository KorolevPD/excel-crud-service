import logging
from typing import Any, Dict

from app.clients.db.table_report_model import TableReport
from app.services.table_report_crud_service import TableReportService

logger = logging.getLogger(__name__)


class GetTableReportUseCase:
    def __init__(self, service: TableReportService):
        """
        Инициализирует use-case получения метаданных отчета.
        Args:
            service (TableReportService): Сервис табличных отчётов.
        Returns:
            None
        Raises:
            None
        """
        self.service = service

    async def execute(self, report_id: int) -> TableReport:
        """
        Возвращает отчёт по идентификатору.
        Args:
            report_id (int): Идентификатор отчёта.
        Returns:
            TableReport: Найденный отчёт.
        Raises:
            NotFoundError: Если отчёт не найден.
        """
        logger.info(
            "Получение отчета.",
            extra={
                "report_id": report_id,
            }
        )
        report = await self.service.get_report(report_id)
        logger.info(
            "Отчет получен.",
            extra={
                "report_id": report_id,
            }
        )
        return report


class GetTableReportDataUseCase:
    def __init__(self, service: TableReportService):
        """
        Инициализирует use-case получения отчета в формате Excel или JSON.
        Args:
            service (TableReportService): Сервис табличных отчётов.
        Returns:
            None
        Raises:
            None
        """
        self.service = service

    async def execute(
        self, report_id: int, as_format: str = "json", limit: int = 50, offset: int = 0
    ) -> bytes | Dict[str, Any]:
        """
        Возвращает отчёт в указанном формате.
        Args:
            report_id (int): Идентификатор отчёта.
            as_format (str): Формат результата ("json" или "excel").
            limit (int): Лимит строк для JSON.
            offset (int): Смещение строк для JSON.
        Returns:
            bytes | Dict[str, Any]: Данные отчёта в выбранном формате.
        Raises:
            ValueError: Если формат не поддерживается.
            NotFoundError: Если отчёт не найден.
        """
        report = await self.service.get_report(report_id)

        if as_format == "json":
            logger.info(
                "Получение отчета.",
                extra={
                    "report_id": report.id,
                    "as_format": as_format,
                }
            )
            json_result = await self.service.get_report_as_json(report.id, limit, offset)
            logger.info(
                "Отчет в формате JSON получен.",
                extra={
                    "report_id": report_id,
                    "as_format": as_format,
                }
            )
            return json_result

        if as_format == "excel":
            logger.info(
                "Получение отчета.",
                extra={
                    "report_id": report_id,
                    "as_format": as_format,
                }
            )
            excel_result = await self.service.get_report_as_excel(report_id)
            logger.info(
                "Отчет в формате Excel получен.",
                extra={
                    "report_id": report_id,
                    "as_format": as_format,
                }
            )
            return excel_result

        logger.error(
            "Неизвестный формат.",
            extra={
                "report_id": report_id,
                "as_format": as_format,
            }
        )
        raise ValueError("Формат не поддерживается")
