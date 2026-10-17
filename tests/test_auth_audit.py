"""Journal d'authentification admin : chaque événement laisse une ligne.

Table ``admin_auth_event``, écrite par ``record_auth_event`` — qui commit lui-même (les
chemins d'échec lèvent une HTTPException juste après, la ligne partirait au rollback) et avale
sa propre panne (une écriture de journal cassée ne doit pas transformer une connexion valide
en 500).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from api.app.auth import (
    AuthEvent,
    AuthEventKind,
    LoginRateLimit,
    hash_password,
    purge_auth_events,
    record_auth_event,
)
from api.app.auth import rate_limit as rate_limit_module
from api.app.config import Retention
from api.infra.db.models import Admin, AdminAuthEvent

EMAIL = "admin@example.com"
PASSWORD = "correct horse battery staple"


@pytest.fixture(autouse=True)
def reset_rate_limit():
    rate_limit_module._failures.clear()
    yield
    rate_limit_module._failures.clear()


async def _seed_admin(db_session) -> Admin:
    admin = Admin(email=EMAIL, display_name="Alice", password_hash=hash_password(PASSWORD))
    db_session.add(admin)
    await db_session.commit()
    return admin


async def _events(db_session) -> list[AdminAuthEvent]:
    rows = await db_session.execute(select(AdminAuthEvent).order_by(AdminAuthEvent.id))
    return list(rows.scalars())


@pytest.mark.asyncio
async def test_login_success_is_journalled(client, db_session):
    admin = await _seed_admin(db_session)

    await client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})

    (event,) = await _events(db_session)
    assert event.kind == AuthEventKind.LOGIN_SUCCESS.value
    assert event.admin_id == admin.id
    assert event.email == EMAIL
    assert event.occurred_at is not None


@pytest.mark.asyncio
async def test_login_failure_is_journalled_without_an_account(client, db_session):
    """Une adresse inconnue n'a pas d'``admin_id`` : c'est ``email`` qui porte l'identité."""
    await client.post("/api/auth/login", json={"email": "ghost@example.com", "password": "x"})

    (event,) = await _events(db_session)
    assert event.kind == AuthEventKind.LOGIN_FAILURE.value
    assert event.admin_id is None
    assert event.email == "ghost@example.com"


@pytest.mark.asyncio
async def test_attempted_email_is_normalised(client, db_session):
    await client.post("/api/auth/login", json={"email": "  GHOST@Example.COM ", "password": "x"})

    (event,) = await _events(db_session)
    assert event.email == "ghost@example.com"


@pytest.mark.asyncio
async def test_throttle_is_journalled(client, db_session):
    await _seed_admin(db_session)

    for _ in range(LoginRateLimit.MAX_FAILURES + 1):
        await client.post("/api/auth/login", json={"email": EMAIL, "password": "wrong"})

    kinds = [event.kind for event in await _events(db_session)]
    assert kinds.count(AuthEventKind.LOGIN_FAILURE.value) == LoginRateLimit.MAX_FAILURES
    assert kinds[-1] == AuthEventKind.LOGIN_BLOCKED.value


@pytest.mark.asyncio
async def test_logout_names_the_account(client, db_session):
    """``revoke_session`` rend l'``admin_id`` : le logout ne dispose que du jeton brut."""
    admin = await _seed_admin(db_session)
    await client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})

    await client.post("/api/auth/logout")

    event = (await _events(db_session))[-1]
    assert event.kind == AuthEventKind.LOGOUT.value
    assert event.admin_id == admin.id


@pytest.mark.asyncio
async def test_logout_without_a_session_writes_nothing(client, db_session):
    await client.post("/api/auth/logout")

    assert await _events(db_session) == []


@pytest.mark.asyncio
async def test_client_ip_and_user_agent_are_kept(client, db_session):
    await _seed_admin(db_session)

    await client.post(
        "/api/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
        headers={"X-Real-IP": "203.0.113.7", "User-Agent": "Firefox/143"},
    )

    (event,) = await _events(db_session)
    assert event.ip == "203.0.113.7"
    assert event.user_agent == "Firefox/143"


@pytest.mark.asyncio
async def test_event_without_a_request_is_journalled(db_session):
    """``scripts/set_admin_password.py`` journalise hors requête HTTP : ni IP ni user-agent."""
    admin = await _seed_admin(db_session)

    await record_auth_event(
        db_session,
        None,
        AuthEvent(
            AuthEventKind.SESSIONS_REVOKED, email=EMAIL, admin_id=admin.id, detail="3 sessions"
        ),
    )

    (event,) = await _events(db_session)
    assert event.kind == AuthEventKind.SESSIONS_REVOKED.value
    assert event.ip is None and event.user_agent is None
    assert event.detail == "3 sessions"


@pytest.mark.asyncio
async def test_long_values_are_truncated(db_session):
    await record_auth_event(
        db_session,
        None,
        AuthEvent(AuthEventKind.LOGIN_FAILURE, email="a" * 400, detail="d" * 400),
    )

    (event,) = await _events(db_session)
    assert len(event.email) == 320
    assert len(event.detail) == 255


@pytest.mark.asyncio
async def test_a_broken_journal_does_not_break_the_login(client, db_session, monkeypatch):
    """Une panne d'écriture du journal ne doit pas transformer une connexion valide en 500.

    Le login commit deux fois : la session admin, puis le journal. Seul le second échoue ici.
    """
    await _seed_admin(db_session)
    business_commit = db_session.commit
    calls = {"n": 0}

    async def _flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            return await business_commit()
        raise OperationalError("INSERT", {}, Exception("disk full"))

    monkeypatch.setattr(db_session, "commit", _flaky)

    resp = await client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})

    assert resp.status_code == 200
    assert calls["n"] == 2  # le journal a bien été tenté


@pytest.mark.asyncio
async def test_a_failed_write_rolls_back_and_returns(db_session, monkeypatch):
    """``record_auth_event`` avale sa panne : il rollback et rend la main sans lever."""
    rolled: list[bool] = []

    async def _explode():
        raise OperationalError("INSERT", {}, Exception("disk full"))

    async def _rollback():
        rolled.append(True)

    monkeypatch.setattr(db_session, "commit", _explode)
    monkeypatch.setattr(db_session, "rollback", _rollback)

    await record_auth_event(db_session, None, AuthEvent(AuthEventKind.LOGIN_SUCCESS, email=EMAIL))

    assert rolled == [True]


@pytest.mark.asyncio
async def test_purge_drops_events_past_retention(db_session):
    old = datetime.now(UTC) - Retention.AUTH_EVENTS - timedelta(days=1)
    recent = datetime.now(UTC) - timedelta(days=1)
    db_session.add_all(
        [
            AdminAuthEvent(occurred_at=old, kind=AuthEventKind.LOGIN_SUCCESS.value),
            AdminAuthEvent(occurred_at=recent, kind=AuthEventKind.LOGIN_SUCCESS.value),
        ]
    )
    await db_session.commit()

    deleted = await purge_auth_events(db_session)

    assert deleted == 1
    assert len(await _events(db_session)) == 1


@pytest.mark.asyncio
async def test_events_are_readable_from_the_dashboard(admin_client, db_session):
    """``GET /auth/events`` : le plus récent d'abord, filtrable par type."""
    resp = await admin_client.get("/api/auth/events")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total"] == 1  # la connexion de la fixture
    assert payload["items"][0]["kind"] == AuthEventKind.LOGIN_SUCCESS.value

    filtered = await admin_client.get("/api/auth/events?kind=login_failure")
    assert filtered.json()["items"] == []


@pytest.mark.asyncio
async def test_a_logout_row_still_names_an_account(admin_client, db_session):
    """La déconnexion ne connaît que son ``admin_id`` : l'adresse est jointe à la lecture."""
    await admin_client.post("/api/auth/logout")

    rows = await db_session.execute(select(AdminAuthEvent).order_by(AdminAuthEvent.id))
    stored = list(rows.scalars())[-1]
    assert stored.kind == AuthEventKind.LOGOUT.value
    assert stored.email is None  # rien n'est copié dans la ligne

    # Mais l'écran affiche bien un compte (relecture après ré-authentification).
    await admin_client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    payload = (await admin_client.get("/api/auth/events?kind=logout")).json()
    assert payload["items"][0]["email"] == EMAIL


@pytest.mark.asyncio
async def test_the_journal_needs_a_session(client, db_session):
    resp = await client.get("/api/auth/events")

    assert resp.status_code == 401
