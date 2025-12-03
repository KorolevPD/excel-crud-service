import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile

from app.api.handlers.table_report_handlers import (
    create_table_report_handler,
    delete_table_report_handler,
    get_quality_stats_handler,
    get_table_report_data_handler,
    get_table_report_metadata_handler,
    list_table_reports_handler,
    update_table_report_handler,
)
from app.api.schemas import (
    TableReportCreateRequest,
    TableReportDataResponse,
    TableReportGetDataRequest,
    TableReportListQuery,
    TableReportListResponse,
    TableReportQualityStatsResponse,
    TableReportResponse,
    TableReportUpdateRequest,
)
from app.clients.db.table_report_model import TableReport
from app.exceptions import NotFoundError, ValidationError
from app.services.table_report_crud_service import TableReportService

router = APIRouter()

logger = logging.getLogger(__name__)


def get_table_report_service() -> TableReportService:
    """
    Возвращает экземпляр TableReportService для использования в Depends.
    Args:
        None
    Returns:
        TableReportService: Сервис работы с табличными отчётами.
    Raises:
        None
    """
    return TableReportService()


@router.post(
    "/table-reports",
    response_model=TableReportResponse,
    status_code=201,
    summary="Создание табличного отчeта из Excel файла",
)
async def create_table_report(
    response: Response,
    data: TableReportCreateRequest = Depends(),
    file: UploadFile = File(..., description="Excel-файл (.xlsx или .xls)"),
    service: TableReportService = Depends(get_table_report_service),
) -> TableReport:
    """
    Создаёт табличный отчёт из загруженного Excel-файла.
    Args:
        response (Response): HTTP-ответ для установки заголовков.
        data (TableReportCreateRequest): Данные для создания отчёта.
        file (UploadFile): Загруженный Excel-файл (.xlsx или .xls).
        service (TableReportService): Сервис работы с отчётами.
    Returns:
        TableReport: Созданный отчёт.
    Raises:
        HTTPException: 422 при ошибке валидации, 500 при других ошибках.
    """
    logger.info(
        "Создание табличного отчeта: начало обработки.",
        extra={
            "operation": "create_table_report",
            "content_type": file.content_type,
            "request_data": data.model_dump(),
        },
    )

    try:
        result = await create_table_report_handler(file, service, data)
        logger.info(
            "Табличный отчет успешно создан.",
            extra={
                "operation": "create_table_report",
                "report_id": result.id,
            },
        )
        response.headers["Location"] = f"/table-reports/{result.id}"
        return result
    except ValidationError as e:
        logger.warning(
            "Ошибка валидации при создании отчeта.",
            extra={
                "operation": "create_table_report",
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(422, detail=str(e))
    except Exception as e:
        logger.exception(
            "Неожиданная ошибка при создании отчeта.",
            extra={
                "operation": "create_table_report",
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(500)


@router.get("/table-reports/{report_id}", response_model=TableReportResponse, summary="Получение метаданных отчета")
async def get_table_report_metadata(
    report_id: int,
    service: TableReportService = Depends(get_table_report_service),
) -> TableReport:
    """
    Возвращает метаданные отчёта по его идентификатору.
    Args:
        report_id (int): Идентификатор отчёта.
        service (TableReportService): Сервис работы с отчётами.
    Returns:
        TableReport: Отчёт с метаданными.
    Raises:
        HTTPException: 404 если отчёт не найден.
    """
    logger.info(
        "Получение метаданных отчeта.",
        extra={
            "operation": "get_table_report_metadata",
            "report_id": report_id
        },
    )

    try:
        result = await get_table_report_metadata_handler(report_id, service)
        logger.info(
            "Метаданные отчeта успешно получены.",
            extra={
                "operation": "get_table_report_metadata",
                "report_id": report_id},
        )
        return result
    except NotFoundError as e:
        logger.warning(
            "Отчет не найден при запросе метаданных.",
            extra={
                "operation": "get_table_report_metadata",
                "report_id": report_id,
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(404, detail=str(e))


@router.get(
    "/table-reports/{report_id}/data",
    response_model=TableReportDataResponse,
    summary="Получение данных отчета (JSON или Excel)",
)
async def get_table_report_data(
    data: TableReportGetDataRequest = Depends(),
    service: TableReportService = Depends(get_table_report_service),
) -> Any:
    """
    Возвращает данные отчёта в формате JSON или Excel.
    Args:
        data (TableReportGetDataRequest): Параметры запроса отчёта.
        service (TableReportService): Сервис работы с отчётами.
    Returns:
        Any: Данные отчёта (JSON-словарь или StreamingResponse для Excel).
    Raises:
        HTTPException: 404 если отчёт не найден, 422 если формат некорректен.
    """
    logger.info(
        "Получение данных отчeта.",
        extra={
            "operation": "get_table_report_data",
            "data": data,
        },
    )

    try:
        result = await get_table_report_data_handler(data, service)
        logger.info(
            "Данные отчeта успешно возвращены.",
            extra={
                "operation": "get_table_report_data",
                "report_id": data.report_id,
                "as_format": data.as_format,
            },
        )
        return result
    except NotFoundError as e:
        logger.warning(
            "Отчет не найден при запросе данных.",
            extra={
                "operation": "get_table_report_data",
                "report_id": data.report_id,
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(404, detail=str(e))
    except ValueError as e:
        logger.warning(
            "Ошибка параметров при запросе данных отчeта.",
            extra={
                "operation": "get_table_report_data",
                "report_id": data.report_id,
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(422, detail=str(e))


@router.delete(
    "/table-reports/{report_id}",
    summary="Удаление отчeта",
    status_code=204,
    response_description="Отчет успешно удалeн",
)
async def delete_table_report(
    report_id: int,
    service: TableReportService = Depends(get_table_report_service),
) -> Response:
    """
    Удаляет отчёт по идентификатору.
    Args:
        report_id (int): Идентификатор отчёта.
        service (TableReportService): Сервис работы с отчётами.
    Returns:
        Response: HTTP-ответ со статусом 204.
    Raises:
        HTTPException: 404 если отчёт не найден.
    """
    logger.info(
        "Удаление табличного отчeта.",
        extra={
            "operation": "delete_table_report",
            "report_id": report_id,
        },
    )

    try:
        await delete_table_report_handler(report_id, service)
        logger.info(
            "Отчет успешно удалeн.",
            extra={
                "operation": "delete_table_report",
                "report_id": report_id,
            },
        )
        return Response(status_code=204)
    except NotFoundError as e:
        logger.warning(
            "Попытка удалить несуществующий отчёт.",
            extra={
                "operation": "delete_table_report",
                "report_id": report_id,
            },
        )
        raise HTTPException(404, detail=str(e))


@router.put("/table-reports/{report_id}", response_model=dict, summary="Обновление отчета из Excel файла")
async def update_table_report(
    report_id: int,
    data: TableReportUpdateRequest = Depends(),
    file: UploadFile = File(..., description="Excel-файл (.xlsx или .xls)"),
    service: TableReportService = Depends(get_table_report_service),
) -> Dict[str, Any]:
    """
    Обновляет отчёт содержимым нового Excel-файла.
    Args:
        report_id (int): Идентификатор отчёта.
        data (TableReportUpdateRequest): Параметры обновления отчёта.
        file (UploadFile): Новый Excel-файл (.xlsx или .xls).
        service (TableReportService): Сервис работы с отчётами.
    Returns:
        Dict[str, Any]: Результаты обновления отчёта.
    Raises:
        HTTPException: 404 если отчёт не найден, 422 при ошибках валидации или некорректного режима.
    """
    logger.info(
        "Обновление табличного отчёта.",
        extra={
            "operation": "update_table_report",
            "report_id": report_id,
            "request_data": data.model_dump(),
        },
    )

    try:
        result = await update_table_report_handler(report_id, file, service, data)
        logger.info(
            "Отчёт успешно обновлён.",
            extra={
                "operation": "update_table_report",
                "report_id": report_id
            },
        )
        return result

    except NotFoundError as e:
        logger.warning(
            "Отчёт не найден при обновлении.",
            extra={
                "operation": "update_table_report",
                "report_id": report_id,
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(404, detail=str(e))
    except (ValidationError, ValueError) as e:
        logger.warning(
            "Ошибка валидации при обновлении отчёта.",
            extra={
                "operation": "update_table_report",
                "report_id": report_id,
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(422, detail=str(e))


@router.get(
    "/table-reports/{report_id}/quality-stats",
    response_model=TableReportQualityStatsResponse,
    summary="Получение статистики качества данных",
)
async def get_quality_stats(
    report_id: int,
    service: TableReportService = Depends(get_table_report_service),
) -> Dict[str, Any]:
    """
    Возвращает статистику качества данных отчёта.
    Args:
        report_id (int): Идентификатор отчёта.
        service (TableReportService): Сервис работы с отчётами.
    Returns:
        Dict[str, Any]: Статистика качества отчёта.
    Raises:
        HTTPException: 404 если отчёт не найден.
    """
    logger.info(
        "Запрос статистики качества данных.",
        extra={
            "operation": "get_quality_stats",
            "report_id": report_id
        },
    )

    try:
        result = await get_quality_stats_handler(report_id, service)
        logger.info(
            "Статистика качества успешно возвращена.",
            extra={
                "operation": "get_quality_stats_handler",
                "report_id": report_id
            },
        )
        return result
    except NotFoundError as e:
        logger.warning(
            "Отчёт не найден при запросе статистики качества.",
            extra={
                "operation": "get_quality_stats_handler",
                "report_id": report_id,
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(404, detail=str(e))


@router.get(
    "/table-reports",
    response_model=TableReportListResponse,
    summary="Список табличных отчeтов с фильтрацией",
)
async def list_table_reports(
    data: TableReportListQuery = Depends(), service: TableReportService = Depends(get_table_report_service)
) -> Dict[str, List[TableReport]]:
    """
    Возвращает список табличных отчётов с возможностью фильтрации.
    Args:
        data (TableReportListQuery): Параметры фильтрации отчётов.
        service (TableReportService): Сервис работы с отчётами.
    Returns:
        Dict[str, List[TableReport]]: Словарь с ключом "items", содержащий список отчётов.
    Raises:
        None
    """
    logger.info(
        "Получение списка табличных отчётов",
        extra={
            "operation": "list_table_reports",
            "filters": data.model_dump(),
        },
    )
    items = await list_table_reports_handler(data, service)
    logger.info(
        "Список отчётов успешно возвращён",
        extra={
            "operation": "list_table_reports",
            "items_count": len(items),
        },
    )
    return {"items": items}
