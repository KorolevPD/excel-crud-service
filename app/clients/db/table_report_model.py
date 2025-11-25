from typing import Any, Dict, List

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import false, func

from app.clients.db.models import ControllerBase


class TableReport(ControllerBase):
    """Метаданные табличного отчёта."""

    __tablename__ = "table_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    template_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    columns_metadata: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    additional_params: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=True)

    rows: Mapped[List["TableReportRow"]] = relationship(
        "TableReportRow",
        back_populates="report",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<TableReport id={self.id} name={self.name}>"


class TableReportRow(ControllerBase):
    """Строка табличного отчёта с уникальным значением."""

    __tablename__ = "table_report_rows"
    __table_args__ = (
        UniqueConstraint("report_id", "unique_value", name="uq_table_report_rows_report_id_unique_value"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("controller.table_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    unique_value: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())

    report: Mapped[TableReport] = relationship("TableReport", back_populates="rows")
    values: Mapped[List["TableReportValue"]] = relationship(
        "TableReportValue",
        back_populates="row",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<TableReportRow id={self.id} unique_value={self.unique_value}>"


class TableReportValue(ControllerBase):
    """Значение ячейки в EAV модели: (row_id, column_name) -> value."""

    __tablename__ = "table_report_values"
    __table_args__ = (UniqueConstraint("row_id", "column_name", name="uq_table_report_values_row_id_column_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    row_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("controller.table_report_rows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    column_name: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    row: Mapped[TableReportRow] = relationship("TableReportRow", back_populates="values")

    def __repr__(self) -> str:
        return f"<TableReportValue row_id={self.row_id} column={self.column_name} value={self.value}>"
