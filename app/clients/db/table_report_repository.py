from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.clients.db.table_report_model import TableReport, TableReportRow, TableReportValue

logger = logging.getLogger(__name__)


class TableReportRepository:
    """Репозиторий для работы с табличными отчетами."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # --- REPORT CRUD ---

    async def create(self, report: TableReport) -> TableReport:
        """
        Создаёт новый табличный отчёт в базе данных.

        Args:
            report (TableReport): Объект отчёта для сохранения. Должен быть валидным и
                содержать все обязательные поля (name, user_id и т.д).

        Returns:
            TableReport: Сохранённый объект отчёта с установленным "id" и актуальными данными из БД.

        Raises:
            SQLAlchemyError: Если произошла ошибка на уровне базы данных(нарушение ограничений,
                потеря соединения и т.д).
            IntegrityError: Если нарушены уникальные ограничения или внешние ключи.
            Exception: Любая другая непредвиденная ошибка.
        """
        try:
            self.session.add(report)
            await self.session.commit()
            await self.session.refresh(report)
            return report
        except Exception:
            await self.session.rollback()
            logger.exception("Ошибка при создании отчета")
            raise

    async def get_by_id(self, report_id: int) -> Optional[TableReport]:
        """
        Возвращает табличный отчёт по его идентификатору.

        Args:
            report_id (int): Идентификатор отчёта для поиска в базе данных.

        Returns:
            Optional[TableReport]: Объект отчёта, если найден и None, если отчёт не существует.

        Raises:
            SQLAlchemyError: Если произошла ошибка на уровне базы данных(нарушение ограничений,
                потеря соединения и т.д).
            Exception: Любая другая непредвиденная ошибка.
        """
        try:
            result = await self.session.execute(select(TableReport).where(TableReport.id == report_id))
            return result.scalar_one_or_none()
        except Exception:
            logger.exception("Ошибка при получении отчета")
            raise

    async def update(self, report: TableReport, **kwargs: Any) -> TableReport:
        """
        Обновляет поля отчёта по его идентификатору и возвращает обновлённую сущность.

        Args:
            report (TableReport): Идентификатор отчёта, который нужно обновить.
            **kwargs (Any): Поля и значения для обновления (например, title="Новый").

        Returns:
            TableReport: Обновлённый объект отчёта с актуальными данными из БД.

        Raises:
            NoResultFound: Если отчёт с указанным "report_id" не найден.
            SQLAlchemyError: Если произошла ошибка на уровне базы данных(нарушение ограничений,
                потеря соединения и т.д).
            Exception: Любая другая непредвиденная ошибка.
        """
        try:
            kwargs["updated_at"] = datetime.now(timezone.utc)
            for key, value in kwargs.items():
                setattr(report, key, value)

            await self.session.commit()
            await self.session.refresh(report)
            return report

        except Exception:
            await self.session.rollback()
            logger.exception("Ошибка при обновлении отчета")
            raise

    async def delete(self, report_id: int) -> None:
        """
        Выполняет "Soft delete" строк отчета.

        Устанавливает флаг "is_deleted" = True для всех строк отчета report_id. Физически строки не удаляются.

        Args:
            report_id (int): Идентификатор отчёта для пометки строк, как удалённых.

        Returns:
            None

        Raises:
            SQLAlchemyError: Если произошла ошибка на уровне базы данных(нарушение ограничений,
                потеря соединения и т.д).
            Exception: Любая другая непредвиденная ошибка.
        """
        try:
            stmt = sa_update(TableReportRow).where(TableReportRow.report_id == report_id).values(is_deleted=True)
            await self.session.execute(stmt)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            logger.exception("Ошибка при удалении отчета")
            raise

    # --- ROWS ---

    async def create_rows(self, report_id: int, rows: List[Dict[str, Any]], unique_column: str) -> None:
        """
        Производит массовое создание строк.

        Args:
            report_id (int): Идентификатор отчёта для создания строк.
            rows (List[Dict[str, Any]]): Список строк.
            unique_column (str): Имя столбца для определения уникальности строки. Должен присутствовать
                в параметре rows.

        Returns:
            None
        """
        try:
            new_rows = []
            for row_data in rows:
                new_row = TableReportRow(
                    report_id=report_id,
                    unique_value=row_data[unique_column],
                )
                new_row.values = [TableReportValue(column_name=k, value=str(v)) for k, v in row_data.items()]
                new_rows.append(new_row)

            self.session.add_all(new_rows)
            await self.session.commit()

        except Exception:
            await self.session.rollback()
            logger.exception("Ошибка при массовом создании строк")
            raise

    async def get_rows(self, report_id: int, limit: int, offset: int) -> List[TableReportRow]:
        """
        Получение строк отчета с пагинацией и загрузкой связанных значений.

        Args:
            report_id (int): Идентификатор отчёта, строки которого нужно получить.
            limit (int): Максимальное количество строк для выборки.
            offset (int): Смещение для пагинации.

        Returns:
            List[TableReportRow]: Список строк отчета с загруженными значениями.
        """
        try:
            stmt = (
                select(TableReportRow)
                .where(TableReportRow.report_id == report_id)
                .options(selectinload(TableReportRow.values))
                .limit(limit)
                .offset(offset)
            )
            result = await self.session.execute(stmt)
            rows = list(result.scalars().all())
            return rows
        except Exception:
            logger.exception("Ошибка при получении строк отчета")
            raise

    async def get_all_rows(self, report_id: int) -> List[TableReportRow]:
        """
        Получение всех строк отчета с загрузкой связанных значений.

        Args:
            report_id (int): Идентификатор отчёта, строки которого нужно получить.

        Returns:
            List[TableReportRow]: Список всех строк отчета с загруженными значениями.
        """
        try:
            stmt = (
                select(TableReportRow)
                .where(
                    TableReportRow.report_id == report_id,
                    TableReportRow.is_deleted == False,  # noqa: E712
                )
                .options(selectinload(TableReportRow.values))
            )
            result = await self.session.execute(stmt)
            rows = list(result.scalars().all())
            return rows
        except Exception:
            logger.exception("Ошибка при получении всех строк отчета")
            raise

    async def get_rows_by_unique_value(self, report_id: int, unique_values: List[str]) -> List[TableReportRow]:
        """
        Получение строк отчета по списку уникальных значений.

        Args:
            report_id (int): Идентификатор отчёта, строки которого нужно получить.
            unique_values (List[str]): Список значений уникального столбца.

        Returns:
            List[TableReportRow]: Список строк отчета с загруженными значениями.
        """
        if not unique_values:
            return []

        try:
            stmt = (
                select(TableReportRow)
                .where(
                    TableReportRow.report_id == report_id,
                    TableReportRow.unique_value.in_(unique_values),
                    TableReportRow.is_deleted == False,  # noqa: E712
                )
                .options(selectinload(TableReportRow.values))
            )
            result = await self.session.execute(stmt)
            rows = list(result.scalars().all())
            return rows
        except Exception:
            logger.exception("Ошибка при получении строк по уникальным значениям")
            raise

    async def get_row_values(self, row_id: int) -> Dict[str, Any]:
        """
        Получение всех значений строки в виде словаря {column_name: value}.

        Args:
            row_id (int): Идентификатор строки, значения которой нужно получить.

        Returns:
            Dict[str, Any]: Список значений строки.
        """
        try:
            stmt = select(TableReportValue).where(TableReportValue.row_id == row_id)
            result = await self.session.execute(stmt)
            return {v.column_name: v.value for v in result.scalars().all()}
        except Exception:
            logger.exception("Ошибка при получении значений строки")
            raise

    async def get_column_values(self, report_id: int, column_name: str) -> List[Any]:
        """
        Получение всех значений столбца.

        Args:
            report_id (int): Идентификатор отчёта, где находится колонка.
            column_name (str): Название колонки из которой нужно получить значения.
        Returns:
            List[Any]: Значения столбца.
        """
        try:
            stmt = (
                select(TableReportValue.value)
                .join(TableReportRow)
                .where(
                    TableReportRow.report_id == report_id,
                    TableReportRow.is_deleted == False,  # noqa: E712
                    TableReportValue.column_name == column_name,
                )
            )
            result = await self.session.execute(stmt)
            return [row[0] for row in result.all()]
        except Exception:
            logger.exception("Ошибка при получении значений столбца")
            raise

    async def replace_rows(
        self, report_id: int, rows: List[Dict[str, Any]], unique_column: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Полная замена строк отчета. Возвращает (новые, обновленные, удаленные).

        Args:
            report_id (int): Идентификатор отчёта, строки которого нужно заменить.
            rows (List[Dict[str, Any]]): Список строк.
            unique_column (str): Имя столбца для определения уникальности строки.
        Returns:
            Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]: Кортеж из new, updated, deleted
        """
        new_rows, updated_rows, deleted_rows = [], [], []

        try:
            existing_rows_stmt = (
                select(TableReportRow)
                .where(TableReportRow.report_id == report_id, TableReportRow.is_deleted == False)  # noqa: E712
                .options(selectinload(TableReportRow.values))
            )
            result = await self.session.execute(existing_rows_stmt)
            existing_rows = result.scalars().all()

            existing_map = {r.unique_value: r for r in existing_rows}
            incoming_map = {r[unique_column]: r for r in rows}

            for key, row_data in incoming_map.items():
                if key in existing_map:
                    existing_row = existing_map[key]
                    for col, val in row_data.items():
                        existing_row_val = next((v for v in existing_row.values if v.column_name == col), None)
                        if existing_row_val:
                            existing_row_val.value = str(val)
                        else:
                            existing_row.values.append(TableReportValue(column_name=col, value=val))
                    updated_rows.append({"id": existing_row.id, **row_data})
                else:
                    new_row = TableReportRow(report_id=report_id, unique_value=row_data[unique_column])
                    new_row.values = [TableReportValue(column_name=k, value=str(v)) for k, v in row_data.items()]
                    self.session.add(new_row)
                    await self.session.flush()
                    new_rows.append({"id": new_row.id, **row_data})

            for key, existing_row in existing_map.items():
                if key not in incoming_map:
                    existing_row.is_deleted = True
                    deleted_rows.append({"unique_value": key})

            await self.session.commit()
            return new_rows, updated_rows, deleted_rows

        except Exception:
            await self.session.rollback()
            logger.exception("Ошибка при полной замене строк")
            raise

    async def append_rows(self, report_id: int, rows: List[Dict[str, Any]], unique_column: str) -> List[Dict[str, Any]]:
        """
        Дозапись строк отчета. Возвращает только новые строки.

        Args:
            report_id (int): Идентификатор отчёта, который нужно дозаписать.
            rows (List[Dict[str, Any]]): Список строк.
            unique_column (str): Имя столбца для определения уникальности строки.
        Returns:
            List[Dict[str, Any]]: Список новых строк.
        """
        new_rows = []
        try:
            existing_rows_stmt = select(TableReportRow.unique_value).where(
                TableReportRow.report_id == report_id, TableReportRow.is_deleted == False  # noqa: E712
            )
            result = await self.session.execute(existing_rows_stmt)
            existing_keys = {r[0] for r in result.all()}

            for row_data in rows:
                key = row_data[unique_column]
                if key not in existing_keys:
                    new_row = TableReportRow(report_id=report_id, unique_value=key)
                    new_row.values = [TableReportValue(column_name=k, value=str(v)) for k, v in row_data.items()]
                    self.session.add(new_row)
                    await self.session.flush()
                    new_rows.append({"id": new_row.id, **row_data})

            await self.session.commit()
            return new_rows
        except Exception:
            await self.session.rollback()
            logger.exception("Ошибка при добавлении строк")
            raise

    async def update_row_values(self, row_id: int, values: Dict[str, Any]) -> None:
        """
        Обновление значений строки.

        Args:
            row_id (List[Dict[str, Any]]): Идентификатор строки, значения которой нужно обновить.
            values (Dict[str, Any]): Новые значения строки.
        Returns:
            None
        """
        try:
            row = await self.session.get(TableReportRow, row_id)
            if not row:
                return
            for col, val in values.items():
                existing_val = next((v for v in row.values if v.column_name == col), None)
                if existing_val:
                    existing_val.value = val
                else:
                    row.values.append(TableReportValue(column_name=col, value=val))
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            logger.exception("Ошибка при обновлении значений строки")
            raise

    async def count_rows(self, report_id: int) -> int:
        """
        Подсчет количества строк отчета.

        Args:
            report_id (int): Идентификатор отчёта, количество строк которого нужно получить.
        Returns:
            int: Количество строк отчета.
        """
        try:
            stmt = (
                select(func.count())
                .select_from(TableReportRow)
                .where(TableReportRow.report_id == report_id, TableReportRow.is_deleted == False)  # noqa: E712
            )
            result = await self.session.execute(stmt)
            return result.scalar_one()
        except Exception:
            logger.exception("Ошибка при подсчете строк")
            raise

    async def count_empty_values(self, report_id: int, column_name: str) -> int:
        """
        Подсчет пустых значений в столбце.

        Args:
            report_id (int): Идентификатор отчёта для поиска колонки.
            column_name (str): Название колонки, количество пустых строк которой нужно получить.
        Returns:
            int: Количество пустых значений колонки отчета.
        """
        try:
            stmt = (
                select(func.count())
                .select_from(TableReportValue)
                .join(TableReportRow, TableReportValue.row_id == TableReportRow.id)
                .where(
                    TableReportRow.report_id == report_id,
                    TableReportRow.is_deleted == False,  # noqa: E712
                    (TableReportValue.value == ""),  # noqa: E711
                    TableReportValue.column_name == column_name,
                )
            )
            result = await self.session.execute(stmt)
            return result.scalar_one()
        except Exception:
            logger.exception("Ошибка при подсчете пустых значений")
            raise

    async def count_unique_values(self, report_id: int, column_name: str) -> int:
        """Подсчет уникальных значений столбца.

        Args:
            report_id (int): Идентификатор отчёта для поиска колонки.
            column_name (str): Название колонки, у которой нужно получить количество уникальных значений.
        Returns:
            int: Количество уникальных значений колонки отчета.
        """
        try:
            stmt = (
                select(func.count(func.distinct(TableReportValue.value)))
                .join(TableReportRow)
                .where(
                    TableReportRow.report_id == report_id,
                    TableReportRow.is_deleted == False,  # noqa: E712
                    TableReportValue.column_name == column_name,
                )
            )
            result = await self.session.execute(stmt)
            return result.scalar_one()
        except Exception:
            logger.exception("Ошибка при подсчете уникальных значений")
            raise

    async def list_reports(self, user_id: Optional[str], limit: int, offset: int) -> List[TableReport]:
        """Список отчетов с фильтрацией по пользователю.

        Args:
            user_id (Optional[str]): Идентификатор пользователя, отчёта которого нужно получить (опционально).
            limit (int): Максимальное количество отчетов для выборки.
            offset (int): Смещение для пагинации.
        Returns:
            List[TableReport]: Список отчетов.
        """
        try:
            stmt = select(TableReport).limit(limit).offset(offset)
            if user_id:
                stmt = stmt.where(TableReport.user_id == user_id)
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception:
            logger.exception("Ошибка при получении списка отчетов")
            raise
