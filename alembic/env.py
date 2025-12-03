from app.config.settings import settings
from logging.config import fileConfig
from typing import Any, cast

from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

from alembic import context
from app.clients.db.models import ControllerBase

load_dotenv()

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
target_metadata = ControllerBase.metadata


def run_migrations_offline() -> None:
    """Запуск миграций в offline-режиме."""
    url = settings.DATABASE_URL

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Запуск миграций в online-режиме."""
    url = settings.DATABASE_URL

    section = config.get_section(config.config_ini_section)
    if section is None:
        section = {}

    connectable = engine_from_config(
        cast(dict[str, Any], section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        url=url,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
