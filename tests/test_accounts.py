"""Comptes admin : liste paginée et désactivation sous step-up."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from api.app.auth import rate_limit as rate_limit_module
from api.infra.db.models import Admin, AdminAuthEvent, AdminSession
from tests.conftest import ADMIN_PASSWORD, OTHER_ADMIN_EMAIL, SeededAdmins, login_as


@pytest.fixture(autouse=True)
def reset_rate_limit():
    """Le compteur d'échecs est module-level : sans reset, il fuit d'un test à l'autre."""
    rate_limit_module._failures.clear()
    yield
    rate_limit_module._failures.clear()


def _proof(password: str) -> dict:
    return {"confirmation": {"method": "password", "password": password}}


async def test_list_accounts_flags_the_caller(admins: SeededAdmins):
    resp = await admins.client.get("/api/accounts")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    me = next(a for a in body["items"] if a["id"] == admins.me.id)
    assert me["is_me"] is True
    assert me["has_password"] is True
    assert "password_hash" not in me


async def test_deactivate_requires_the_right_password(admins: SeededAdmins, db_session):
    resp = await admins.client.post(
        f"/api/accounts/{admins.other.id}/deactivate", json=_proof("wrong")
    )

    assert resp.status_code == 403
    await db_session.refresh(admins.other)
    assert admins.other.is_active is True
    kinds = (await db_session.execute(select(AdminAuthEvent.kind))).scalars().all()
    assert "step_up_failure" in kinds


async def test_deactivate_cuts_the_target_sessions(admins: SeededAdmins, client, db_session):
    # Une session ouverte pour l'autre compte, puis retour sur le premier.
    await login_as(client, OTHER_ADMIN_EMAIL)
    await login_as(client, admins.me.email)

    resp = await client.post(
        f"/api/accounts/{admins.other.id}/deactivate", json=_proof(ADMIN_PASSWORD)
    )

    assert resp.status_code == 200
    assert resp.json()["revoked_sessions"] == 1
    other = await db_session.get(Admin, admins.other.id)
    assert other is not None and other.is_active is False
    live = await db_session.execute(
        select(AdminSession).where(
            AdminSession.admin_id == admins.other.id, AdminSession.revoked_at.is_(None)
        )
    )
    assert live.scalars().all() == []


async def test_cannot_deactivate_yourself(admins: SeededAdmins):
    resp = await admins.client.post(
        f"/api/accounts/{admins.me.id}/deactivate", json=_proof(ADMIN_PASSWORD)
    )

    assert resp.status_code == 400
