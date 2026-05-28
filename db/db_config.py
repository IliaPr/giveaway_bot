import contextlib
import os
from typing import AsyncIterator, Optional

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
    AsyncConnection,
    AsyncSession,
)
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()


def _require_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return _normalize_database_url(database_url)

    db_user = _require_env("DB_USER")
    db_password = _require_env("DB_PASSWORD")
    db_host = _require_env("DB_HOST")
    db_port = _require_env("DB_PORT")
    db_name = _require_env("DB_NAME")
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if value:
        return value
    raise RuntimeError(f"Environment variable {name} is required.")


def _normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql://", 1)
    return database_url


def _to_sync_dsn(database_url: str) -> str:
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    if database_url.startswith("postgresql://"):
        return database_url
    raise RuntimeError(
        "DATABASE_URL must start with postgresql:// or postgresql+asyncpg://")


def _to_async_dsn(database_url: str) -> str:
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    raise RuntimeError(
        "DATABASE_URL must start with postgresql:// or postgresql+asyncpg://")


class Config:
    SYNC_CONFIG = _to_sync_dsn(_require_database_url())
    DB_CONFIG = _to_async_dsn(SYNC_CONFIG)


config = Config

Base = declarative_base()


class DatabaseSessionManager:
    def __init__(self):
        self._engine: Optional[AsyncEngine] = None
        self._sessionmaker: Optional[async_sessionmaker] = None

    def init(self, host: str):
        self._engine = create_async_engine(host)
        self._sessionmaker = async_sessionmaker(
            autocommit=False, bind=self._engine)

    async def close(self):
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")
        await self._engine.dispose()
        self._engine = None
        self._sessionmaker = None

    @contextlib.asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncConnection]:
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")

        async with self._engine.begin() as connection:
            try:
                yield connection
            except Exception:
                await connection.rollback()
                raise

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if self._sessionmaker is None:
            raise Exception("DatabaseSessionManager is not initialized")

        session = self._sessionmaker()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


sessionmanager = DatabaseSessionManager()

engine = create_async_engine(config.DB_CONFIG)

sync_engine = create_engine(config.SYNC_CONFIG)
SyncSession = sessionmaker(bind=sync_engine)


async def get_db():
    async with sessionmanager.session() as session:
        yield session
