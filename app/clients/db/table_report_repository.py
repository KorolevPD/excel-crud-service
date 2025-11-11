import logging
from typing import Any, Optional

from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.db.table_report_model import TableReport, TableReportRow

logger = logging.getLogger(__name__)


class TableReportRepository:
    """Репозиторий для работы с табличными отчетами."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, report: TableReport) -> TableReport:
        """
        Создаёт новый табличный отчёт в базе данных.

        Args:
            report (TableReport): Объект отчёта для сохранения. Должен быть валидным и
                содержать все обязательные поля (name, user_id и т.д).

        Returns:
            TableReport: Сохранённый объект отчёта с установленным ``id`` и актуальными данными из БД.

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
            report_id (int): Уникальный идентификатор отчёта в базе данных.

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

    async def update(self, report_id: int, **kwargs: Any) -> TableReport:
        """
        Обновляет поля отчёта по его ID и возвращает обновлённую сущность.

        Args:
            report_id (int): Идентификатор отчёта, который нужно обновить.
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
            stmt = sa_update(TableReport).where(TableReport.id == report_id).values(**kwargs).returning(TableReport)
            result = await self.session.execute(stmt)
            updated = result.scalar_one()

            await self.session.commit()
            return updated

        except Exception:
            await self.session.rollback()
            logger.exception("Ошибка при обновлении отчета")
            raise

    async def delete(self, report_id: int) -> None:
        """
        Удаляет отчет (помечает все его строки, как удаленные).

        Устанавливает флаг "is_deleted" = True. Физически строки не удаляются.

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
