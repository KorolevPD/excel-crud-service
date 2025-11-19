"""
Создание таблиц табличных отчётов

Revision ID: 011
Revises: 010_create_reports_table
Create Date: 2025-11-10 16:52:03.000453

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "011_create_table_reports"
down_revision: Union[str, Sequence[str], None] = None  # "010_create_reports_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Создаёт таблицы table_reports, table_report_rows и table_report_values в схеме controller"""

    schema = "controller"

    op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

    op.create_table(
        "table_reports",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=True),
        sa.Column("columns_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("total_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("additional_params", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema=schema,
    )

    op.create_table(
        "table_report_rows",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "report_id",
            sa.Integer(),
            sa.ForeignKey(f"{schema}.table_reports.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("unique_value", sa.String(length=255), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.false(), nullable=False, index=True),
        sa.UniqueConstraint("report_id", "unique_value", name="uq_table_report_rows_report_id_unique_value"),
        schema=schema,
    )

    op.create_table(
        "table_report_values",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "row_id",
            sa.Integer(),
            sa.ForeignKey(f"{schema}.table_report_rows.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("column_name", sa.String(length=100), nullable=False, index=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("row_id", "column_name", name="uq_table_report_values_row_id_column_name"),
        schema=schema,
    )

    op.create_index(
        "ix_controller_table_report_values_row_id_column_name",
        "table_report_values",
        ["row_id", "column_name"],
        unique=True,
        schema=schema,
    )


def downgrade() -> None:
    """Удаляет таблицы table_report_values, table_report_rows и table_reports из схемы controller."""

    schema = "controller"

    op.drop_table("table_report_values", if_exists=True, schema=schema)
    op.drop_table("table_report_rows", if_exists=True, schema=schema)
    op.drop_table("table_reports", if_exists=True, schema=schema)
