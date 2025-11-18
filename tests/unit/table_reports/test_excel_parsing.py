from pathlib import Path
from zipfile import BadZipFile

import pandas as pd
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.services.table_report_crud_service import TableReportService

LARGE_FILE_ROW = 50000
LARGE_FILE_COL = 10
pytestmark = pytest.mark.asyncio


@pytest.fixture
def valid_excel_file(tmp_path: Path) -> Path:
    df = pd.DataFrame(
        {
            "String": ["String_1", "String_2"],
            "Integer": [1, 2],
            "Float": [1.1, 2.2],
            "Bool": [True, False],
            "Date": pd.to_datetime(["2024-01-01", "2025-02-01"]),
        }
    )
    file_path = tmp_path / "valid.xlsx"
    df.to_excel(file_path, index=False)
    return file_path


@pytest.fixture
def excel_with_empty_cells(tmp_path: Path) -> Path:
    df = pd.DataFrame(
        {
            "String": ["String_1", "String_2"],
            "Integer": [1, None],
            "Float": [1.1, None],
            "Bool": [True, None],
        }
    )
    file_path = tmp_path / "empty_cells.xlsx"
    df.to_excel(file_path, index=False)
    return file_path


@pytest.fixture
def invalid_files_path(tmp_path: Path) -> Path:
    file_path_txt = tmp_path / "invalid.txt"
    file_path_txt.write_text("not an excel file")

    file_path_xlsx = tmp_path / "invalid.xlsx"
    file_path_xlsx.write_text("not an excel file")

    return tmp_path


@pytest.fixture
def large_excel_file(tmp_path: Path) -> Path:
    file_path = tmp_path / "large.xlsx"
    columns = [f"col_{j}" for j in range(LARGE_FILE_COL)]

    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        header_written = False

        for start_row in range(0, LARGE_FILE_ROW, settings.MAX_ROWS_PER_BATCH):
            end_row = min(start_row + settings.MAX_ROWS_PER_BATCH, LARGE_FILE_ROW)

            chunk_data = [[f"{i}_{j}" for j in range(LARGE_FILE_COL)] for i in range(start_row, end_row)]

            df_chunk = pd.DataFrame(chunk_data, columns=columns)

            df_chunk.to_excel(
                writer,
                index=False,
                header=not header_written,
                startrow=writer.sheets["Sheet1"].max_row if header_written else 0,
            )

            header_written = True

    return file_path


async def test_parse_valid_excel_file(async_session: AsyncSession, valid_excel_file: Path) -> None:
    service = TableReportService(async_session)
    rows, metadata = await service._parse_excel_file(valid_excel_file.absolute().as_posix())

    assert isinstance(rows, list)
    assert len(rows) == 2
    assert "Integer" in metadata


async def test_parse_excel_with_empty_cells(async_session: AsyncSession, excel_with_empty_cells: Path) -> None:
    service = TableReportService(async_session)
    rows, metadata = await service._parse_excel_file(excel_with_empty_cells.absolute().as_posix())

    assert len(rows) == 2
    assert any(row.get("Integer") == "" for row in rows)


async def test_data_type_conversion(async_session: AsyncSession, valid_excel_file: Path) -> None:
    service = TableReportService(async_session)
    rows, _ = await service._parse_excel_file(valid_excel_file.absolute().as_posix())
    first_row = rows[0]

    for value in first_row.values():
        assert isinstance(value, str)
    assert first_row["String"] == "String_1"
    assert first_row["Integer"] == "1"
    assert first_row["Float"] == "1.1"
    assert first_row["Bool"] == "True"
    assert first_row["Date"] == "2024-01-01 00:00:00"


async def test_invalid_file_format(async_session: AsyncSession, invalid_files_path: Path) -> None:
    txt_file = invalid_files_path / "invalid.txt"
    xlsx_file = invalid_files_path / "invalid.xlsx"
    service = TableReportService(async_session)
    with pytest.raises(ValueError):
        await service._validate_excel_file(txt_file.absolute().as_posix())
    with pytest.raises(BadZipFile):
        await service._validate_excel_file(xlsx_file.absolute().as_posix())


async def test_extract_columns_metadata(async_session: AsyncSession) -> None:
    service = TableReportService(async_session)
    df = pd.DataFrame(
        {
            "id": [1, 2],
            "float": [1.1, 2.2],
            "name": ["A", "B"],
            "active": [True, False],
            "date": pd.to_datetime(["2024-01-01", "2025-02-01"]),
        }
    )
    metadata = await service._extract_columns_metadata(df)

    assert metadata["id"] == "integer"
    assert metadata["float"] == "float"
    assert metadata["name"] == "string"
    assert metadata["active"] == "boolean"
    assert metadata["date"] == "datetime"


async def test_large_excel_file_parsing(async_session: AsyncSession, large_excel_file: Path) -> None:
    service = TableReportService(async_session)
    rows, metadata = await service._parse_excel_file(large_excel_file.absolute().as_posix())

    assert len(rows) == LARGE_FILE_ROW
    assert "col_0" in metadata
