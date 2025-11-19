#!/bin/sh
set -e

echo "Ожидание готовности PostgreSQL (db:5432)..."

wait-for-it db:5432 --timeout=60 --strict -- echo "PostgreSQL готова ✓"

echo "Применение миграций Alembic..."
poetry run alembic upgrade head

echo "Запуск Uvicorn..."
exec poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 "$@"