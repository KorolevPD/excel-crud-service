from pathlib import Path

from httpx import AsyncClient
import pandas as pd
import pytest


@pytest.fixture
def simple_excel_file(tmp_path: Path) -> Path:
    df = pd.DataFrame({"id": [1, 2], "value": ["A", "B"]})
    file_path = tmp_path / "test.xlsx"
    df.to_excel(file_path, index=False)
    return file_path


@pytest.fixture
def invalid_excel_file(tmp_path: Path) -> Path:
    file_path = tmp_path / "broken.bin"
    file_path.write_bytes(b"not-an-excel")
    return file_path


@pytest.fixture
def updated_excel_file(tmp_path: Path) -> Path:
    df = pd.DataFrame({"id": [1, 2, 3], "value": ["A", "B", "C"]})
    file_path = tmp_path / "update.xlsx"
    df.to_excel(file_path, index=False)
    return file_path


@pytest.mark.asyncio
async def test_create_report_success(client: AsyncClient, simple_excel_file: Path) -> None:
    with open(simple_excel_file, "rb") as f:
        resp = await client.post(
            "/table-reports",
            params={"name": "Test Report", "user_id": "user-1", "unique_column": "id"},
            files={"file": ("test.xlsx", f)},
        )

    assert resp.status_code == 201
    assert "id" in resp.json()
    assert resp.json()["name"] == "Test Report"


@pytest.mark.asyncio
async def test_create_report_invalid_file(client: AsyncClient, invalid_excel_file: Path) -> None:
    with open(invalid_excel_file, "rb") as f:
        files = {"file": ("bad.bin", f, "application/octet-stream")}
        data = {"name": "Broken", "user_id": "1"}

        resp = await client.post("/table-reports", data=data, files=files)

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_report_metadata(client: AsyncClient, simple_excel_file: Path) -> None:
    with open(simple_excel_file, "rb") as f:
        resp = await client.post(
            "/table-reports",
            params={"name": "Test Report", "user_id": "user-1", "unique_column": "id"},
            files={"file": ("test.xlsx", f)},
        )

    report_id = resp.json()["id"]
    assert resp.status_code == 201

    resp2 = await client.get(f"/table-reports/{report_id}")
    assert resp2.status_code == 200
    assert resp2.json()["id"] == report_id


@pytest.mark.asyncio
async def test_get_report_not_found(client: AsyncClient) -> None:
    resp = await client.get("/table-reports/999999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_report_data_excel(client: AsyncClient, simple_excel_file: Path) -> None:
    with open(simple_excel_file, "rb") as f:
        resp = await client.post(
            "/table-reports",
            params={"name": "Test Report", "user_id": "user-1", "unique_column": "id"},
            files={"file": ("test.xlsx", f)},
        )

    report_id = resp.json()["id"]

    resp2 = await client.get(f"/table-reports/{report_id}/data?as_format=excel")
    assert resp2.status_code == 200
    assert resp2.headers["Content-Type"].startswith("application/vnd")


@pytest.mark.asyncio
async def test_get_report_data_json(client: AsyncClient, simple_excel_file: Path) -> None:
    with open(simple_excel_file, "rb") as f:
        resp = await client.post(
            "/table-reports",
            params={"name": "Test Report", "user_id": "user-1", "unique_column": "id"},
            files={"file": ("test.xlsx", f)},
        )
    report_id = resp.json()["id"]

    resp2 = await client.get(f"/table-reports/{report_id}/data?as_format=json")
    assert resp2.status_code == 200
    data = resp2.json()
    assert "rows" in data
    assert len(data["rows"]) > 0


@pytest.mark.asyncio
async def test_update_report_replace(client: AsyncClient, simple_excel_file: Path, updated_excel_file: Path) -> None:
    with open(simple_excel_file, "rb") as f:
        resp = await client.post(
            "/table-reports",
            params={"name": "Test Report", "user_id": "user-1", "unique_column": "id"},
            files={"file": ("test.xlsx", f)},
        )
    report_id = resp.json()["id"]

    with open(updated_excel_file, "rb") as f2:
        resp2 = await client.put(
            f"/table-reports/{report_id}?update_mode=replace&unique_column=id",
            files={"file": ("update.xlsx", f2)},
        )

    assert resp2.status_code == 200
    assert "updated" in resp2.json()


@pytest.mark.asyncio
async def test_update_report_append(client: AsyncClient, simple_excel_file: Path, updated_excel_file: Path) -> None:
    with open(simple_excel_file, "rb") as f:
        resp = await client.post(
            "/table-reports",
            params={"name": "Test Report", "user_id": "user-1", "unique_column": "id"},
            files={"file": ("test.xlsx", f)},
        )
    report_id = resp.json()["id"]

    with open(updated_excel_file, "rb") as f2:
        resp2 = await client.put(
            f"/table-reports/{report_id}?update_mode=append&unique_column=id",
            files={"file": ("update.xlsx", f2)},
        )

    assert resp2.status_code == 200


@pytest.mark.asyncio
async def test_update_report_invalid_unique_column(client: AsyncClient, simple_excel_file: Path) -> None:
    with open(simple_excel_file, "rb") as f:
        resp = await client.post(
            "/table-reports",
            params={"name": "Test Report", "user_id": "user-1", "unique_column": "id"},
            files={"file": ("test.xlsx", f)},
        )
    report_id = resp.json()["id"]

    with open(simple_excel_file, "rb") as f2:
        resp2 = await client.put(
            f"/table-reports/{report_id}?update_mode=replace&unique_column=unknown",
            files={"file": ("test.xlsx", f2)},
        )

    assert resp2.status_code == 422


@pytest.mark.asyncio
async def test_delete_report(client: AsyncClient, simple_excel_file: Path) -> None:
    with open(simple_excel_file, "rb") as f:
        resp = await client.post(
            "/table-reports",
            params={"name": "Test Report", "user_id": "user-1", "unique_column": "id"},
            files={"file": ("test.xlsx", f)},
        )
    report_id = resp.json()["id"]

    resp2 = await client.delete(f"/table-reports/{report_id}")
    assert resp2.status_code == 204


@pytest.mark.asyncio
async def test_get_quality_stats(client: AsyncClient, simple_excel_file: Path) -> None:
    with open(simple_excel_file, "rb") as f:
        resp = await client.post(
            "/table-reports",
            params={"name": "Test Report", "user_id": "user-1", "unique_column": "id"},
            files={"file": ("test.xlsx", f)},
        )
    report_id = resp.json()["id"]

    resp2 = await client.get(f"/table-reports/{report_id}/quality-stats")
    assert resp2.status_code == 200
    assert "rows" in resp2.json()


@pytest.mark.asyncio
async def test_list_reports(client: AsyncClient, simple_excel_file: Path) -> None:
    with open(simple_excel_file, "rb") as f:
        await client.post(
            "/table-reports",
            data={"name": "List1", "user_id": "u1"},
            files={"file": ("test.xlsx", f)},
        )
    with open(simple_excel_file, "rb") as f:
        await client.post(
            "/table-reports",
            data={"name": "List2", "user_id": "u1"},
            files={"file": ("test.xlsx", f)},
        )

    resp = await client.get("/table-reports?name=List")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) >= 2


@pytest.mark.asyncio
async def test_error_http_statuses(client: AsyncClient) -> None:
    resp = await client.get("/table-reports/1/data?as_format=xml")
    assert resp.status_code in (422, 404)
