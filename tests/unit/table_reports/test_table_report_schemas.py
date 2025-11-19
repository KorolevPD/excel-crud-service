from datetime import datetime, timezone
from typing import Any, Dict

from pydantic import ValidationError
import pytest

from app.api.schemas import (
    TableReportCreateRequest,
    TableReportDataResponse,
    TableReportListQuery,
    TableReportListResponse,
    TableReportQualityStatsResponse,
    TableReportResponse,
    TableReportRowResponse,
    TableReportUpdateRequest,
)

pytestmark = pytest.mark.asyncio


async def test_create_request_valid() -> None:
    req = TableReportCreateRequest(
        name="New",
        user_id="user_1",
        unique_column="col",
    )
    assert req.name == "New"
    assert req.user_id == "user_1"
    assert req.unique_column == "col"


@pytest.mark.parametrize(
    "data",
    [
        {"name": "", "user_id": "123", "unique_column": {}},
        {"name": "Report", "columns_metadata": {}},
    ],
)
async def test_create_request_invalid(data: Dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        TableReportCreateRequest(**data)


async def test_update_request_valid() -> None:
    req = TableReportUpdateRequest(
        report_id=1,
        update_mode="replace",
        unique_column="id",
    )
    assert req.report_id == 1
    assert req.update_mode == "replace"
    assert req.unique_column == "id"


async def test_table_report_response_serialization() -> None:
    now = datetime.now(timezone.utc)
    resp = TableReportResponse(
        id=1,
        name="Report",
        user_id="user_1",
        columns_metadata={"col": "int"},
        total_rows=10,
        created_at=now,
        updated_at=now,
    )
    data = resp.model_dump()
    assert data["id"] == resp.id
    assert data["name"] == resp.name
    assert data["user_id"] == resp.user_id
    assert data["columns_metadata"] == resp.columns_metadata
    assert data["total_rows"] == resp.total_rows
    assert data["user_id"] == resp.user_id
    assert data["total_rows"] == 10
    assert "created_at" in data
    assert "updated_at" in data


async def test_table_report_row_response() -> None:
    row = TableReportRowResponse(
        id=5,
        report_id=1,
        unique_value="row_5",
        is_deleted=False,
        values={"col": "val"},
    )
    assert row.report_id == 1
    assert not row.is_deleted
    assert "values" in row.model_dump()


async def test_table_report_data_response() -> None:
    now = datetime.now(timezone.utc)
    report = TableReportResponse(
        id=1,
        name="Test",
        user_id="user_1",
        columns_metadata={},
        total_rows=5,
        created_at=now,
        updated_at=now,
    )
    row = TableReportRowResponse(
        id=1,
        report_id=1,
        unique_value="val",
        is_deleted=False,
        values={},
    )
    resp = TableReportDataResponse(report=report, rows=[row])
    assert resp.report.id == 1
    assert len(resp.rows) == 1


async def test_quality_stats_response() -> None:
    stats = TableReportQualityStatsResponse(
        rows={
            "new": 0,
            "updated": 0,
            "deleted": 0,
        },
        empty_values={
            "total": {
                "id": 0,
                "value": 0,
            },
            "new": {
                "id": 0,
                "value": 0,
            },
        },
        unique_values={
            "total": {
                "id": 2,
                "value": 2,
            },
            "new": {
                "id": 0,
                "value": 0,
            },
        },
    )
    assert isinstance(stats.rows, dict)
    assert isinstance(stats.empty_values, dict)
    assert isinstance(stats.unique_values, dict)


async def test_list_response() -> None:
    now = datetime.now(timezone.utc)
    report = TableReportResponse(
        id=1,
        name="Test",
        user_id="u1",
        columns_metadata={},
        total_rows=1,
        created_at=now,
        updated_at=now,
    )
    lst = TableReportListResponse(items=[report])
    assert lst.total == 1
    assert lst.items[0].name == "Test"


async def test_list_query_defaults() -> None:
    q = TableReportListQuery()
    assert q.limit == 50
    assert q.offset == 0


@pytest.mark.parametrize("limit", [0, 1000])
async def test_list_query_invalid_limit(limit: int) -> None:
    with pytest.raises(ValidationError):
        TableReportListQuery(limit=limit)
