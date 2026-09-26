from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from .config import get_settings
from .models import Base

settings = get_settings()

database_url = str(settings.database_url)
use_sqlite = database_url.startswith("sqlite")
# REMOVE postgresql->sqlite override in development; honor DATABASE_URL as-is.
# Only default to sqlite when DATABASE_URL is unset (handled by Settings default).
if "sqlite" in database_url:
    engine = create_async_engine(
        database_url,
        echo=False,
        poolclass=NullPool,
        connect_args={"check_same_thread": False},
    )

    from sqlalchemy import event

    @event.listens_for(engine.sync_engine, "connect")
    def _register_sqlite_functions(dbapi_connection, connection_record):
        import datetime

        try:
            dbapi_connection.create_function(
                "now", 0, lambda: datetime.datetime.utcnow().isoformat()
            )
        except Exception:
            pass
else:
    engine = create_async_engine(
        database_url,
        echo=settings.is_development,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
    )

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    await engine.dispose()


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a session and commit on clean exit.

    Read-only callers must not rely on auto-commit; commit explicitly
    where a write is intended.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with get_session() as session:
        yield session
