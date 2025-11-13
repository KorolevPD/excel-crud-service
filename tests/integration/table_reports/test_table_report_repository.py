from asyncio import sleep
from datetime import datetime

from _pytest.logging import LogCaptureFixture
import pytest

from app.clients.db.table_report_model import TableReport, TableReportRow
from app.clients.db.table_report_repository import TableReportRepository

pytestmark = pytest.mark.asyncio


async def test_create_report(repo: TableReportRepository, table_report: TableReport) -> None:
    created = await repo.create(table_report)

    assert created.id is not None
    assert created.name == table_report.name
    assert created.user_id == table_report.user_id
    assert created.columns_metadata == table_report.columns_metadata
    assert created.total_rows == table_report.total_rows


async def test_get_report(repo: TableReportRepository, table_report: TableReport) -> None:
    created = await repo.create(table_report)
    fetched = await repo.get_by_id(created.id)

    assert fetched is not None
    assert isinstance(fetched, TableReport)
    assert fetched.id == created.id
    assert fetched.name == created.name


async def test_get_non_existent_report(repo: TableReportRepository) -> None:
    non_existent = await repo.get_by_id(1)

    assert non_existent is None


async def test_update_report(repo: TableReportRepository, table_report: TableReport) -> None:
    created = await repo.create(table_report)
    old_updated_at = created.updated_at
    await sleep(0.01)
    updated = await repo.update(created, name="New")

    assert updated is not None
    assert updated.id == created.id
    assert updated.name == "New"
    assert isinstance(updated.updated_at, datetime)
    assert isinstance(old_updated_at, datetime)
    assert updated.updated_at > old_updated_at


async def test_delete_report(repo: TableReportRepository, table_report: TableReport) -> None:
    created = await repo.create(table_report)

    rows = [{"test_column": "str"}]
    await repo.create_rows(created.id, rows, "test_column")
    await repo.delete(created.id)

    created_rows = await repo.get_all_rows(created.id)

    assert len(created_rows) == 1
    assert isinstance(created_rows[0], TableReportRow)
    assert created_rows[0].is_deleted is True


async def test_create_report_db_error(
    repo: TableReportRepository, table_report: TableReport, caplog: LogCaptureFixture
) -> None:

    table_report.name = None  # type: ignore[assignment]

    with pytest.raises(Exception):
        await repo.create(table_report)

    assert "Ошибка при создании отчета" in caplog.text
