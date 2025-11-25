from pathlib import Path

import pandas as pd
import pytest

from app.exceptions import NotFoundError, ValidationError
from app.services.table_report_crud_service import TableReportService
from app.use_cases.table_reports.create_table_report import CreateTableReportUseCase
from app.use_cases.table_reports.delete_table_report import DeleteTableReportUseCase
from app.use_cases.table_reports.get_quality_stats import GetQualityStatsUseCase
from app.use_cases.table_reports.get_table_report import GetTableReportUseCase
from app.use_cases.table_reports.update_table_report import UpdateTableReportUseCase

pytestmark = pytest.mark.asyncio


@pytest.fixture
def sample_excel(tmp_path: Path) -> str:
    file_path = tmp_path / "report.xlsx"
    df = pd.DataFrame(
        {
            "id": [1, 2],
            "name": ["Alice", "Bob"],
            "age": ["30", ""],
        }
    )
    df.to_excel(file_path, index=False)

    return str(file_path)


async def test_create_table_report_use_case(service: TableReportService, sample_excel: str) -> None:
    uc = CreateTableReportUseCase(service)

    report = await uc.execute(sample_excel, "MyReport", "user1", "id")

    assert report.id is not None
    assert report.name == "MyReport"
    assert await service.repo.get_by_id(report.id) is not None


async def test_get_table_report_use_case(service: TableReportService, sample_excel: str) -> None:
    create_uc = CreateTableReportUseCase(service)
    report = await create_uc.execute(sample_excel, "Test", "user1", "id")

    get_uc = GetTableReportUseCase(service)
    data = await get_uc.execute(report.id)
    assert data.id == report.id
    assert len(data.rows) == 2

    with pytest.raises(NotFoundError):
        await get_uc.execute(9999)


async def test_update_table_report_use_case(service: TableReportService, sample_excel: str, tmp_path: Path) -> None:
    create_uc = CreateTableReportUseCase(service)
    report = await create_uc.execute(sample_excel, "Test", "user1", "id")

    new_file = tmp_path / "new.xlsx"
    df = pd.DataFrame(
        {
            "id": [1, 3],
            "name": ["Alice", "Charlie"],
            "age": ["30", "25"],
        }
    )
    df.to_excel(new_file, index=False)

    uc = UpdateTableReportUseCase(service)

    with pytest.raises(ValidationError):
        await uc.execute(report.id, str(new_file), "INVALID", "id")

    stats = await uc.execute(report.id, str(new_file), "replace", "id")
    assert "new" in stats
    assert "updated" in stats
    assert len(stats["new"]) == 1
    assert len(stats["updated"]) == 1


async def test_delete_table_report_use_case(service: TableReportService, sample_excel: str) -> None:
    create_uc = CreateTableReportUseCase(service)
    report = await create_uc.execute(sample_excel, "ToDelete", "user1", "id")

    delete_uc = DeleteTableReportUseCase(service)
    result = await delete_uc.execute(report.id)

    assert result["status"] == "deleted"
    assert len(await service.repo.get_all_rows(report.id)) == 0


async def test_get_quality_stats_use_case(service: TableReportService, sample_excel: str) -> None:
    create_uc = CreateTableReportUseCase(service)
    report = await create_uc.execute(sample_excel, "Quality", "user1", "id")

    uc = GetQualityStatsUseCase(service)
    stats = await uc.execute(report.id)

    assert "empty_values" in stats
    assert "unique_values" in stats
    assert stats["rows"]["new"] == 0


async def test_use_case_logging_and_errors(service: TableReportService) -> None:
    get_uc = GetTableReportUseCase(service)

    with pytest.raises(NotFoundError):
        await get_uc.execute(12345)

    update_uc = UpdateTableReportUseCase(service)

    with pytest.raises(NotFoundError):
        await update_uc.execute(12345, "missing.xlsx", "replace", "id")
