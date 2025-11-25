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


async def create_table_report_handler(
    file: UploadFile,
    service: TableReportService,
    data: TableReportCreateRequest,
) -> TableReport:
    tmp_file = await _save_report_file(file)

    use_case = CreateTableReportUseCase(service)
    report = await use_case.execute(file_path=tmp_file, **data.model_dump())
    return report


async def get_table_report_metadata_handler(
    report_id: int,
    service: TableReportService,
) -> TableReport:
    use_case = GetTableReportUseCase(service)
    result = await use_case.execute(report_id)
    return result


async def get_table_report_data_handler(
    data: TableReportGetDataRequest,
    service: TableReportService,
) -> bytes | Dict[str, Any] | StreamingResponse:
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


async def delete_table_report_handler(
    report_id: int,
    service: TableReportService
) -> None:
    use_case = DeleteTableReportUseCase(service)
    await use_case.execute(report_id)


async def update_table_report_handler(
    report_id: int,
    file: UploadFile,
    service: TableReportService,
    data: TableReportUpdateRequest,
) -> Dict[str, Any]:
    tmp_file = await _save_report_file(file)
    use_case = UpdateTableReportUseCase(service)

    stats = await use_case.execute(file_path=tmp_file, report_id=report_id, **data.model_dump())
    return stats


async def get_quality_stats_handler(
    report_id: int,
    service: TableReportService
) -> Dict[str, Any]:
    use_case = GetQualityStatsUseCase(service)
    return await use_case.execute(report_id)


async def list_table_reports_handler(
    data: TableReportListQuery,
    service: TableReportService
) -> List[TableReport]:
    use_case = ListReportUseCase(service)
    return await use_case.execute(data.model_dump())


async def _save_report_file(file: UploadFile) -> str:
    suffix = os.path.splitext(str(file.filename))[1]
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as tmp:
        tmp.write(await file.read())
    return path
