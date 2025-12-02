from typing import Any, Dict, List

import pytest

from app.clients.db.table_report_model import TableReport
from app.clients.db.table_report_repository import TableReportRepository

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def saved_report(repo: TableReportRepository, table_report: TableReport) -> TableReport:
    """Создает и сохраняет отчёт в БД, возвращает его."""
    return await repo.create(table_report)


async def test_create_rows(repo: TableReportRepository, saved_report: TableReport) -> None:
    rows = [{"col1": "A", "col2": 1}, {"col1": "B", "col2": 2}]
    await repo.create_rows(saved_report.id, rows, "col1")

    created_rows = await repo.get_all_rows(saved_report.id)
    assert len(created_rows) == 2
    values_0 = {v.column_name: v.value for v in created_rows[0].values}
    assert values_0 == {"col1": "A", "col2": "1"}


async def test_get_rows_with_pagination(repo: TableReportRepository, saved_report: TableReport) -> None:
    rows = [{"col1": f"X{i}", "col2": i} for i in range(5)]
    await repo.create_rows(saved_report.id, rows, "col1")

    first_page = await repo.get_rows(saved_report.id, limit=2, offset=0)
    second_page = await repo.get_rows(saved_report.id, limit=2, offset=2)

    assert len(first_page) == 2
    assert len(second_page) == 2
    assert first_page[0].unique_value == "X0"
    assert second_page[0].unique_value == "X2"


async def test_get_rows_by_unique_value(repo: TableReportRepository, saved_report: TableReport) -> None:
    rows = [{"col1": "U1", "col2": 10}, {"col1": "U2", "col2": 20}, {"col1": "U3", "col2": 30}]
    await repo.create_rows(saved_report.id, rows, "col1")

    result = await repo.get_rows_by_unique_value(saved_report.id, ["U1", "U2"])
    assert len(result) == 2
    assert result[0].unique_value == "U1"
    assert result[1].unique_value == "U2"


async def test_get_row_values(repo: TableReportRepository, saved_report: TableReport) -> None:
    rows = [{"col1": "Row1", "col2": 100}]
    await repo.create_rows(saved_report.id, rows, "col1")

    all_rows = await repo.get_all_rows(saved_report.id)
    values = await repo.get_row_values(all_rows[0].id)

    assert values == {"col1": "Row1", "col2": "100"}


async def test_get_column_values(repo: TableReportRepository, saved_report: TableReport) -> None:
    rows = [{"col1": "A", "col2": 1}, {"col1": "B", "col2": 2}]
    await repo.create_rows(saved_report.id, rows, "col1")

    col_values = await repo.get_column_values(saved_report.id, "col2")
    assert set(col_values) == {"1", "2"}


async def test_replace_rows(repo: TableReportRepository, saved_report: TableReport) -> None:
    old_rows = [{"col1": "K1", "col2": 1}, {"col1": "K2", "col2": 2}]
    await repo.create_rows(saved_report.id, old_rows, "col1")

    new_rows = [{"col1": "K2", "col2": 200}, {"col1": "K3", "col2": 3}]
    added, updated, deleted = await repo.replace_rows(saved_report.id, new_rows, "col1")

    assert any(r["col1"] == "K3" for r in added)
    assert any(r["col1"] == "K2" for r in updated)
    assert any(r["unique_value"] == "K1" for r in deleted)


async def test_append_rows(repo: TableReportRepository, saved_report: TableReport) -> None:
    base = [{"col1": "A", "col2": 1}]
    await repo.create_rows(saved_report.id, base, "col1")

    new = [{"col1": "B", "col2": 2}, {"col1": "A", "col2": 999}]
    added = await repo.append_rows(saved_report.id, new, "col1")

    assert len(added) == 1
    assert added[0]["col1"] == "B"


async def test_update_row_values(repo: TableReportRepository, saved_report: TableReport) -> None:
    rows = [{"col1": "Up", "col2": "1"}]
    await repo.create_rows(saved_report.id, rows, "col1")

    row = (await repo.get_all_rows(saved_report.id))[0]
    await repo.update_row_values(row.id, {"col2": "999", "col3": "new"})

    updated = await repo.get_row_values(row.id)
    assert updated["col2"] == "999"
    assert updated["col3"] == "new"


async def test_count_rows(repo: TableReportRepository, saved_report: TableReport) -> None:
    rows = [{"col1": "C1", "col2": 1}, {"col1": "C2", "col2": 2}]
    await repo.create_rows(saved_report.id, rows, "col1")

    count = await repo.count_rows(saved_report.id)
    assert count == 2


async def test_count_empty_values(repo: TableReportRepository, saved_report: TableReport) -> None:
    rows: List[Dict[str, Any]] = [{"col1": "A", "col2": ""}, {"col1": "B", "col2": ""}, {"col1": "C", "col2": "str"}]
    await repo.create_rows(saved_report.id, rows, "col1")

    count = await repo.count_empty_values(saved_report.id, "col2")
    assert count == 2


async def test_count_unique_values(repo: TableReportRepository, saved_report: TableReport) -> None:
    rows = [{"col1": "A", "col2": 1}, {"col1": "B", "col2": 1}, {"col1": "C", "col2": 2}]
    await repo.create_rows(saved_report.id, rows, "col1")

    count = await repo.count_unique_values(saved_report.id, "col2")
    assert count == 2


async def test_row_diff_comparison(repo: TableReportRepository, saved_report: TableReport) -> None:
    initial = [{"col1": "A", "col2": 1}, {"col1": "B", "col2": 2}]
    await repo.create_rows(saved_report.id, initial, "col1")

    changed = [{"col1": "B", "col2": 222}, {"col1": "C", "col2": 3}]
    new, updated, deleted = await repo.replace_rows(saved_report.id, changed, "col1")

    assert {"B"} == {r["col1"] for r in updated}
    assert {"C"} == {r["col1"] for r in new}
    assert {"A"} == {r["unique_value"] for r in deleted}


async def test_replace_rows_eav_integrity(repo: TableReportRepository, saved_report: TableReport) -> None:
    old_rows = [
        {"col1": "K1", "col2": 1},
        {"col1": "K2", "col2": 2},
    ]
    await repo.create_rows(saved_report.id, old_rows, "col1")

    new_rows = [
        {"col1": "K2", "col2": 200},
        {"col1": "K3", "col2": 3},
    ]
    await repo.replace_rows(saved_report.id, new_rows, "col1")

    rows_in_db = await repo.get_all_rows(saved_report.id)

    grouped = {}
    for r in rows_in_db:
        grouped[r.unique_value] = {v.column_name: v.value for v in r.values}

    assert "K1" not in grouped
    assert grouped["K3"] == {"col1": "K3", "col2": "3"}
    assert grouped["K2"] == {"col1": "K2", "col2": "200"}
    assert set(grouped.keys()) == {"K2", "K3"}
