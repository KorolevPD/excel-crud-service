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
        columns_metadata={"col1": "string", "col2": "int"},
        file_path="/tmp/new.xlsx",
    )
    assert req.name == "New"
    assert req.user_id == "user_1"
    assert isinstance(req.columns_metadata, dict)
    assert req.columns_metadata == {"col1": "string", "col2": "int"}
    assert req.file_path == "/tmp/new.xlsx"


@pytest.mark.parametrize(
    "data",
    [
        {"name": "", "user_id": "123", "columns_metadata": {}},
        {"name": "Report", "columns_metadata": {}},
    ],
)
async def test_create_request_invalid(data: Dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        TableReportCreateRequest(**data)


async def test_update_request_valid() -> None:
    req = TableReportUpdateRequest(
        name="Updated",
        mode="replace",
        unique_column="id",
        file_path="/tmp/new.xlsx",
    )
    assert req.mode == "replace"
    if req.file_path:
        assert req.file_path.endswith(".xlsx")


async def test_update_request_partial() -> None:
    req = TableReportUpdateRequest(name=None)
    assert req.name is None
    assert req.model_dump(exclude_none=True) == {}


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
        total_rows=100,
        empty_values_count=5,
        unique_values_count=90,
        duplicate_values_count=5,
        completeness_percent=95.0,
    )
    assert stats.total_rows == 100
    assert stats.empty_values_count == 5
    assert stats.unique_values_count == 90
    assert stats.duplicate_values_count == 5
    assert stats.completeness_percent == 95.0


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
