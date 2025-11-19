from io import BytesIO
import os
import tempfile
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from fastapi.responses import StreamingResponse

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
from app.use_cases.table_reports.create_table_report import CreateTableReportUseCase
from app.use_cases.table_reports.delete_table_report import DeleteTableReportUseCase
from app.use_cases.table_reports.get_quality_stats import GetQualityStatsUseCase
from app.use_cases.table_reports.get_table_report import GetTableReportDataUseCase, GetTableReportUseCase
from app.use_cases.table_reports.update_table_report import UpdateTableReportUseCase

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
        tmp_file = await _save_report_file(file)

        use_case = CreateTableReportUseCase(service)
        result = await use_case.execute(file_path=tmp_file, **data.model_dump())
        response.headers["Location"] = f"/table-reports/{result.id}"
        return result

    except ValidationError as e:
        raise HTTPException(422, detail=str(e))


@router.get("/table-reports/{report_id}", response_model=TableReportResponse, summary="Получение метаданных отчета")
async def get_table_report_metadata(
    report_id: int,
    service: TableReportService = Depends(get_table_report_service),
) -> TableReport:
    try:
        use_case = GetTableReportUseCase(service)
        result = await use_case.execute(report_id)
        return result
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
        use_case = GetTableReportDataUseCase(service)

        if data.as_format == "json":
            result = await use_case.execute(**data.model_dump())
            return result

        elif data.as_format == "excel":
            excel_bytes = await use_case.execute(data.report_id, "excel")
            if isinstance(excel_bytes, bytes):
                filename = f"report_{data.report_id}.xlsx"
                return StreamingResponse(
                    BytesIO(excel_bytes),
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={
                        "Content-Disposition": f'attachment; filename="{filename}"',
                        "Access-Control-Expose-Headers": "Content-Disposition",
                    },
                )

        raise ValueError("Поддерживаемые форматы: Json или Excel")

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
        use_case = DeleteTableReportUseCase(service)
        await use_case.execute(report_id)
        return Response(status_code=204)
    except NotFoundError as e:
        raise HTTPException(404, detail=str(e))


@router.put("/table-reports/{report_id}", response_model=dict, summary="Обновление отчета из Excel файла")
async def update_table_report(
    data: TableReportUpdateRequest = Depends(),
    file: UploadFile = File(..., description="Excel-файл (.xlsx или .xls)"),
    service: TableReportService = Depends(get_table_report_service),
) -> Dict[str, Any]:
    try:
        tmp_file = await _save_report_file(file)
        use_case = UpdateTableReportUseCase(service)

        stats = await use_case.execute(file_path=tmp_file, **data.model_dump())
        return stats

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
        use_case = GetQualityStatsUseCase(service)
        return await use_case.execute(report_id)
    except NotFoundError as e:
        raise HTTPException(404, detail=str(e))


@router.get(
    "/table-reports",
    response_model=TableReportListResponse,
    summary="Список табличных отчётов с фильтрацией",
)
async def list_table_reports(
    data: TableReportListQuery = Depends(), service: TableReportService = Depends(get_table_report_service)
) -> Dict[str, List[TableReport]]:
    items = await service.repo.list_reports(**data.model_dump())

    return {"items": items}


async def _save_report_file(file: UploadFile) -> str:
    suffix = os.path.splitext(str(file.filename))[1]
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as tmp:
        tmp.write(await file.read())
    return path
