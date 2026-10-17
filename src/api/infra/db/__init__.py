"""Database engine, session and base model."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from api.infra.config import DbPool

_raw_url = os.environ.get("DATABASE_URL", "")
if _raw_url.startswith("postgresql://"):
    DATABASE_URL = _raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif _raw_url.startswith("postgres://"):
    DATABASE_URL = _raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
else:
    DATABASE_URL = _raw_url

engine = (
    create_async_engine(
        DATABASE_URL,
        pool_size=DbPool.SIZE,
        max_overflow=DbPool.MAX_OVERFLOW,
        pool_recycle=DbPool.RECYCLE_S,
        pool_pre_ping=True,
        pool_timeout=DbPool.CHECKOUT_TIMEOUT_S,
        connect_args={
            "timeout": DbPool.CONNECT_TIMEOUT_S,
            "server_settings": {"statement_timeout": str(DbPool.STATEMENT_TIMEOUT_MS)},
        },
    )
    if DATABASE_URL
    else None
)

# Reserved for background work (retention loop, scripts) that must
# persist independently of the main request transaction.  Request-scoped DB
# work should use the session provided by get_session() / Depends(get_session).
_session_factory = async_sessionmaker(engine, expire_on_commit=False) if engine else None


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency yielding an async session."""
    if _session_factory is None:
        raise RuntimeError("DATABASE_URL is not configured")
    async with _session_factory() as session:
        yield session
