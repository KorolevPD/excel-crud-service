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


def get_table_report_service() -> TableReportService:
    return TableReportService()


@router.post(
    "/table-reports",
    response_model=TableReportResponse,
    status_code=201,
    summary="Создание табличного отчёта из Excel файла",
)
async def create_table_report(
    response: Response,
    data: TableReportCreateRequest = Depends(),
    file: UploadFile = File(..., description="Excel-файл (.xlsx или .xls)"),
    service: TableReportService = Depends(get_table_report_service),
) -> TableReport:
    try:
        result = await create_table_report_handler(file, service, data)
        response.headers["Location"] = f"/table-reports/{result.id}"
        return result
    except ValidationError as e:
        raise HTTPException(422, detail=str(e))
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.get("/table-reports/{report_id}", response_model=TableReportResponse, summary="Получение метаданных отчета")
async def get_table_report_metadata(
    report_id: int,
    service: TableReportService = Depends(get_table_report_service),
) -> TableReport:
    try:
        return await get_table_report_metadata_handler(report_id, service)
    except NotFoundError as e:
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
    try:
        return await get_table_report_data_handler(data, service)
    except NotFoundError as e:
        raise HTTPException(404, detail=str(e))
    except ValueError as e:
        raise HTTPException(422, detail=str(e))


@router.delete(
    "/table-reports/{report_id}",
    summary="Удаление отчёта",
    status_code=204,
    response_description="Отчёт успешно удалён",
)
async def delete_table_report(
    report_id: int,
    service: TableReportService = Depends(get_table_report_service),
) -> Response:
    try:
        await delete_table_report_handler(report_id, service)
        return Response(status_code=204)
    except NotFoundError as e:
        raise HTTPException(404, detail=str(e))


@router.put("/table-reports/{report_id}", response_model=dict, summary="Обновление отчета из Excel файла")
async def update_table_report(
    report_id: int,
    data: TableReportUpdateRequest = Depends(),
    file: UploadFile = File(..., description="Excel-файл (.xlsx или .xls)"),
    service: TableReportService = Depends(get_table_report_service),
) -> Dict[str, Any]:
    try:
        return await update_table_report_handler(report_id, file, service, data)

    except NotFoundError as e:
        raise HTTPException(404, detail=str(e))
    except (ValidationError, ValueError) as e:
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
    try:
        return await get_quality_stats_handler(report_id, service)
    except NotFoundError as e:
        raise HTTPException(404, detail=str(e))


@router.get(
    "/table-reports",
    response_model=TableReportListResponse,
    summary="Список табличных отчётов с фильтрацией",
)
async def list_table_reports(
    data: TableReportListQuery = Depends(),
    service: TableReportService = Depends(get_table_report_service)
) -> Dict[str, List[TableReport]]:
    items = await list_table_reports_handler(data, service)
    return {"items": items}
