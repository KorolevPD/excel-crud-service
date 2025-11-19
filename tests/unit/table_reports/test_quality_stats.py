from typing import Dict, List

import pytest

from app.clients.db.table_report_model import TableReport
from app.services.table_report_crud_service import TableReportService

LARGE_FILE_ROW = 50000
LARGE_FILE_COL = 10
pytestmark = pytest.mark.asyncio


@pytest.fixture()
async def sample_report(service: TableReportService, table_report: TableReport) -> TableReport:
    report = await service.repo.create(table_report)
    await service.repo.create_rows(
        report.id, [{"col1": "1", "col2": "A"}, {"col1": "2", "col2": ""}, {"col1": "3", "col2": "B"}], "col1"
    )
    return report


async def test_new_rows_count(service: TableReportService, sample_report: TableReport) -> None:
    new_rows: List[Dict[str, str]] = [{"col1": "4", "col2": "X"}]
    updated_rows: List[Dict[str, str]] = []
    deleted_rows: List[Dict[str, str]] = []

    stats = await service.calculate_quality_stats(sample_report.id, new_rows, updated_rows, deleted_rows)
    assert stats["rows"]["new"] == 1
    assert stats["rows"]["updated"] == 0
    assert stats["rows"]["deleted"] == 0


async def test_updated_rows_count(service: TableReportService, sample_report: TableReport) -> None:
    new_rows: List[Dict[str, str]] = []
    updated_rows = [{"col1": "1", "col2": "UPDATED"}]
    deleted_rows: List[Dict[str, str]] = []

    stats = await service.calculate_quality_stats(sample_report.id, new_rows, updated_rows, deleted_rows)

    assert stats["rows"]["updated"] == 1
    assert stats["rows"]["new"] == 0
    assert stats["rows"]["deleted"] == 0


@pytest.mark.asyncio
async def test_deleted_rows_count(service: TableReportService, sample_report: TableReport) -> None:
    new_rows: List[Dict[str, str]] = []
    updated_rows: List[Dict[str, str]] = []
    deleted_rows: List[Dict[str, str]] = [{"col1": "3"}]

    stats = await service.calculate_quality_stats(sample_report.id, new_rows, updated_rows, deleted_rows)

    assert stats["rows"]["deleted"] == 1


@pytest.mark.asyncio
async def test_empty_values(service: TableReportService, sample_report: TableReport) -> None:
    new_rows: List[Dict[str, str]] = [{"col1": "4", "col2": ""}]
    updated_rows: List[Dict[str, str]] = []
    deleted_rows: List[Dict[str, str]] = []

    stats = await service.calculate_quality_stats(sample_report.id, new_rows, updated_rows, deleted_rows)

    assert stats["empty_values"]["total"]["col2"] == 1
    assert stats["empty_values"]["new"]["col2"] == 1


@pytest.mark.asyncio
async def test_unique_values(service: TableReportService, sample_report: TableReport) -> None:
    """
    Существующие уникальные:
        id: {"1","2","3"} → 3
        value: {"A","", "B"} → 3

    Добавляем:
        {"col1": "4", "col2": "C"}

    → unique_total["col1"] = 4
      unique_total["col2"] = 4
      unique_new["col2"] = 1
    """
    new_rows: List[Dict[str, str]] = [{"col1": "4", "col2": "C"}]
    updated_rows: List[Dict[str, str]] = []
    deleted_rows: List[Dict[str, str]] = []

    await service.repo.append_rows(sample_report.id, new_rows, "col1")
    stats = await service.calculate_quality_stats(sample_report.id, new_rows, updated_rows, deleted_rows)

    assert stats["unique_values"]["total"]["col1"] == 4
    assert stats["unique_values"]["total"]["col2"] == 4
    assert stats["unique_values"]["new"]["col2"] == 1


@pytest.mark.asyncio
async def test_new_empty_values(service: TableReportService, sample_report: TableReport) -> None:
    new_rows = [
        {"col1": "4", "col2": ""},
        {"col1": "5", "col2": ""},
    ]

    stats = await service.calculate_quality_stats(sample_report.id, new_rows, [], [])

    assert stats["empty_values"]["new"]["col2"] == 2


@pytest.mark.asyncio
async def test_new_unique_values(service: TableReportService, sample_report: TableReport) -> None:
    new_rows = [
        {"col1": "4", "col2": "AAA"},
        {"col1": "5", "col2": "BBB"},
    ]

    stats = await service.calculate_quality_stats(sample_report.id, new_rows, [], [])

    assert stats["unique_values"]["new"]["col2"] == 2
