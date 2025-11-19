from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config.settings import settings

async_engine = create_async_engine(settings.DATABASE_URL_ASYNC, echo=False, future=True)

async_session_maker = async_sessionmaker(async_engine, expire_on_commit=False)

session = async_session_maker(bind=async_engine)
