from io import BytesIO
import logging
import os
from typing import Any, Dict, List, Optional, Set, Tuple
from zipfile import BadZipFile

from openpyxl.utils.exceptions import InvalidFileException
import pandas as pd

from app.clients.db.sessions import session
from app.clients.db.table_report_model import TableReport, TableReportRow
from app.clients.db.table_report_repository import TableReportRepository
from app.config.settings import settings
from app.exceptions import NotFoundError

logger = logging.getLogger(__name__)


class TableReportService:
    """Сервис для работы с табличными отчётами."""

    SUPPORTED_FORMATS: Tuple[str, str] = (".xlsx", ".xls")

    repo: TableReportRepository

    def get_repository(self) -> TableReportRepository:
        """
        Возвращает экземпляр репозитория TableReportRepository.
        Args:
            None
        Returns:
            TableReportRepository: Экземпляр репозитория.
        Raises:
            None
        """
        return TableReportRepository(session)

    def __init__(self, repository: Optional[TableReportRepository] = None) -> None:
        """
        Инициализирует сервис табличных отчётов.
        Args:
            repository (Optional[TableReportRepository]): Кастомный репозиторий (опционально).
        Returns:
            None
        Raises:
            None
        """
        self.repo = repository or self.get_repository()

    async def create_report_from_excel(
        self, file_path: str, name: str, user_id: str, unique_column: str
    ) -> TableReport:
        """
        Создаёт отчёт и строки на основе Excel-файла.
        Args:
            file_path (str): Путь к Excel-файлу.
            name (str): Название отчёта.
            user_id (str): Идентификатор пользователя.
            unique_column (str): Название уникального столбца.
        Returns:
            TableReport: Созданный отчёт.
        Raises:
            ValueError: Если файл некорректен.
            NotFoundError: Если нужные данные не найдены.
        """
        logger.info(
            "Создание отчета из Excel.",
            extra={
                "operation": "create_report_from_excel",
                "file_path": file_path,
                "name": name,
                "user_id": user_id,
                "unique_column": unique_column,
            },
        )
        rows, columns_metadata = await self._parse_excel_file(file_path)

        await self._validate_unique_column(unique_column, columns_metadata)

        report = TableReport(
            name=name,
            user_id=user_id,
            columns_metadata=columns_metadata,
        )
        report = await self.repo.create(report)
        await self.repo.create_rows(report.id, rows, unique_column)
        logger.info(
            "Отчета создан.",
            extra={
                "operation": "create_report_from_excel",
                "report_id": report.id,
                "name": name,
                "user_id": user_id,
                "unique_column": unique_column,
            },
        )
        return report

    async def get_report(self, report_id: int) -> TableReport:
        """
        Получает отчёт по его идентификатору.
        Args:
            report_id (int): Идентификатор отчёта.
        Returns:
            TableReport: Найденный отчёт.
        Raises:
            NotFoundError: Если отчёт не найден.
        """
        logger.info(
            "Получение отчета.",
            extra={
                "operation": "get_report",
                "report_id": report_id,
            },
        )
        report = await self.repo.get_by_id(report_id)
        if report is None:
            logger.exception(
                "Ошибка получения отчета.",
                extra={
                    "operation": "get_report",
                    "report_id": report_id,
                },
            )
            raise NotFoundError(f"TableReport с id={report_id} не найден")
        logger.info(
            "Отчет получен.",
            extra={
                "operation": "get_report",
                "report_id": report_id,
            },
        )
        return report

    async def get_report_as_excel(self, report_id: int) -> bytes:
        """
        Возвращает отчёт в виде Excel-файла.
        Args:
            report_id (int): Идентификатор отчёта.
        Returns:
            bytes: Содержимое Excel-файла.
        Raises:
            NotFoundError: Если отчёт не найден.
        """
        logger.info(
            "Получение отчета в виде Excel-файла.",
            extra={
                "operation": "get_report_as_excel",
                "report_id": report_id,
            },
        )
        rows = await self.repo.get_all_rows(report_id)

        data = [{v.column_name: v.value for v in row.values} for row in rows]

        df = pd.DataFrame(data)

        output = BytesIO()
        df.to_excel(output, index=False, engine="openpyxl")
        logger.info(
            "Отчет в виде Excel-файла получен.",
            extra={
                "operation": "get_report_as_excel",
                "report_id": report_id,
            },
        )
        return output.getvalue()

    async def get_report_as_json(self, report_id: int, limit: int, offset: int) -> Dict[str, Any]:
        """
        Возвращает отчёт и строки в формате JSON.
        Args:
            report_id (int): Идентификатор отчёта.
            limit (int): Максимум возвращаемых строк.
            offset (int): Смещение строк.
        Returns:
            Dict[str, Any]: Данные отчёта и строк.
        Raises:
            NotFoundError: Если отчёт не найден.
        """
        logger.info(
            "Получение отчета в виде JSON.",
            extra={
                "operation": "get_report_as_json",
                "report_id": report_id,
                "limit": limit,
                "offset": offset,
            },
        )
        report = await self.repo.get_by_id(report_id)
        rows = await self.repo.get_rows(report_id, limit, offset)

        parsed = []
        for row in rows:
            parsed.append(
                {
                    "id": row.id,
                    "report_id": row.report_id,
                    "unique_value": row.unique_value,
                    "is_deleted": row.is_deleted,
                    "values": {v.column_name: v.value for v in row.values},
                }
            )

        logger.info(
            "Отчет получен в виде JSON.",
            extra={
                "operation": "get_report_as_json",
                "report_id": report_id,
                "limit": limit,
                "offset": offset,
            },
        )

        return {
            "report": report,
            "rows": parsed,
            "limit": limit,
            "offset": offset,
        }

    async def update_report_from_excel(
        self, report_id: int, file_path: str, update_mode: str, unique_column: str
    ) -> Dict[str, Any]:
        """
        Обновляет отчёт содержимым Excel-файла.
        Args:
            report_id (int): Идентификатор отчёта.
            file_path (str): Путь к Excel-файлу.
            update_mode (str): Режим обновления ("replace" или "append").
            unique_column (str): Уникальный столбец.
        Returns:
            Dict[str, Any]: Результаты обновления.
        Raises:
            ValueError: Если режим обновления некорректный.
            NotFoundError: Если отчёт не найден.
        """
        logger.info(
            "Обновление отчета.",
            extra={
                "operation": "update_report_from_excel",
                "report_id": report_id,
            },
        )
        new_rows, columns_metadata = await self._parse_excel_file(file_path)

        await self._validate_unique_column(unique_column, columns_metadata)

        report = await self.repo.get_by_id(report_id)
        if not report:
            raise NotFoundError(f"TableReport с id={report_id} не найден")
        await self.repo.update(report, **{"columns_metadata": columns_metadata})

        logger.info(
            "Отчет обновлен.",
            extra={
                "operation": "update_report_from_excel",
                "report_id": report_id,
            },
        )

        if update_mode == "replace":
            old_rows = await self.repo.get_all_rows(report_id)
            new, updated, deleted = await self._compare_rows_by_unique_column(old_rows, new_rows, unique_column)
            quality_stats = await self.calculate_quality_stats(report_id, new, updated, deleted)
            await self.repo.replace_rows(report_id, new_rows, unique_column)
            return {"new": new, "updated": updated, "deleted": deleted, "quality_stats": quality_stats}

        elif update_mode == "append":
            new = await self.repo.append_rows(report_id, new_rows, unique_column)
            return {"new": new}

        else:
            raise ValueError("update_mode должен быть 'replace' или 'append'")

    async def delete_report(self, report_id: int) -> None:
        """
        Удаляет отчёт по идентификатору.
        Args:
            report_id (int): Идентификатор отчёта.
        Returns:
            None
        Raises:
            None
        """
        logger.info(
            "Удаление отчета.",
            extra={
                "operation": "delete_report",
                "report_id": report_id,
            },
        )
        await self.repo.delete(report_id)
        logger.info(
            "Отчет удален.",
            extra={
                "operation": "updadelete_reportte_report_from_excel",
                "report_id": report_id,
            },
        )

    async def calculate_quality_stats(
        self,
        report_id: int,
        new_rows: List[Dict[str, str]] = [],
        updated_rows: List[Dict[str, str]] = [],
        deleted_rows: List[Dict[str, str]] = [],
    ) -> Dict[str, Any]:
        """
        Рассчитывает статистику качества данных отчёта.
        Args:
            report_id (int): Идентификатор отчёта.
            new_rows (List[Dict[str, str]]): Добавленные строки.
            updated_rows (List[Dict[str, str]]): Обновлённые строки.
            deleted_rows (List[Dict[str, str]]): Удалённые строки.
        Returns:
            Dict[str, Any]: Статистика качества.
        Raises:
            NotFoundError: Если отчёт не найден.
        """
        logger.info(
            "Расчет статистики качества.",
            extra={
                "operation": "calculate_quality_stats",
                "report_id": report_id,
            },
        )
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

        unique_new_count = {col: len(values) for col, values in unique_new.items()}

        logger.info(
            "Статистики качества расчитана.",
            extra={
                "operation": "calculate_quality_stats",
                "report_id": report_id,
            },
        )

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

    async def _validate_excel_file(self, file_path: str) -> None:
        """
        Валидирует Excel-файл перед обработкой.
        Args:
            file_path (str): Путь к Excel-файлу.
        Returns:
            None
        Raises:
            ValueError: Если файл не найден или пуст.
            InvalidFileException: Если файл некорректен.
            BadZipFile: Если структура файла повреждена.
        """
        logger.info(
            "Валидация файла.",
            extra={
                "operation": "_validate_excel_file",
                "file_path": file_path,
            },
        )

        if not os.path.exists(file_path):
            raise ValueError(f"Файл {file_path} не найден")

        if not file_path.endswith(self.SUPPORTED_FORMATS):
            raise ValueError("Поддерживаются только файлы .xlsx и .xls")

        try:
            df = pd.read_excel(file_path, engine="openpyxl", nrows=1)
        except (
            FileNotFoundError,
            InvalidFileException,
            ValueError,
        ) as e:
            logger.exception(
                "Ошибка при парсинге Excel файла.",
                extra={
                    "operation": "_validate_excel_file",
                    "file_path": file_path,
                    "error_type": type(e).__name__,
                },
            )
            raise
        except BadZipFile as e:
            logger.exception(
                "Некорректная структура Excel файла.",
                extra={
                    "operation": "_validate_excel_file",
                    "file_path": file_path,
                    "error_type": type(e).__name__,
                },
            )
            raise

        if df.empty:
            raise ValueError("Excel файл пустой")

        logger.info(
            "Валидация файла завершена.",
            extra={
                "operation": "_validate_excel_file",
                "file_path": file_path,
            },
        )

    async def _parse_excel_file(self, file_path: str) -> Tuple[List[Dict[str, str]], Dict[str, str]]:
        """
        Парсит Excel-файл и возвращает строки и метаданные колонок.
        Args:
            file_path (str): Путь к Excel-файлу.
        Returns:
            Tuple[List[Dict[str, str]], Dict[str, str]]: Список строк и метаданные колонок.
        Raises:
            ValueError: Если файл некорректен.
        """
        logger.info(
            "Парсинг файла.",
            extra={
                "operation": "_parse_excel_file",
                "file_path": file_path,
            },
        )
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

        logger.info(
            "Парсинг файла завершен.",
            extra={
                "operation": "_parse_excel_file",
                "file_path": file_path,
            },
        )

        return result, columns_metadata

    async def _compare_rows_by_unique_column(
        self,
        old_rows: List[TableReportRow],
        new_rows: List[Dict[str, str]],
        unique_column: str,
    ) -> Tuple[List[Dict[str, str]], List[Dict[str, str]], List[Dict[str, str]]]:
        """
        Сравнивает старые и новые строки по уникальному столбцу.
        Args:
            old_rows (List[TableReportRow]): Существующие строки.
            new_rows (List[Dict[str, str]]): Новые строки.
            unique_column (str): Название уникального столбца.
        Returns:
            Tuple[List[Dict[str, str]], List[Dict[str, str]], List[Dict[str, str]]]:
                Новые строки, обновлённые, удалённые.
        Raises:
            None
        """
        logger.info(
            "Проверка строк по стольбцу уникальности.",
            extra={
                "operation": "_compare_rows_by_unique_column",
                "unique_column": unique_column,
            },
        )
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
                updated_items.append(
                    {
                        "id": str(old_row.id),
                        **incoming,
                    }
                )

        for key in old_map.keys():
            if key not in new_map:
                deleted_items.append({"unique_value": key})

        logger.info(
            "Проверка строк по стольбцу уникальности завершена.",
            extra={
                "operation": "_compare_rows_by_unique_column",
                "unique_column": unique_column,
            },
        )

        return new_items, updated_items, deleted_items

    async def _convert_row_to_dict(self, row: TableReportRow) -> Dict[str, Any]:
        """
        Преобразует объект TableReportRow в словарь.
        Args:
            row (TableReportRow): Строка отчёта.
        Returns:
            Dict[str, Any]: Словарь значений строки.
        Raises:
            None
        """
        logger.info(
            "Пребразование TableReportRow в словарь.",
            extra={
                "operation": "_convert_row_to_dict",
            },
        )
        values_dict = {v.column_name: v.value for v in row.values}
        logger.info(
            "TableReportRow преобразован в словарь.",
            extra={
                "operation": "_convert_row_to_dict",
            },
        )
        return {
            "id": row.id,
            "unique_value": row.unique_value,
            **values_dict,
        }

    async def _extract_columns_metadata(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Извлекает метаданные столбцов из DataFrame.
        Args:
            df (pd.DataFrame): Исходный DataFrame.
        Returns:
            Dict[str, str]: Словарь с именами столбцов и типами данных.
        Raises:
            None
        """
        logger.info(
            "Извлечение метаданных столбцов.",
            extra={
                "operation": "_extract_columns_metadata",
            },
        )
        dtype_map = {
            "int64": "integer",
            "float64": "float",
            "object": "string",
            "bool": "boolean",
            "datetime64[ns]": "datetime",
        }
        metadata = {str(col): dtype_map.get(str(dtype), "unknown") for col, dtype in df.dtypes.items()}
        logger.info(
            "Извлечены метаданные столбцов.",
            extra={
                "operation": "_extract_columns_metadata",
                "metadata": metadata,
            },
        )
        return metadata

    async def _convert_value_to_text(self, value: Any) -> str:
        """
        Преобразует значение ячейки в строку.
        Args:
            value (Any): Значение ячейки.
        Returns:
            str: Текстовое представление значения.
        Raises:
            None
        """
        if pd.isna(value):
            return ""
        else:
            return str(value)

    async def _validate_unique_column(self, unique_column: str, columns_metadata: Dict[str, str]) -> None:
        """
        Проверяет наличие уникального столбца в метаданных.
        Args:
            unique_column (str): Название уникального столбца.
            columns_metadata (Dict[str, str]): Метаданные столбцов.
        Returns:
            None
        Raises:
            ValueError: Если уникальный столбец отсутствует.
        """
        if unique_column not in columns_metadata:
            raise ValueError(f"Указанный уникальный столбец '{unique_column}' отсутствует в Excel.")
