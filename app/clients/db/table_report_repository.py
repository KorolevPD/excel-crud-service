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
        logger.info(
            "Начало создания отчета.",
            extra={
                "operation": "create",
                "report_id": report.id,
            },
        )
        try:
            self.session.add(report)
            await self.session.commit()
            await self.session.refresh(report)
            logger.info(
                "Отчет успешно создан.",
                extra={
                    "operation": "create",
                    "report_id": report.id,
                },
            )
            return report

        except Exception as e:
            await self.session.rollback()
            logger.exception(
                "Ошибка создания отчета.",
                extra={
                    "operation": "create",
                    "report_id": report.id,
                    "error_type": type(e).__name__,
                },
            )
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
        logger.info(
            "Получение отчета.",
            extra={
                "operation": "get_by_id",
                "report_id": report_id,
            },
        )
        try:
            result = await self.session.execute(select(TableReport).where(TableReport.id == report_id))
            logger.info(
                "Результат получен.",
                extra={
                    "operation": "get_by_id",
                    "report_id": report_id,
                },
            )
            return result.scalar_one_or_none()
        except Exception as e:
            await self.session.rollback()
            logger.exception(
                "Ошибка получения отчета.",
                extra={
                    "operation": "get_by_id",
                    "report_id": report_id,
                    "error_type": type(e).__name__,
                },
            )
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
        logger.info(
            "Обновление отчета.",
            extra={
                "operation": "update",
                "report_id": report.id,
            },
        )
        try:
            kwargs["updated_at"] = datetime.now(timezone.utc)
            for key, value in kwargs.items():
                setattr(report, key, value)

            await self.session.commit()
            await self.session.refresh(report)
            logger.info(
                "Отчет обновлен.",
                extra={
                    "operation": "update",
                    "report_id": report.id,
                },
            )
            return report

        except Exception as e:
            await self.session.rollback()
            logger.exception(
                "Ошибка обновления отчета.",
                extra={
                    "operation": "update",
                    "report_id": report.id,
                    "error_type": type(e).__name__,
                },
            )
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
        logger.info(
            "Удаление отчета.",
            extra={
                "operation": "delete",
                "report_id": report_id,
            },
        )
        try:
            stmt = sa_update(TableReportRow).where(TableReportRow.report_id == report_id).values(is_deleted=True)
            await self.session.execute(stmt)
            await self.session.commit()
            logger.info(
                "Отчет удален.",
                extra={
                    "operation": "delete",
                    "report_id": report_id,
                },
            )
        except Exception as e:
            await self.session.rollback()
            logger.exception(
                "Ошибка удаления отчета.",
                extra={
                    "operation": "delete",
                    "report_id": report_id,
                    "error_type": type(e).__name__,
                },
            )
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
        Raises:
            SQLAlchemyError: Если произошла ошибка на уровне базы данных(нарушение ограничений,
                потеря соединения и т.д).
            Exception: Любая другая непредвиденная ошибка.
        """
        logger.info(
            "Массовое создание строк.",
            extra={
                "operation": "create_rows",
                "report_id": report_id,
                "unique_column": unique_column,
            },
        )
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
            await self.update_report_total_rows(report_id)
            await self.session.commit()
            logger.info(
                "Строки созданы.",
                extra={
                    "operation": "create_rows",
                    "report_id": report_id,
                    "unique_column": unique_column,
                    "new_rows_count": len(new_rows),
                },
            )
        except Exception as e:
            await self.session.rollback()
            logger.exception(
                "Ошибка массового создания строк.",
                extra={
                    "operation": "create_rows",
                    "report_id": report_id,
                    "unique_column": unique_column,
                    "error_type": type(e).__name__,
                },
            )
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
        Raises:
            SQLAlchemyError: Если произошла ошибка на уровне базы данных(нарушение ограничений,
                потеря соединения и т.д).
            Exception: Любая другая непредвиденная ошибка.
        """
        logger.info(
            "Получение строк отчета с пагинацией.",
            extra={
                "operation": "get_rows",
                "report_id": report_id,
                "limit": limit,
                "offset": offset,
            },
        )
        try:
            stmt = (
                select(TableReportRow)
                .where(TableReportRow.report_id == report_id, TableReportRow.is_deleted == False)  # noqa: E712
                .options(selectinload(TableReportRow.values))
                .limit(limit)
                .offset(offset)
            )
            result = await self.session.execute(stmt)
            rows = list(result.scalars().all())
            logger.info(
                "Строки отчета получены.",
                extra={
                    "operation": "get_rows",
                    "report_id": report_id,
                    "limit": limit,
                    "offset": offset,
                    "rows_count": len(result.all()),
                },
            )
            return rows
        except Exception as e:
            await self.session.rollback()
            logger.exception(
                "Ошибка получения строк отчета.",
                extra={
                    "operation": "get_rows",
                    "report_id": report_id,
                    "limit": limit,
                    "offset": offset,
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def get_all_rows(self, report_id: int) -> List[TableReportRow]:
        """
        Получение всех строк отчета с загрузкой связанных значений.
        Args:
            report_id (int): Идентификатор отчёта, строки которого нужно получить.
        Returns:
            List[TableReportRow]: Список всех строк отчета с загруженными значениями.
        Raises:
            SQLAlchemyError: Если произошла ошибка на уровне базы данных(нарушение ограничений,
                потеря соединения и т.д).
            Exception: Любая другая непредвиденная ошибка.
        """
        logger.info(
            "Получение всех строк отчета с загрузкой связанных значений.",
            extra={
                "operation": "get_all_rows",
                "report_id": report_id,
            },
        )
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
            logger.info(
                "Строки отчета получены.",
                extra={
                    "operation": "get_all_rows",
                    "report_id": report_id,
                    "rows_count": len(rows),
                },
            )
            return rows
        except Exception as e:
            await self.session.rollback()
            logger.exception(
                "Ошибка получения всех строк отчета.",
                extra={
                    "operation": "get_all_rows",
                    "report_id": report_id,
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def get_rows_by_unique_value(self, report_id: int, unique_values: List[str]) -> List[TableReportRow]:
        """
        Получение строк отчета по списку уникальных значений.
        Args:
            report_id (int): Идентификатор отчёта, строки которого нужно получить.
            unique_values (List[str]): Список значений уникального столбца.
        Returns:
            List[TableReportRow]: Список строк отчета с загруженными значениями.
        Raises:
            SQLAlchemyError: Если произошла ошибка на уровне базы данных(нарушение ограничений,
                потеря соединения и т.д).
            Exception: Любая другая непредвиденная ошибка.
        """
        logger.info(
            "Получение строк отчета по списку уникальных значений.",
            extra={
                "operation": "get_rows_by_unique_value",
                "report_id": report_id,
            },
        )
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
            logger.info(
                "Строки отчета по уникальным значениям получены.",
                extra={
                    "operation": "get_rows_by_unique_value",
                    "report_id": report_id,
                    "rows_count": len(result.all()),
                },
            )
            return rows
        except Exception as e:
            await self.session.rollback()
            logger.exception(
                "Ошибка получения строк по уникальным значениям.",
                extra={
                    "operation": "get_rows_by_unique_value",
                    "report_id": report_id,
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def get_row_values(self, row_id: int) -> Dict[str, Any]:
        """
        Получение всех значений строки в виде словаря {column_name: value}.
        Args:
            row_id (int): Идентификатор строки, значения которой нужно получить.
        Returns:
            Dict[str, Any]: Список значений строки.
        Raises:
            SQLAlchemyError: Если произошла ошибка на уровне базы данных(нарушение ограничений,
                потеря соединения и т.д).
            Exception: Любая другая непредвиденная ошибка.
        """
        logger.info(
            "Получение значений строки.",
            extra={
                "operation": "get_row_values",
                "row_id": row_id,
            },
        )
        try:
            stmt = select(TableReportValue).where(TableReportValue.row_id == row_id)
            result = await self.session.execute(stmt)
            values = result.scalars().all()
            logger.info(
                "Значения строки получены.",
                extra={
                    "operation": "get_row_values",
                    "row_id": row_id,
                    "values_count": len(values),
                },
            )
            return {v.column_name: v.value for v in values}
        except Exception as e:
            await self.session.rollback()
            logger.exception(
                "Ошибка получениия значений строки.",
                extra={
                    "operation": "get_row_values",
                    "row_id": row_id,
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def get_column_values(self, report_id: int, column_name: str) -> List[Any]:
        """
        Получение всех значений столбца.
        Args:
            report_id (int): Идентификатор отчёта, где находится колонка.
            column_name (str): Название колонки из которой нужно получить значения.
        Returns:
            List[Any]: Значения столбца.
        Raises:
            SQLAlchemyError: Если произошла ошибка на уровне базы данных(нарушение ограничений,
                потеря соединения и т.д).
            Exception: Любая другая непредвиденная ошибка.
        """
        logger.info(
            "Получение значений столбца.",
            extra={
                "operation": "get_column_values",
                "report_id": report_id,
                "column_name": column_name,
            },
        )
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
            values = result.all()
            logger.info(
                "Значения столбца получены.",
                extra={
                    "operation": "get_column_values",
                    "report_id": report_id,
                    "column_name": column_name,
                    "values_count": len(values),
                },
            )
            return [row[0] for row in values]
        except Exception as e:
            await self.session.rollback()
            logger.exception(
                "Ошибка получения значений столбца.",
                extra={
                    "operation": "get_column_values",
                    "report_id": report_id,
                    "column_name": column_name,
                    "error_type": type(e).__name__,
                },
            )
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
        Raises:
            SQLAlchemyError: Если произошла ошибка на уровне базы данных(нарушение ограничений,
                потеря соединения и т.д).
            Exception: Любая другая непредвиденная ошибка.
        """
        logger.info(
            "Замена строк отчета.",
            extra={
                "operation": "replace_rows",
                "report_id": report_id,
                "unique_column": unique_column,
            },
        )
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

            await self.update_report_total_rows(report_id)
            await self.session.commit()
            logger.info(
                "Строки отчета заменены.",
                extra={
                    "operation": "replace_rows",
                    "report_id": report_id,
                    "unique_column": unique_column,
                    "new_rows": new_rows,
                    "updated_rows": updated_rows,
                    "deleted_rows": deleted_rows,
                },
            )
            return new_rows, updated_rows, deleted_rows

        except Exception as e:
            await self.session.rollback()
            logger.exception(
                "Ошибка полной замены строк.",
                extra={
                    "operation": "replace_rows",
                    "report_id": report_id,
                    "unique_column": unique_column,
                    "error_type": type(e).__name__,
                },
            )
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
        Raises:
            SQLAlchemyError: Если произошла ошибка на уровне базы данных(нарушение ограничений,
                потеря соединения и т.д).
            Exception: Любая другая непредвиденная ошибка.
        """
        logger.info(
            "Дозаписи строк отчета.",
            extra={
                "operation": "append_rows",
                "report_id": report_id,
                "unique_column": unique_column,
            },
        )
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

            await self.update_report_total_rows(report_id)
            await self.session.commit()
            logger.info(
                "Строки отчета дозаписаны.",
                extra={
                    "operation": "append_rows",
                    "report_id": report_id,
                    "new_rows": len(new_rows),
                },
            )
            return new_rows
        except Exception as e:
            await self.session.rollback()
            logger.exception(
                "Ошибка добавления строк.",
                extra={
                    "operation": "append_rows",
                    "report_id": report_id,
                    "unique_column": unique_column,
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def update_row_values(self, row_id: int, values: Dict[str, Any]) -> None:
        """
        Обновление значений строки.
        Args:
            row_id (List[Dict[str, Any]]): Идентификатор строки, значения которой нужно обновить.
            values (Dict[str, Any]): Новые значения строки.
        Returns:
            None
        Raises:
            SQLAlchemyError: Если произошла ошибка на уровне базы данных(нарушение ограничений,
                потеря соединения и т.д).
            Exception: Любая другая непредвиденная ошибка.
        """
        logger.info(
            "Обновление значений строки.",
            extra={
                "operation": "update_row_values",
                "row_id": row_id,
            },
        )
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
            logger.info(
                "Значений строки обновлено.",
                extra={
                    "operation": "update_row_values",
                    "row_id": row_id,
                },
            )
        except Exception as e:
            await self.session.rollback()
            logger.exception(
                "Ошибка обновления значений строки.",
                extra={
                    "operation": "update_row_values",
                    "row_id": row_id,
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def count_rows(self, report_id: int) -> int:
        """
        Подсчет количества строк отчета.
        Args:
            report_id (int): Идентификатор отчёта, количество строк которого нужно получить.
        Returns:
            int: Количество строк отчета.
        Raises:
            SQLAlchemyError: Если произошла ошибка на уровне базы данных(нарушение ограничений,
                потеря соединения и т.д).
            Exception: Любая другая непредвиденная ошибка.
        """
        logger.info(
            "Подсчет количества строк отчета.",
            extra={
                "operation": "count_rows",
                "report_id": report_id,
            },
        )
        try:
            stmt = (
                select(func.count())
                .select_from(TableReportRow)
                .where(TableReportRow.report_id == report_id, TableReportRow.is_deleted == False)  # noqa: E712
            )
            result = await self.session.execute(stmt)
            rows_count = result.scalar_one()
            logger.info(
                "Количество строк отчета получено.",
                extra={
                    "operation": "count_rows",
                    "report_id": report_id,
                    "rows_count": rows_count,
                },
            )
            return rows_count
        except Exception as e:
            await self.session.rollback()
            logger.exception(
                "Ошибка подсчета строк.",
                extra={
                    "operation": "count_rows",
                    "report_id": report_id,
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def count_empty_values(self, report_id: int, column_name: str) -> int:
        """
        Подсчет пустых значений в столбце.
        Args:
            report_id (int): Идентификатор отчёта для поиска колонки.
            column_name (str): Название колонки, количество пустых строк которой нужно получить.
        Returns:
            int: Количество пустых значений колонки отчета.
        Raises:
            SQLAlchemyError: Если произошла ошибка на уровне базы данных(нарушение ограничений,
                потеря соединения и т.д).
            Exception: Любая другая непредвиденная ошибка.
        """
        logger.info(
            "Подсчет пустых значений в столбце.",
            extra={
                "operation": "count_empty_values",
                "report_id": report_id,
                "column_name": column_name,
            },
        )
        try:
            stmt = (
                select(func.count())
                .select_from(TableReportValue)
                .join(TableReportRow, TableReportValue.row_id == TableReportRow.id)
                .where(
                    TableReportRow.report_id == report_id,
                    TableReportRow.is_deleted == False,  # noqa: E712
                    TableReportValue.value == "",  # noqa: E711
                    TableReportValue.column_name == column_name,
                )
            )
            result = await self.session.execute(stmt)
            empty_rows = result.scalar_one()
            logger.info(
                "Пустые значения в столбце посчитаны.",
                extra={
                    "operation": "count_empty_values",
                    "report_id": report_id,
                    "column_name": column_name,
                    "empty_rows": empty_rows,
                },
            )
            return empty_rows
        except Exception as e:
            await self.session.rollback()
            logger.exception(
                "Ошибка подсчета пустых значений.",
                extra={
                    "operation": "count_empty_values",
                    "report_id": report_id,
                    "column_name": column_name,
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def count_unique_values(self, report_id: int, column_name: str) -> int:
        """
        Подсчет уникальных значений столбца.
        Args:
            report_id (int): Идентификатор отчёта для поиска колонки.
            column_name (str): Название колонки, у которой нужно получить количество уникальных значений.
        Returns:
            int: Количество уникальных значений колонки отчета.
        Raises:
            SQLAlchemyError: Если произошла ошибка на уровне базы данных(нарушение ограничений,
                потеря соединения и т.д).
            Exception: Любая другая непредвиденная ошибка.
        """
        logger.info(
            "Подсчет уникальных значений столбца.",
            extra={
                "operation": "count_unique_values",
                "report_id": report_id,
                "column_name": column_name,
            },
        )
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
            unique_values = result.scalar_one()
            logger.info(
                "Уникальные значения столбца получены.",
                extra={
                    "operation": "count_unique_values",
                    "report_id": report_id,
                    "column_name": column_name,
                    "unique_values": unique_values,
                },
            )
            return unique_values
        except Exception as e:
            await self.session.rollback()
            logger.exception(
                "Ошибка подсчета уникальных значений.",
                extra={
                    "operation": "count_unique_values",
                    "report_id": report_id,
                    "column_name": column_name,
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def list_reports(self, user_id: Optional[str], limit: int, offset: int) -> List[TableReport]:
        """
        Список отчетов с фильтрацией по пользователю.
        Args:
            user_id (Optional[str]): Идентификатор пользователя, отчёта которого нужно получить (опционально).
            limit (int): Максимальное количество отчетов для выборки.
            offset (int): Смещение для пагинации.
        Returns:
            List[TableReport]: Список отчетов.
        Raises:
            SQLAlchemyError: Если произошла ошибка на уровне базы данных(нарушение ограничений,
                потеря соединения и т.д).
            Exception: Любая другая непредвиденная ошибка.
        """
        logger.info(
            "Получение списока отчетов с фильтрацией.",
            extra={
                "operation": "list_reports",
                "user_id": user_id,
                "limit": limit,
                "offset": offset,
            },
        )
        try:
            stmt = select(TableReport).limit(limit).offset(offset)
            if user_id:
                stmt = stmt.where(TableReport.user_id == user_id)
            result = await self.session.execute(stmt)
            rows = result.scalars().all()
            logger.info(
                "Список отчетов с фильтрацией получен.",
                extra={
                    "operation": "list_reports",
                    "user_id": user_id,
                    "rows_count": len(rows),
                },
            )
            return list(rows)
        except Exception as e:
            await self.session.rollback()
            logger.exception(
                "Ошибка получения списка отчетов.",
                extra={
                    "operation": "list_reports",
                    "user_id": user_id,
                    "limit": limit,
                    "offset": offset,
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def update_report_total_rows(self, report_id: int) -> None:
        """
        Обновление поля total_rows в отчете.
        Args:
            report_id (int): Идентификатор отчёта, для которого нужно обновить количество строк.
        Returns:
            None
        Raises:
            SQLAlchemyError: Если произошла ошибка на уровне базы данных(нарушение ограничений,
                потеря соединения и т.д).
            Exception: Любая другая непредвиденная ошибка.
        """
        logger.info(
            "Обновление поля total_rows в отчете.",
            extra={
                "operation": "update_report_total_rows",
                "report_id": report_id,
            },
        )
        try:
            report = await self.get_by_id(report_id)
            if not report:
                return
            total_rows = await self.count_rows(report_id)
            stmt = sa_update(TableReport).where(TableReport.id == report_id).values(total_rows=total_rows)
            await self.session.execute(stmt)
            await self.session.refresh(report)
            logger.info(
                "Поле total_rows обновлено.",
                extra={
                    "operation": "update_report_total_rows",
                    "report_id": report_id,
                    "total_rows": total_rows,
                },
            )
        except Exception as e:
            await self.session.rollback()
            logger.exception(
                "Ошибка обновления количества строк отчета.",
                extra={
                    "operation": "update_report_total_rows",
                    "report_id": report_id,
                    "error_type": type(e).__name__,
                },
            )
            raise
