import logging
from io import BytesIO
import os
import tempfile
from typing import Any, Dict, List

from fastapi import UploadFile
from fastapi.responses import StreamingResponse

from app.api.schemas import (
    TableReportCreateRequest,
    TableReportGetDataRequest,
    TableReportListQuery,
    TableReportUpdateRequest,
)
from app.clients.db.table_report_model import TableReport
from app.services.table_report_crud_service import TableReportService
from app.use_cases.table_reports.create_table_report import CreateTableReportUseCase
from app.use_cases.table_reports.delete_table_report import DeleteTableReportUseCase
from app.use_cases.table_reports.get_quality_stats import GetQualityStatsUseCase
from app.use_cases.table_reports.get_table_report import GetTableReportDataUseCase, GetTableReportUseCase
from app.use_cases.table_reports.update_table_report import UpdateTableReportUseCase
from app.use_cases.table_reports.list_reports import ListReportUseCase

logger = logging.getLogger(__name__)


async def create_table_report_handler(
    file: UploadFile,
    service: TableReportService,
    data: TableReportCreateRequest,
) -> TableReport:
    """
    Создаёт отчёт на основе загруженного Excel-файла.
    Args:
        file (UploadFile): Загруженный Excel-файл.
        service (TableReportService): Сервис работы с отчётами.
        data (TableReportCreateRequest): Данные для создания отчёта.
    Returns:
        TableReport: Созданный отчёт.
    Raises:
        Exception: Любая ошибка обработки файла или создания отчёта.
    """
    logger.info(
        "Создание табличного отчёта",
        extra={
            "operation": "create_table_report",
            "filename": file.filename,
            "content_type": file.content_type,
            "request_data": data.model_dump(),
        },
    )

    tmp_file = await _save_report_file(file)

    use_case = CreateTableReportUseCase(service)
    report = await use_case.execute(file_path=tmp_file, **data.model_dump())
    logger.info(
        "Отчет создан.",
        extra={
            "operation": "create_table_report_handler",
            "report_id": report,
            "file_path": file,
        },
    )
    return report


async def get_table_report_metadata_handler(
    report_id: int,
    service: TableReportService,
) -> TableReport:
    """
    Получает метаданные отчёта по идентификатору.
    Args:
        report_id (int): Идентификатор отчёта.
        service (TableReportService): Сервис работы с отчётами.
    Returns:
        TableReport: Отчёт с метаданными.
    Raises:
        NotFoundError: Если отчёт не найден.
    """
    logger.info(
        "Получение метаданных отчета.",
        extra={
            "operation": "get_table_report_metadata_handler",
            "report_id": report_id,
        },
    )
    use_case = GetTableReportUseCase(service)
    result = await use_case.execute(report_id)
    logger.info(
        "Метаданных отчета получены.",
        extra={
            "operation": "get_table_report_metadata_handler",
            "report_id": report_id,
        },
    )
    return result


async def get_table_report_data_handler(
    data: TableReportGetDataRequest,
    service: TableReportService,
) -> bytes | Dict[str, Any] | StreamingResponse:
    """
    Возвращает данные отчёта в формате JSON или Excel.
    Args:
        data (TableReportGetDataRequest): Параметры запроса отчёта.
        service (TableReportService): Сервис работы с отчётами.
    Returns:
        bytes | Dict[str, Any] | StreamingResponse: Данные отчёта в выбранном формате.
    Raises:
        ValueError: Если формат не поддерживается.
        NotFoundError: Если отчёт не найден.
    """
    logger.info(
        "Получение отчета.",
        extra={
            "operation": "get_table_report_data_handler",
            "data": data,
        },
    )
    use_case = GetTableReportDataUseCase(service)

    if data.as_format == "json":
        result = await use_case.execute(**data.model_dump())
        logger.info(
            "Отчет получен в формате JSON.",
            extra={
                "operation": "get_table_report_data_handler",
                "data": data,
            },
        )
        return result

    elif data.as_format == "excel":
        excel_bytes = await use_case.execute(data.report_id, "excel")
        if isinstance(excel_bytes, bytes):
            filename = f"report_{data.report_id}.xlsx"
            logger.info(
                "Отчет получен в формате Excel.",
                extra={
                    "operation": "get_table_report_data_handler",
                    "data": data,
                },
            )
            return StreamingResponse(
                BytesIO(excel_bytes),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Access-Control-Expose-Headers": "Content-Disposition",
                },
            )
    logger.error(
        "Некорректный форматы.",
        extra={
            "operation": "get_table_report_data_handler",
            "as_format": data.as_format,
        },
    )
    raise ValueError("Поддерживаемые форматы: Json или Excel")


async def delete_table_report_handler(report_id: int, service: TableReportService) -> None:
    """
    Удаляет отчёт по идентификатору.
    Args:
        report_id (int): Идентификатор отчёта.
        service (TableReportService): Сервис работы с отчётами.
    Returns:
        None
    Raises:
        None
    """
    logger.info(
        "Удаление отчета.",
        extra={
            "operation": "delete_table_report_handler",
            "report_id": report_id,
        },
    )
    use_case = DeleteTableReportUseCase(service)
    await use_case.execute(report_id)
    logger.info(
        "Отчет удален.",
        extra={
            "operation": "delete_table_report_handler",
            "report_id": report_id,
        },
    )


async def update_table_report_handler(
    report_id: int,
    file: UploadFile,
    service: TableReportService,
    data: TableReportUpdateRequest,
) -> Dict[str, Any]:
    """
    Обновляет отчёт содержимым Excel-файла.
    Args:
        report_id (int): Идентификатор отчёта.
        file (UploadFile): Новый Excel-файл.
        service (TableReportService): Сервис работы с отчётами.
        data (TableReportUpdateRequest): Параметры обновления отчёта.
    Returns:
        Dict[str, Any]: Результаты обновления.
    Raises:
        ValueError: Если режим обновления некорректен.
        NotFoundError: Если отчёт не найден.
    """
    logger.info(
        "Обновление отчета.",
        extra={
            "operation": "update_table_report_handler",
            "report_id": report_id,
        },
    )
    tmp_file = await _save_report_file(file)
    use_case = UpdateTableReportUseCase(service)

    stats = await use_case.execute(file_path=tmp_file, report_id=report_id, **data.model_dump())
    logger.info(
        "Отчет обновлен.",
        extra={
            "operation": "update_table_report_handler",
            "report_id": report_id,
        },
    )
    return stats


async def get_quality_stats_handler(report_id: int, service: TableReportService) -> Dict[str, Any]:
    """
    Возвращает статистику качества данных отчёта.
    Args:
        report_id (int): Идентификатор отчёта.
        service (TableReportService): Сервис работы с отчётами.
    Returns:
        Dict[str, Any]: Статистика качества отчёта.
    Raises:
        NotFoundError: Если отчёт не найден.
    """
    logger.info(
        "Получение статистики качества.",
        extra={
            "operation": "get_quality_stats_handler",
            "report_id": report_id,
        },
    )
    use_case = GetQualityStatsUseCase(service)
    result = await use_case.execute(report_id)
    logger.info(
        "Статистика качества получена.",
        extra={
            "operation": "get_quality_stats_handler",
            "report_id": report_id,
        },
    )
    return result


async def list_table_reports_handler(data: TableReportListQuery, service: TableReportService) -> List[TableReport]:
    """
    Возвращает список отчётов по заданным фильтрам.
    Args:
        data (TableReportListQuery): Параметры фильтрации.
        service (TableReportService): Сервис работы с отчётами.
    Returns:
        List[TableReport]: Список найденных отчётов.
    Raises:
        Exception: Ошибка получения списка отчётов.
    """
    logger.info(
        "Получение списка отчетов.",
        extra={
            "operation": "list_table_reports_handler",
            "data": data,
        },
    )
    use_case = ListReportUseCase(service)
    result = await use_case.execute(data.model_dump())
    logger.info(
        "Cписок отчетов получен.",
        extra={
            "operation": "list_table_reports_handler",
            "result_count": len(result),
        },
    )
    return result


async def _save_report_file(file: UploadFile) -> str:
    """
    Сохраняет загруженный файл во временное хранилище.
    Args:
        file (UploadFile): Загруженный файл.
    Returns:
        str: Путь к временно сохранённому файлу.
    Raises:
        Exception: Ошибка при сохранении файла.
    """
    suffix = os.path.splitext(str(file.filename))[1]
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as tmp:
        tmp.write(await file.read())
    return path
