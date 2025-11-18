from io import BytesIO
from app.clients.db.table_report_repository import TableReportRepository
from app.clients.db.table_report_model import TableReport, TableReportRow
from zipfile import BadZipFile
import logging
import os
from typing import Any, Dict, List, Tuple, Set

from openpyxl.utils.exceptions import InvalidFileException
import pandas as pd

from app.config.settings import settings

logger = logging.getLogger(__name__)


class NotFoundError(LookupError):
    pass


class TableReportService():
    """Сервис для работы с табличными отчётами."""

    SUPPORTED_FORMATS: Tuple[str, str] = (".xlsx", ".xls")

    repo: TableReportRepository

    def __init__(self, repository: TableReportRepository) -> None:
        self.repo = repository

    async def create_report_from_excel(
            self, file_path: str, name: str, user_id: str, **kwargs: str) -> TableReport:
        """
        Создание отчёта на основе Excel файла.
        """
        rows, columns_metadata = await self._parse_excel_file(file_path)

        unique_column = kwargs.get(
            "unique_column", list(columns_metadata.keys())[0])

        await self._validate_unique_column(unique_column, columns_metadata)

        report = TableReport(
            name=name,
            user_id=user_id,
            columns_metadata=columns_metadata,
            unique_column=unique_column,
            **kwargs
        )

        report = await self.repo.create(report)

        await self.repo.create_rows(report.id, rows, unique_column)

        return report

    async def get_report(self, report_id: int) -> TableReport:
        """
        Возвращает метаданные отчета по report_id.

        Args:
            report_id (int): Идентификатор отчета.

        Returns:
            TableReport: Метаданные отчета.

        Raises:
            NotFoundError: Отчет по report_id не найден.
        """
        report = await self.repo.get_by_id(report_id)
        if report is None:
            raise NotFoundError(f"TableReport с id={report_id} не найден")
        return report

    async def get_report_as_excel(self, report_id: int) -> bytes:
        """Возвращает отчёт в виде Excel-файла."""

        rows = await self.repo.get_all_rows(report_id)

        data = [{v.column_name: v.value for v in row.values} for row in rows]

        df = pd.DataFrame(data)

        output = BytesIO()
        df.to_excel(output, index=False, engine="openpyxl")
        return output.getvalue()

    async def get_report_as_json(self, report_id: int, limit: int, offset: int) -> Dict[str, Any]:
        """Пагинированный JSON отчёта."""

        rows = await self.repo.get_rows(report_id, limit, offset)

        parsed = []
        for row in rows:
            parsed.append({
                "id": row.id,
                "unique_value": row.unique_value,
                "values": {v.column_name: v.value for v in row.values},
            })

        return {
            "limit": limit,
            "offset": offset,
            "count": len(parsed),
            "rows": parsed,
        }

    async def update_report_from_excel(
        self,
        report_id: int,
        file_path: str,
        update_mode: str,
        unique_column: str
    ) -> Dict[str, Any]:
        """
        Обновляет отчёт новыми данными из Excel-файла.

        update_mode:
            "replace" - полная замена
            "append" - дозапись
        """

        new_rows, columns_metadata = await self._parse_excel_file(file_path)

        await self._validate_unique_column(unique_column, columns_metadata)

        if update_mode == "replace":
            old_rows = await self.repo.get_all_rows(report_id)
            new, updated, deleted = await self._compare_rows_by_unique_column(old_rows, new_rows, unique_column)
            quality_stats = await self.calculate_quality_stats(report_id, new, updated, deleted, unique_column)
            await self.repo.replace_rows(report_id, new_rows, unique_column)
            return {"new": new, "updated": updated, "deleted": deleted, "quality_stats": quality_stats}

        elif update_mode == "append":
            new = await self.repo.append_rows(report_id, new_rows, unique_column)
            return {"new": new}

        else:
            raise ValueError("update_mode должен быть 'replace' или 'append'")

    async def delete_report(self, report_id: int) -> None:
        await self.repo.delete(report_id)

    async def _validate_excel_file(self, file_path: str) -> None:
        """
        Проверяет наличие файла, формат и корректность чтения Excel.

        Args:
            file_path (str): Путь к Excel файлу.

        Returns:
            None
        """
        if not os.path.exists(file_path):
            raise ValueError(f"Файл {file_path} не найден")

        if not file_path.endswith(self.SUPPORTED_FORMATS):
            raise ValueError("Поддерживаются только файлы .xlsx и .xls")

        try:
            df = pd.read_excel(file_path, engine="openpyxl", nrows=1)
        except (FileNotFoundError, InvalidFileException, ValueError, ):
            logger.exception("Ошибка при парсинге Excel файла")
            raise
        except BadZipFile:
            logger.exception("Некорректная структура Excel файла")
            raise

        if df.empty:
            raise ValueError("Excel файл пустой")

    async def _parse_excel_file(self, file_path: str) -> Tuple[List[Dict[str, str]], Dict[str, str]]:
        """
        Парсит Excel-файл в список строк (dict) и метаданные столбцов.

        Args:
            file_path (str): Путь к Excel файлу.

        Returns:
            Tuple[List[Dict], Dict]: Кортеж из списка строк и метаданных столбцов {имя: тип}.
        """
        await self._validate_excel_file(file_path)
        result: List[Dict[str, str]] = []
        batch_size = settings.MAX_ROWS_PER_BATCH
        start_row = 1

        with pd.ExcelFile(file_path, engine="openpyxl") as xls:
            df = pd.read_excel(xls, nrows=batch_size).fillna("")
            columns_metadata = await self._extract_columns_metadata(df)

        while True:
            df_batch = pd.read_excel(
                file_path, skiprows=range(1, start_row), nrows=batch_size, engine="openpyxl"
            ).fillna("")

            if df_batch.empty:
                break

            batch_dicts = [
                {str(k): await self._convert_value_to_text(v) for k, v in row.items()}
                for row in df_batch.to_dict(orient="records")
            ]
            result.extend(batch_dicts)

            start_row += batch_size

        return result, columns_metadata

    async def _compare_rows_by_unique_column(
        self,
        old_rows: List[TableReportRow],
        new_rows: List[Dict[str, str]],
        unique_column: str,
    ) -> Tuple[List[Dict[str, str]], List[Dict[str, str]], List[Dict[str, str]]]:
        """
        (new_rows, updated_rows, deleted_rows)
        """

        old_map = {r.unique_value: r for r in old_rows}
        new_map = {r[unique_column]: r for r in new_rows}

        new_items = []
        updated_items: list[dict[str, str]] = []
        deleted_items = []

        for key, incoming in new_map.items():
            if key not in old_map:
                new_items.append(incoming)
            else:
                old_row = old_map[key]
                updated_items.append({
                    "id": str(old_row.id),
                    **incoming,
                })

        for key in old_map.keys():
            if key not in new_map:
                deleted_items.append({"unique_value": key})

        return new_items, updated_items, deleted_items

    async def _convert_row_to_dict(self, row: TableReportRow) -> Dict[str, Any]:
        """
        Преобразует объект TableReportRow в словарь формата:
        {
            "id": int,
            "unique_value": str,
            "values": {column_name: value}
        }

        Args:
            row (TableReportRow): ORM-объект строки отчёта.

        Returns:
            Dict[str, Any]: Словарь с данными строки.
        """
        values_dict = {v.column_name: v.value for v in row.values}

        return {
            "id": row.id,
            "unique_value": row.unique_value,
            **values_dict,
        }

    async def _extract_columns_metadata(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Извлекает метаданные столбцов из DataFrame.

        Args:
            df (pd.DataFrame): Таблица pandas.

        Returns:
            Dict[str, str]: Метаданных столбцов (название столбца: тип данных).
        """
        dtype_map = {
            "int64": "integer",
            "float64": "float",
            "object": "string",
            "bool": "boolean",
            "datetime64[ns]": "datetime",
        }

        metadata = {str(col): dtype_map.get(str(dtype), "unknown")
                    for col, dtype in df.dtypes.items()}
        logger.debug(f"Извлечены метаданные столбцов: {metadata}")
        return metadata

    async def _convert_value_to_text(self, value: Any) -> str:
        """
        Конвертирует Excel-значение в строково представление.

        Args:
            value (Any): Значение из таблицы Excel.

        Returns:
            str: Конвертированная строка.
        """
        if pd.isna(value):
            return ""
        else:
            return str(value)

    async def _validate_unique_column(self, unique_column: str, columns_metadata: Dict[str, str]) -> None:
        """Проверка, что колонка уникальности существует."""

        if unique_column not in columns_metadata:
            raise ValueError(
                f"Указанный уникальный столбец '{unique_column}' отсутствует в Excel. "
                f"Доступные столбцы: {list(columns_metadata.keys())}"
            )

    async def calculate_quality_stats(
            self,
            report_id: int,
            new_rows: List[Dict[str, str]],
            updated_rows: List[Dict[str, str]],
            deleted_rows: List[Dict[str, str]],
            unique_column: str) -> Dict[str, Any]:

        report = await self.repo.get_by_id(report_id)
        if not report:
            raise NotFoundError(f"TableReport с id={report_id} не найден")

        new_count = len(new_rows)
        updated_count = len(updated_rows)
        deleted_count = len(deleted_rows)

        all_columns = report.columns_metadata.keys()

        empty_total = {col: await self.repo.count_empty_values(report.id, col) for col in all_columns}
        empty_new = {col: 0 for col in all_columns}

        for row in new_rows:
            for col, val in row.items():
                if val == "":
                    empty_new[col] += 1

        unique_total = {col: await self.repo.count_unique_values(report.id, col) for col in all_columns}
        unique_new: Dict[str, Set[str]] = {col: set() for col in all_columns}

        for row in new_rows:
            for col, val in row.items():
                unique_new[col].add(val)

        unique_new_count = {col: len(values)
                            for col, values in unique_new.items()}

        return {
            "rows": {
                "new": new_count,
                "updated": updated_count,
                "deleted": deleted_count,
            },
            "empty_values": {
                "total": empty_total,
                "new": empty_new,
            },
            "unique_values": {
                "total": unique_total,
                "new": unique_new_count,
            },
        }
