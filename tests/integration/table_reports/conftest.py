from asyncio import AbstractEventLoop, get_event_loop_policy
from collections.abc import AsyncGenerator, Generator

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.clients.db.models import ControllerBase
from app.clients.db.table_report_model import TableReport
from app.clients.db.table_report_repository import TableReportRepository
from app.config.settings import settings


@pytest.fixture(scope="session")
def event_loop() -> Generator[AbstractEventLoop, None]:
    loop = get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture()
async def async_engine() -> AsyncGenerator[AsyncEngine, None]:
    engine = create_async_engine(settings.DATABASE_URL_ASYNC, echo=False, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(ControllerBase.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture()
async def async_session(async_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    async_session_maker = async_sessionmaker(async_engine, expire_on_commit=False)

    async with async_engine.connect() as connection:
        transaction = await connection.begin()
        async with async_session_maker(bind=connection) as session:
            yield session
        await transaction.rollback()


@pytest.fixture
async def repo(async_session: AsyncSession) -> TableReportRepository:
    return TableReportRepository(async_session)


@pytest.fixture
async def table_report() -> TableReport:
    return TableReport(
        name="Report",
        user_id="user_1",
        columns_metadata={"col1": "string", "col2": "int"},
        total_rows=0,
    )
