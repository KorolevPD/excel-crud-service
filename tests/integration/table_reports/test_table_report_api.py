from io import BytesIO
from pathlib import Path

from httpx import AsyncClient
import pandas as pd
import pytest

pytestmark = pytest.mark.asyncio


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


async def test_create_report_invalid_file(client: AsyncClient, invalid_excel_file: Path) -> None:
    with open(invalid_excel_file, "rb") as f:
        files = {"file": ("bad.bin", f, "application/octet-stream")}
        data = {"name": "Broken", "user_id": "1"}

        resp = await client.post("/table-reports", data=data, files=files)

    assert resp.status_code == 422


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


async def test_get_report_not_found(client: AsyncClient) -> None:
    resp = await client.get("/table-reports/999999")
    assert resp.status_code == 404


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


async def test_error_http_statuses(client: AsyncClient) -> None:
    resp = await client.get("/table-reports/1/data?as_format=xml")
    assert resp.status_code in (422, 404)


async def test_create_report_with_arbitrary_columns(client: AsyncClient, tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "id": [101, 102],
            "float": [99.90, 149.90],
            "bool": [True, False],
            "str": ["Первый товар", None],
            "date": ["2024-01-01", "2025-12-31"],
        }
    )
    file_path = tmp_path / "arbitrary_cols.xlsx"
    df.to_excel(file_path, index=False)

    with open(file_path, "rb") as f:
        resp = await client.post(
            "/table-reports",
            params={"name": "Test", "user_id": "user1", "unique_column": "id"},
            files={"file": ("arbitrary.xlsx", f)},
        )

    assert resp.status_code == 201
    report_id = resp.json()["id"]

    meta_resp = await client.get(f"/table-reports/{report_id}")
    metadata = meta_resp.json()["columns_metadata"]
    assert len(metadata) == 5
    assert metadata.get("float") == "float"
    assert metadata.get("bool") == "boolean"
    assert metadata.get("str") == "string"


async def test_update_replace_full_data_integrity(client: AsyncClient, tmp_path: Path) -> None:
    initial = pd.DataFrame(
        {"id": [1, 2, 3], "name": ["Alice", "Bob", "Charlie"], "score": [100, 200, 300], "active": [True, False, True]}
    )
    updated = pd.DataFrame(
        {
            "id": [2, 3, 4],
            "name": ["BOB_UPDATED", "Charlie", "David"],
            "score": [999, 300, 500],
            "active": [True, True, False],
            "new_col": ["extra", None, "yes"],
        }
    )

    init_path = tmp_path / "init.xlsx"
    update_path = tmp_path / "update.xlsx"
    initial.to_excel(init_path, index=False)
    updated.to_excel(update_path, index=False)

    with open(init_path, "rb") as f:
        resp = await client.post(
            "/table-reports",
            params={"name": "Integrity", "user_id": "u1", "unique_column": "id"},
            files={"file": ("f.xlsx", f)},
        )
    report_id = resp.json()["id"]

    with open(update_path, "rb") as f:
        await client.put(
            f"/table-reports/{report_id}?update_mode=replace&unique_column=id", files={"file": ("u.xlsx", f)}
        )

    data_resp = await client.get(f"/table-reports/{report_id}/data?as_format=json")
    rows = data_resp.json()["rows"]

    by_id = {row["unique_value"]: row["values"] for row in rows}

    assert len(rows) == 3
    assert by_id["2"]["name"] == "BOB_UPDATED"
    assert by_id["2"]["score"] == "999"
    assert by_id["2"]["active"] == "True"
    assert by_id["3"]["score"] == "300"
    assert by_id["4"]["new_col"] == "yes"
    assert "1" not in list(by_id.keys())


async def test_quality_stats_after_real_update(client: AsyncClient, tmp_path: Path) -> None:
    df1 = pd.DataFrame({"code": ["A1", "A2", "A3"], "price": [100, None, 300], "category": ["X", "X", None]})
    df2 = pd.DataFrame({"code": ["A1", "A3", "A4"], "price": [150, 300, None], "category": ["X", "Y", "Z"]})

    p1 = tmp_path / "v1.xlsx"
    df1.to_excel(p1, index=False)
    p2 = tmp_path / "v2.xlsx"
    df2.to_excel(p2, index=False)

    with open(p1, "rb") as f:
        r = await client.post(
            "/table-reports",
            params={"name": "QualityFlow", "user_id": "u1", "unique_column": "code"},
            files={"file": ("v1.xlsx", f)},
        )
    rid = r.json()["id"]

    stats1 = (await client.get(f"/table-reports/{rid}/quality-stats")).json()
    assert stats1["empty_values"]["total"]["price"] == 1
    assert stats1["empty_values"]["total"]["category"] == 1

    with open(p2, "rb") as f:
        await client.put(f"/table-reports/{rid}?update_mode=replace&unique_column=code", files={"file": ("v2.xlsx", f)})

    stats2 = (await client.get(f"/table-reports/{rid}/quality-stats")).json()
    assert stats2["empty_values"]["total"]["price"] == 1
    assert stats2["empty_values"]["total"]["category"] == 0
    assert stats2["unique_values"]["total"]["category"] == 3


async def test_export_excel_content_matches(client: AsyncClient, simple_excel_file: Path) -> None:
    with open(simple_excel_file, "rb") as f:
        resp = await client.post(
            "/table-reports",
            params={"name": "ExportCheck", "user_id": "u1", "unique_column": "id"},
            files={"file": ("orig.xlsx", f)},
        )
    report_id = resp.json()["id"]

    export_resp = await client.get(f"/table-reports/{report_id}/data?as_format=excel")
    assert export_resp.status_code == 200
    assert "application/vnd" in export_resp.headers["Content-Type"]

    exported_df = pd.read_excel(BytesIO(export_resp.content))
    original_df = pd.read_excel(simple_excel_file)

    exported_df = exported_df.sort_values("id").reset_index(drop=True)
    original_df = original_df.sort_values("id").reset_index(drop=True)

    pd.testing.assert_frame_equal(exported_df, original_df)


async def test_export_json_full_structure_and_data(client: AsyncClient, tmp_path: Path) -> None:
    df = pd.DataFrame({"uid": ["x1", "x2"], "amount": [10.5, 20.0], "flag": [True, False], "comment": ["note", None]})
    path = tmp_path / "json_export.xlsx"
    df.to_excel(path, index=False)

    with open(path, "rb") as f:
        r = await client.post(
            "/table-reports",
            params={"name": "JSON Export", "user_id": "u1", "unique_column": "uid"},
            files={"file": ("f.xlsx", f)},
        )
    rid = r.json()["id"]

    json_resp = await client.get(f"/table-reports/{rid}/data?as_format=json")
    data = json_resp.json()

    assert "rows" in data
    assert len(data["rows"]) == 2

    row1 = data["rows"][0]
    assert row1["values"]["uid"] == "x1"
    assert row1["values"]["amount"] == "10.5"
    assert row1["values"]["flag"] == "True"
    assert row1["values"]["comment"] == "note"
