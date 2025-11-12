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
        Обновляет поля отчёта по его ID и возвращает обновлённую сущность.

        Args:
            report (TableReport): Отчёта, который нужно обновить.
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
                .where(TableReportRow.report_id == report_id)
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

