import logging

from app.clients.db.table_report_model import TableReport
from app.services.table_report_crud_service import TableReportService

logger = logging.getLogger(__name__)


class CreateTableReportUseCase:
    def __init__(self, service: TableReportService):
        """
        Инициализирует use-case создания отчета.
        Args:
            service (TableReportService): Сервис табличных отчётов.
        Returns:
            None
        Raises:
            None
        """
        self.service = service

    async def execute(self, file_path: str, name: str, user_id: str, unique_column: str) -> TableReport:
        """
        Создаёт отчёт на основе Excel-файла.
        Args:
            file_path (str): Путь к Excel-файлу.
            name (str): Название отчёта.
            user_id (str): Идентификатор пользователя.
            unique_column (str): Название уникального столбца.
        Returns:
            TableReport: Созданный отчёт.
        Raises:
            Exception: Любая ошибка обработки Excel.
        """
        logger.info(
            "Создание отчета.",
            extra={
                "file_path": file_path,
                "name": name,
                "user_id": user_id,
                "unique_column": unique_column,
            },
        )

        try:
            report = await self.service.create_report_from_excel(file_path, name, user_id, unique_column)
        except Exception as e:
            logger.error(
                "Ошибка парсинга Excel.",
                extra={
                    "file_path": file_path,
                    "name": name,
                    "user_id": user_id,
                    "unique_column": unique_column,
                    "error_type": type(e).__name__,
                },
            )
            raise

        logger.info(
            "Отчет создан.",
            extra={
                "file_path": file_path,
                "report_id": report.id,
                "name": report.name,
                "user_id": report.user_id,
                "unique_column": unique_column,
            },
        )
        return report
