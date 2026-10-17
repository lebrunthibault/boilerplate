"""Test fixtures: in-memory SQLite database, HTTP client, authenticated admins."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

# Register ORM models with Base.metadata before create_all
import api.infra.db.models  # noqa: F401
from api.app.auth import hash_password
from api.infra.db import Base, get_session
from api.infra.db.models import Admin
from api.main import app

# ---------------------------------------------------------------------------
# SQLite compatibility for PostgreSQL-specific column types
# ---------------------------------------------------------------------------


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(PG_UUID, "sqlite")
def _compile_uuid_sqlite(type_, compiler, **kw):
    return "VARCHAR(36)"


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db_engine():
    """In-memory SQLite engine with all tables created."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Async session bound to the test database."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTPX async test client with DB dependency overridden."""

    async def _override() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_session] = _override

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Authenticated admin client
# ---------------------------------------------------------------------------

# Les tests construisent le schéma via ``create_all`` (les migrations ne rejouent pas) et
# aucune migration ne seede de compte : on les crée ici — et il en faut bien **deux**, le
# fan-out des notifications ne vise que « l'autre » admin.
ADMIN_EMAIL = "admin@example.com"
OTHER_ADMIN_EMAIL = "other@example.com"
ADMIN_PASSWORD = "correct horse battery staple"

# Argon2 coûte ~50-100 ms : on hache une fois pour toute la session de tests.
_ADMIN_PASSWORD_HASH = hash_password(ADMIN_PASSWORD)


@dataclass(frozen=True)
class SeededAdmins:
    """Les deux comptes admin d'un test, et le client connecté sur le premier."""

    client: AsyncClient
    me: Admin
    other: Admin


async def login_as(client: AsyncClient, email: str) -> None:
    """Ouvre une vraie session (cookie posé par /auth/login).

    On ne peut pas court-circuiter par ``dependency_overrides[get_current_user]`` : les
    overrides sont indexés par callable, le ``Depends(get_current_session)`` déclaré sur les
    endpoints se résoudrait pour de vrai (401) — et ne fournirait aucun ``admin_id``.
    """
    resp = await client.post("/api/auth/login", json={"email": email, "password": ADMIN_PASSWORD})
    assert resp.status_code == 200, resp.text


@pytest_asyncio.fixture
async def admins(client: AsyncClient, db_session: AsyncSession) -> SeededAdmins:
    """Deux admins actifs, session ouverte sur le premier."""
    me = Admin(email=ADMIN_EMAIL, display_name="Alice", password_hash=_ADMIN_PASSWORD_HASH)
    other = Admin(email=OTHER_ADMIN_EMAIL, display_name="Bob", password_hash=_ADMIN_PASSWORD_HASH)
    db_session.add_all([me, other])
    await db_session.commit()
    await login_as(client, ADMIN_EMAIL)
    return SeededAdmins(client, me, other)


@pytest_asyncio.fixture
async def admin_client(admins: SeededAdmins) -> AsyncClient:
    """Client HTTP authentifié comme admin — le passe-partout des routes admin."""
    return admins.client
