"""Session admin révocable : la garde vérifie la ligne `admin_session` en base.

Une session morte (révoquée, inactive trop longtemps, plafond absolu atteint, compte
désactivé) doit produire un 401 propre — jamais une 500 — et un seul détail
(« Session expired ») pour ne rien apprendre au porteur d'un cookie révoqué.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from starlette.requests import Request

from api.app.auth import AuthConfig, create_session, get_current_session, revoke_all_sessions
from api.infra.db.models import Admin, AdminSession

EMAIL = "admin@example.com"


def _request(token: str | None) -> Request:
    headers = [(b"cookie", f"{AuthConfig.COOKIE_NAME}={token}".encode())] if token else []
    return Request({"type": "http", "headers": headers})


async def _seed_session(db_session, is_active=True) -> tuple[str, AdminSession]:
    admin = Admin(email=EMAIL, display_name="Alice Martin", is_active=is_active)
    db_session.add(admin)
    await db_session.flush()
    raw, row = create_session(db_session, admin)
    await db_session.commit()
    return raw, row


@pytest.mark.asyncio
async def test_valid_session_yields_auth_with_sliding_expiry(db_session):
    raw, row = await _seed_session(db_session)

    auth = await get_current_session(_request(raw), db_session)

    assert auth.admin_id == row.admin_id
    assert auth.email == EMAIL
    # Session fraîche : l'échéance effective est celle d'inactivité, pas le plafond absolu.
    expected = datetime.now(UTC) + AuthConfig.IDLE_TIMEOUT
    assert abs((auth.expires_at - expected).total_seconds()) < 5


@pytest.mark.asyncio
async def test_db_stores_only_the_token_hash(db_session):
    raw, row = await _seed_session(db_session)

    assert row.token_hash == hashlib.sha256(raw.encode()).hexdigest()
    assert raw not in row.token_hash


@pytest.mark.asyncio
async def test_idle_expired_session_is_401(db_session):
    raw, row = await _seed_session(db_session)
    row.last_seen_at = datetime.now(UTC) - AuthConfig.IDLE_TIMEOUT - timedelta(minutes=1)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc:
        await get_current_session(_request(raw), db_session)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Session expired"


@pytest.mark.asyncio
async def test_absolute_lifetime_caps_even_an_active_session(db_session):
    """Plafond dur : une session née il y a plus de 12h meurt même utilisée à l'instant."""
    raw, row = await _seed_session(db_session)
    row.created_at = datetime.now(UTC) - AuthConfig.ABSOLUTE_LIFETIME - timedelta(hours=1)
    row.last_seen_at = datetime.now(UTC)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc:
        await get_current_session(_request(raw), db_session)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Session expired"


@pytest.mark.asyncio
async def test_revoked_session_is_401(db_session):
    raw, row = await _seed_session(db_session)
    row.revoked_at = datetime.now(UTC)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc:
        await get_current_session(_request(raw), db_session)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Session expired"


@pytest.mark.asyncio
async def test_deactivated_admin_is_cut_off_immediately(db_session):
    raw, _ = await _seed_session(db_session, is_active=False)

    with pytest.raises(HTTPException) as exc:
        await get_current_session(_request(raw), db_session)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Session expired"


@pytest.mark.asyncio
async def test_unknown_token_is_401(db_session):
    await _seed_session(db_session)

    with pytest.raises(HTTPException) as exc:
        await get_current_session(_request("not-a-known-token"), db_session)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid session"


@pytest.mark.asyncio
async def test_missing_cookie_is_401(db_session):
    with pytest.raises(HTTPException) as exc:
        await get_current_session(_request(None), db_session)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Not authenticated"


@pytest.mark.asyncio
async def test_touch_refreshes_a_stale_last_seen(db_session):
    """L'activité fait glisser l'échéance : last_seen_at est réécrit quand il date."""
    raw, row = await _seed_session(db_session)
    stale = datetime.now(UTC) - timedelta(minutes=5)
    row.last_seen_at = stale
    await db_session.commit()

    await get_current_session(_request(raw), db_session)

    refreshed = (
        await db_session.execute(select(AdminSession.last_seen_at).where(AdminSession.id == row.id))
    ).scalar_one()
    assert refreshed.replace(tzinfo=UTC) > stale


@pytest.mark.asyncio
async def test_touch_is_throttled_on_a_fresh_last_seen(db_session):
    """Pas une écriture par requête : un last_seen_at récent n'est pas réécrit."""
    raw, row = await _seed_session(db_session)
    recent = datetime.now(UTC) - timedelta(seconds=10)
    row.last_seen_at = recent
    await db_session.commit()

    await get_current_session(_request(raw), db_session)

    stored = (
        await db_session.execute(select(AdminSession.last_seen_at).where(AdminSession.id == row.id))
    ).scalar_one()
    assert stored.replace(tzinfo=UTC) == recent


@pytest.mark.asyncio
async def test_revoke_all_sessions_kills_every_live_session(db_session):
    """Chemin du changement de mot de passe : toutes les sessions du compte tombent."""
    raw1, row = await _seed_session(db_session)
    admin_id = row.admin_id
    admin = (await db_session.execute(select(Admin).where(Admin.id == admin_id))).scalar_one()
    raw2, _ = create_session(db_session, admin)

    revoked = await revoke_all_sessions(db_session, admin_id)
    await db_session.commit()

    assert revoked == 2
    for raw in (raw1, raw2):
        with pytest.raises(HTTPException) as exc:
            await get_current_session(_request(raw), db_session)
        assert exc.value.detail == "Session expired"
