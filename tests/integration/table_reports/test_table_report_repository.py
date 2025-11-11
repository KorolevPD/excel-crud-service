import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.db.table_report_model import TableReport
from app.clients.db.table_report_repository import TableReportRepository


@pytest.mark.asyncio
async def test_create_and_get_report(async_session: AsyncSession) -> None:
    repo = TableReportRepository(async_session)

    name = "Report"
    user_id = "1"
    columns_metadata = {"name": "name", "type": "string"}
    total_rows = 1

    report = TableReport(
        name=name,
        user_id=user_id,
        columns_metadata=columns_metadata,
        total_rows=total_rows,
    )

    created = await repo.create(report)
    assert created.id is not None

    fetched = await repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.name == name
    assert fetched.user_id == user_id
    assert fetched.columns_metadata == columns_metadata
    assert fetched.total_rows == total_rows


@pytest.mark.asyncio
async def test_update_report(async_session: AsyncSession) -> None:
    repo = TableReportRepository(async_session)
    report = TableReport(name="Old")
    created = await repo.create(report)

    updated = await repo.update(created.id, name="New")
    assert updated is not None
    assert updated.name == "New"


@pytest.mark.asyncio
async def test_delete_report(async_session: AsyncSession) -> None:
    repo = TableReportRepository(async_session)
    report = TableReport(name="ToDelete")
    created = await repo.create(report)

    await repo.delete(created.id)

    deleted = await repo.get_by_id(created.id)
    assert deleted is None
