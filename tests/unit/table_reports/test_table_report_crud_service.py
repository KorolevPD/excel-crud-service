from io import BytesIO
import os
from pathlib import Path
import tempfile

import pandas as pd
import pytest

from app.clients.db.table_report_model import TableReport
from app.services.table_report_crud_service import TableReportService

pytestmark = pytest.mark.asyncio


@pytest.fixture
def sample_excel_file(tmp_path: Path) -> str:
    file_path = tmp_path / "sample_excel.xlsx"
    df = pd.DataFrame({
        "col1": ["A", "B", "C"],
        "col2": [1, 2, 3],
    })
    df.to_excel(file_path, index=False)

    return str(file_path)


@pytest.fixture
def update_excel_file(tmp_path: Path) -> str:
    file_path = tmp_path / "update_excel.xlsx"
    df = pd.DataFrame({"col1": ["B", "D"], "col2": [20, 40]})
    df.to_excel(file_path, index=False)

    return str(file_path)


async def test_create_report(service: TableReportService, sample_excel_file: str) -> None:
    report = await service.create_report_from_excel(
        file_path=sample_excel_file,
        name="Test Report",
        user_id="user_1",
        unique_column="col1",
    )
    assert report.id is not None
    assert report.name == "Test Report"
    rows = await service.repo.get_all_rows(report.id)
    assert len(rows) == 3


async def test_invalid_excel_file(service: TableReportService) -> None:
    with pytest.raises(ValueError):
        await service._validate_excel_file("non_existing.xlsx")


async def test_get_report_as_excel(service: TableReportService, sample_excel_file: str) -> None:
    report = await service.create_report_from_excel(
        file_path=sample_excel_file,
        name="Excel Report",
        user_id="user_1",
        unique_column="col1",
    )
    excel_bytes = await service.get_report_as_excel(report.id)
    assert isinstance(excel_bytes, bytes)
    df = pd.read_excel(BytesIO(excel_bytes), engine="openpyxl")
    assert df.shape[0] == 3


async def test_get_report_as_json(service: TableReportService, sample_excel_file: str) -> None:
    report = await service.create_report_from_excel(
        file_path=sample_excel_file,
        name="JSON Report",
        user_id="user_1",
        unique_column="col1",
    )
    data = await service.get_report_as_json(report.id, limit=10, offset=0)
    assert data["report"].id == report.id
    assert len(data["rows"]) == 3


async def test_update_replace(service: TableReportService, sample_excel_file: str, update_excel_file: str) -> None:
    report = await service.create_report_from_excel(
        file_path=sample_excel_file,
        name="Replace Report",
        user_id="user_1",
        unique_column="col1",
    )
    result = await service.update_report_from_excel(
        report_id=report.id,
        file_path=update_excel_file,
        update_mode="replace",
        unique_column="col1",
    )
    assert len(result["new"]) == 1
    assert len(result["updated"]) == 1
    assert len(result["deleted"]) == 2


async def test_update_append(service: TableReportService, sample_excel_file: str) -> None:
    report = await service.create_report_from_excel(
        file_path=sample_excel_file,
        name="Append Report",
        user_id="user_1",
        unique_column="col1",
    )
    df_append = pd.DataFrame({"col1": ["D"], "col2": [4]})
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        df_append.to_excel(tmp.name, index=False, engine="openpyxl")
        tmp_path = tmp.name

    result = await service.update_report_from_excel(
        report_id=report.id,
        file_path=tmp_path,
        update_mode="append",
        unique_column="col1",
    )
    os.remove(tmp_path)
    assert len(result["new"]) == 1
    rows = await service.repo.get_all_rows(report.id)
    assert len(rows) == 4


async def test_validate_unique_column(service: TableReportService) -> None:
    with pytest.raises(ValueError):
        await service._validate_unique_column("non_existing", {"col1": "string", "col2": "integer"})


async def test_convert_value_to_text(service: TableReportService) -> None:
    assert await service._convert_value_to_text(None) == ""
    assert await service._convert_value_to_text(123) == "123"
    assert await service._convert_value_to_text(12.3) == "12.3"
    assert await service._convert_value_to_text("text") == "text"


async def test_compare_rows_by_unique_column(service: TableReportService) -> None:
    report = TableReport(name="Compare Test", user_id="user_1",
                         columns_metadata={"col1": "string"})
    report = await service.repo.create(report)
    old_rows = [{"col1": "A"}, {"col1": "B"}]
    await service.repo.create_rows(report.id, old_rows, "col1")
    new_rows = [{"col1": "B"}, {"col1": "C"}]
    old_rows_objects = await service.repo.get_all_rows(report.id)
    new_items, updated_items, deleted_items = await service._compare_rows_by_unique_column(
        old_rows_objects, new_rows, "col1")
    assert len(new_items) == 1
    assert len(updated_items) == 1
    assert len(deleted_items) == 1


async def test_delete_report(service: TableReportService, sample_excel_file: str) -> None:
    report = await service.create_report_from_excel(
        file_path=sample_excel_file,
        name="Delete Report",
        user_id="user_1",
        unique_column="col1",
    )
    await service.delete_report(report.id)
    rows = await service.repo.get_all_rows(report.id)
    assert all(row.is_deleted for row in rows)
