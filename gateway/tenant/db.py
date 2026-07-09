"""Database connection pool and session management for multi-tenant registry."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from gateway.tenant.models import Base

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_db(database_url: str, echo: bool = False) -> None:
    """Initialize the async engine and session factory."""
    global _engine, _session_factory

    if not database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    _engine = create_async_engine(
        database_url,
        echo=echo,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def get_session() -> AsyncSession:
    """Return a new async session from the pool."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized — call init_db() first")
    return _session_factory()


async def run_migrations() -> None:
    """Create all tables (dev/bootstrap convenience). Use alembic for production."""
    if _engine is None:
        raise RuntimeError("Database not initialized — call init_db() first")
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose the engine and release connections."""
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None


def get_session_factory() -> async_sessionmaker[AsyncSession] | None:
    """Return the session factory for use with UserRegistry."""
    return _session_factory
