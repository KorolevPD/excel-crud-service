import logging
from typing import Any, Dict, Literal

from app.exceptions import ValidationError
from app.services.table_report_crud_service import TableReportService

logger = logging.getLogger(__name__)


class UpdateTableReportUseCase:
    def __init__(self, service: TableReportService):
        self.service = service

    async def execute(
            self, report_id: int, file_path: str, update_mode: Literal["replace", "append"], unique_column: str
            ) -> Dict[str, Any]:
        """
        Обновляет отчёт содержимым Excel-файла.
        Args:
            report_id (int): Идентификатор отчёта.
            file_path (str): Путь к Excel-файлу.
            update_mode (Literal["replace", "append"]): Режим обновления.
            unique_column (str): Название уникального столбца.
        Returns:
            Dict[str, Any]: Результаты обновления отчёта.
        Raises:
            ValidationError: Если update_mode некорректен.
            NotFoundError: Если отчёт не найден.
        """
        logger.info(
            "Обновление отчета.",
            extra={
                "report_id": report_id,
                "file_path": file_path,
                "update_mode": update_mode,
                "unique_column": unique_column,
            }
        )

        if update_mode not in ("replace", "append"):
            logger.error(
                "Некорректный update_mode.",
                extra={
                    "report_id": report_id,
                    "file_path": file_path,
                    "update_mode": update_mode,
                    "unique_column": unique_column,
                }
            )
            raise ValidationError("Некорректный update_mode.")

        report = await self.service.get_report(report_id)
        stats = await self.service.update_report_from_excel(report.id, file_path, update_mode, unique_column)

        logger.info(
            "Отчет обновлен.",
            extra={
                "report_id": report_id,
                "file_path": file_path,
                "update_mode": update_mode,
                "unique_column": unique_column,
            }
        )
        return stats
