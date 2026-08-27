# Excel CRUD Service

REST API решение, разработанное для компании [«Нейроэксперт»](https://neuroexp.ru/) для загрузки, хранения, обновления, анализа и выгрузки табличных отчетов из Excel-файлов.

## Описание

Сервис принимает файлы `.xlsx` и `.xls`, извлекает структуру колонок и строки, сохраняет данные в PostgreSQL и позволяет:

- создавать отчет из Excel-файла;
- получать метаданные отчета;
- получать данные отчета в JSON или Excel;
- обновлять отчет в режимах `replace` и `append`;
- удалять строки отчета через soft delete;
- получать статистику качества данных;
- получать список отчетов с фильтрацией по пользователю и пагинацией.

После локального запуска интерактивная документация API доступна по адресу:

```text
http://localhost:8000/docs
```

Базовый префикс API:

```text
/api/v1
```

## Архитектура

Проект построен как FastAPI-приложение с разделением на слои:

- `app/main.py` - точка входа приложения, настройка FastAPI, CORS и подключение роутеров.
- `app/api` - HTTP-слой: роуты, обработчики запросов и Pydantic-схемы.
- `app/use_cases/table_reports` - сценарии бизнес-операций: создание, обновление, получение, удаление и расчет статистики.
- `app/services` - сервисный слой с основной логикой работы с Excel и отчетами.
- `app/clients/db` - слой доступа к PostgreSQL: SQLAlchemy-модели, async-сессии и репозиторий.
- `app/config` - настройки приложения через Pydantic Settings.
- `alembic` - миграции базы данных.
- `tests` - unit- и integration-тесты.

Основной поток обработки запроса:

```text
HTTP request
  -> FastAPI router
  -> API handler
  -> Use case
  -> TableReportService
  -> TableReportRepository
  -> PostgreSQL
```

Данные отчетов хранятся в схеме `controller` в трех таблицах:

- `table_reports` - метаданные отчета: название, пользователь, шаблон, метаданные колонок, количество строк.
- `table_report_rows` - строки отчета с уникальным значением и флагом `is_deleted`.
- `table_report_values` - значения ячеек в EAV-формате: строка, имя колонки, значение.

Такой подход позволяет хранить отчеты с произвольным набором колонок без создания отдельной таблицы под каждый Excel-файл.

## Технологический стек

- Python 3.11
- FastAPI
- Uvicorn
- Pydantic 2
- Pydantic Settings
- SQLAlchemy 2
- AsyncPG
- Psycopg2
- PostgreSQL 15
- Alembic
- Pandas
- OpenPyXL
- Python Multipart
- Docker и Docker Compose
- Poetry
- Pytest
- Pytest Asyncio
- HTTPX
- Black, Isort, Flake8, Mypy

## Переменные окружения

Настройки описаны в `app/config/settings.py`.

| Переменная | Значение по умолчанию | Описание |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+psycopg2://postgres:postgres@db:5432/excel_crud` | Синхронный DSN PostgreSQL. Используется Alembic-миграциями. |
| `DATABASE_URL_ASYNC` | `postgresql+asyncpg://postgres:postgres@db:5432/excel_crud` | Асинхронный DSN PostgreSQL. Используется приложением через SQLAlchemy AsyncSession. |
| `MAX_ROWS_PER_BATCH` | `10000` | Размер батча при чтении Excel-файла. Минимальное допустимое значение: `5000`. |

При запуске через `docker-compose.yml` база данных создается со следующими параметрами:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=excel_crud
```

Для локального запуска без Docker обычно нужен DSN с хостом `localhost`, например:

```env
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/excel_crud
DATABASE_URL_ASYNC=postgresql+asyncpg://postgres:postgres@localhost:5432/excel_crud
MAX_ROWS_PER_BATCH=10000
```

## Бизнес-логика

### Создание отчета

Эндпоинт:

```http
POST /api/v1/table-reports
```

Сервис получает Excel-файл и параметры `name`, `user_id`, `unique_column`, опционально `template_id` и `additional_params`.

Логика:

- файл временно сохраняется на диск;
- проверяется расширение `.xlsx` или `.xls`;
- файл читается через `pandas` и `openpyxl`;
- извлекаются метаданные колонок: `integer`, `float`, `string`, `boolean`, `datetime` или `unknown`;
- проверяется, что колонка `unique_column` есть в Excel;
- создается запись отчета в `table_reports`;
- каждая строка сохраняется в `table_report_rows`;
- значения ячеек сохраняются в `table_report_values`;
- пустые значения приводятся к пустой строке, остальные значения сохраняются как текст.

### Получение отчета

Метаданные отчета:

```http
GET /api/v1/table-reports/{report_id}
```

Данные отчета:

```http
GET /api/v1/table-reports/{report_id}/data?as_format=json&limit=50&offset=0
GET /api/v1/table-reports/{report_id}/data?as_format=excel
```

В формате `json` сервис возвращает метаданные отчета и строки с пагинацией. В формате `excel` сервис собирает строки обратно в Excel-файл и отдает его как attachment.

### Обновление отчета

Эндпоинт:

```http
PUT /api/v1/table-reports/{report_id}?update_mode=replace&unique_column=id
PUT /api/v1/table-reports/{report_id}?update_mode=append&unique_column=id
```

Поддерживаются два режима:

- `replace` - новый Excel-файл считается актуальной версией отчета. Сервис сравнивает старые и новые строки по `unique_column`, определяет новые, обновленные и удаленные строки, пересчитывает статистику качества и заменяет строки отчета.
- `append` - сервис добавляет только те строки, уникального значения которых еще нет в отчете.

### Удаление отчета

Эндпоинт:

```http
DELETE /api/v1/table-reports/{report_id}
```

Удаление реализовано как soft delete для строк отчета: у строк выставляется `is_deleted = true`. Такие строки не попадают в обычную выборку данных.

### Статистика качества данных

Эндпоинт:

```http
GET /api/v1/table-reports/{report_id}/quality-stats
```

Сервис возвращает:

- количество новых, обновленных и удаленных строк;
- количество пустых значений по каждой колонке;
- количество уникальных значений по каждой колонке.

### Список отчетов

Эндпоинт:

```http
GET /api/v1/table-reports?user_id=user-1&limit=50&offset=0
```

Возвращает список отчетов с опциональной фильтрацией по `user_id` и пагинацией.

## Локальный запуск

### Запуск через Docker Compose

Самый простой способ поднять приложение вместе с PostgreSQL:

```bash
docker compose up --build
```

Контейнер `web` при старте выполняет миграции:

```bash
alembic upgrade head
```

После запуска API будет доступно по адресу:

```text
http://localhost:8000
```

Swagger UI:

```text
http://localhost:8000/docs
```

### Запуск без Docker

Установите зависимости:

```bash
poetry install
```

Поднимите PostgreSQL и задайте переменные окружения для локальной базы:

```bash
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/excel_crud
DATABASE_URL_ASYNC=postgresql+asyncpg://postgres:postgres@localhost:5432/excel_crud
```

В PowerShell:

```powershell
$env:DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/excel_crud"
$env:DATABASE_URL_ASYNC = "postgresql+asyncpg://postgres:postgres@localhost:5432/excel_crud"
```

Примените миграции:

```bash
poetry run alembic upgrade head
```

Запустите приложение:

```bash
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Тесты и проверки

Запуск тестов:

```bash
poetry run pytest
```

Проверка типов:

```bash
poetry run mypy .
```

Форматирование и линтинг:

```bash
poetry run black .
poetry run isort .
poetry run flake8 .
```
