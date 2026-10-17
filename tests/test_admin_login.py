"""Comptes admin en base : `authenticate` (échec indistinct) et la route /auth/login.

Contrat : un échec indistinct — email inconnu,
compte inactif, hash NULL (compte seedé pas encore bootstrappé) et mauvais mot de passe
rendent tous None — et un login qui persiste `last_login_at` (commit explicite : la
dépendance get_session ne commit jamais d'elle-même).
"""

from __future__ import annotations

import hashlib

import pytest
from sqlalchemy import select

from api.app.auth import AuthConfig, LoginRateLimit, authenticate, hash_password
from api.app.auth import rate_limit as rate_limit_module
from api.infra.db.models import Admin, AdminSession

EMAIL = "admin@example.com"
PASSWORD = "correct horse battery staple"


@pytest.fixture(autouse=True)
def reset_rate_limit():
    """Le compteur d'échecs est module-level : sans reset, il fuit d'un test à l'autre."""
    rate_limit_module._failures.clear()
    yield
    rate_limit_module._failures.clear()


async def _seed_admin(db_session, password_hash=None, is_active=True) -> Admin:
    admin = Admin(
        email=EMAIL, display_name="Alice Martin", password_hash=password_hash, is_active=is_active
    )
    db_session.add(admin)
    await db_session.commit()
    return admin


@pytest.mark.asyncio
async def test_authenticate_success_sets_last_login(db_session):
    await _seed_admin(db_session, password_hash=hash_password(PASSWORD))

    admin = await authenticate(db_session, EMAIL, PASSWORD)

    assert admin is not None
    assert admin.email == EMAIL
    assert admin.last_login_at is not None


@pytest.mark.asyncio
async def test_authenticate_is_case_insensitive_on_email(db_session):
    await _seed_admin(db_session, password_hash=hash_password(PASSWORD))

    assert await authenticate(db_session, "Admin@Example.com ", PASSWORD) is not None


@pytest.mark.asyncio
async def test_authenticate_wrong_password(db_session):
    await _seed_admin(db_session, password_hash=hash_password(PASSWORD))

    assert await authenticate(db_session, EMAIL, "wrong") is None


@pytest.mark.asyncio
async def test_authenticate_unknown_email(db_session):
    assert await authenticate(db_session, "nobody@example.com", PASSWORD) is None


@pytest.mark.asyncio
async def test_authenticate_inactive_account(db_session):
    await _seed_admin(db_session, password_hash=hash_password(PASSWORD), is_active=False)

    assert await authenticate(db_session, EMAIL, PASSWORD) is None


@pytest.mark.asyncio
async def test_authenticate_null_hash_refuses_login(db_session):
    """Compte seedé par la migration, mot de passe jamais posé : connexion impossible."""
    await _seed_admin(db_session, password_hash=None)

    assert await authenticate(db_session, EMAIL, PASSWORD) is None
    # Un mot de passe vide ne doit pas non plus « matcher » le hash absent.
    assert await authenticate(db_session, EMAIL, "") is None


@pytest.mark.asyncio
async def test_login_route_sets_cookie_and_creates_session_row(client, db_session):
    await _seed_admin(db_session, password_hash=hash_password(PASSWORD))

    resp = await client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})

    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert "expires_at" in body
    raw = resp.cookies[AuthConfig.COOKIE_NAME]
    # La base ne stocke que l'empreinte du cookie, jamais le jeton brut.
    row = (await db_session.execute(select(AdminSession))).scalar_one()
    assert row.token_hash == hashlib.sha256(raw.encode()).hexdigest()
    assert row.revoked_at is None


@pytest.mark.asyncio
async def test_login_cookie_attributes(client, db_session):
    """HttpOnly + SameSite + Path=/ + Max-Age = plafond absolu (12h)."""
    await _seed_admin(db_session, password_hash=hash_password(PASSWORD))

    resp = await client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})

    set_cookie = resp.headers["set-cookie"]
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Path=/" in set_cookie
    assert f"Max-Age={int(AuthConfig.ABSOLUTE_LIFETIME.total_seconds())}" in set_cookie


@pytest.mark.asyncio
async def test_logout_revokes_the_session_server_side(client, db_session):
    """Le logout n'est plus un simple oubli de cookie : la ligne est révoquée en base."""
    await _seed_admin(db_session, password_hash=hash_password(PASSWORD))
    login = await client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    raw = login.cookies[AuthConfig.COOKIE_NAME]
    assert (await client.get("/api/auth/me")).status_code == 200

    resp = await client.post("/api/auth/logout")

    assert resp.status_code == 200
    row = (await db_session.execute(select(AdminSession))).scalar_one()
    assert row.revoked_at is not None
    # Un cookie volé rejoué après logout est mort côté serveur, pas juste oublié côté client.
    client.cookies.set(AuthConfig.COOKIE_NAME, raw)
    assert (await client.get("/api/auth/me")).status_code == 401


@pytest.mark.asyncio
async def test_login_route_rejects_bad_password(client, db_session):
    await _seed_admin(db_session, password_hash=hash_password(PASSWORD))

    resp = await client.post("/api/auth/login", json={"email": EMAIL, "password": "wrong"})

    assert resp.status_code == 401
    assert AuthConfig.COOKIE_NAME not in resp.cookies


@pytest.mark.asyncio
async def test_login_rate_limited_after_repeated_failures(client, db_session):
    """Au-delà de MAX_FAILURES échecs, 429 même avec le bon mot de passe (fenêtre glissante)."""
    await _seed_admin(db_session, password_hash=hash_password(PASSWORD))

    for _ in range(LoginRateLimit.MAX_FAILURES):
        resp = await client.post("/api/auth/login", json={"email": EMAIL, "password": "wrong"})
        assert resp.status_code == 401

    resp = await client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert resp.status_code == 429
    assert "access_token" not in resp.cookies


@pytest.mark.asyncio
async def test_login_success_clears_failure_counter(client, db_session):
    await _seed_admin(db_session, password_hash=hash_password(PASSWORD))

    for _ in range(LoginRateLimit.MAX_FAILURES - 1):
        await client.post("/api/auth/login", json={"email": EMAIL, "password": "wrong"})
    assert (
        await client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    ).status_code == 200

    # Compteur remis à zéro : un nouvel échec ne déclenche pas le blocage.
    resp = await client.post("/api/auth/login", json={"email": EMAIL, "password": "wrong"})
    assert resp.status_code == 401


def test_rate_limit_window_expires(monkeypatch):
    """Les échecs sortis de la fenêtre glissante ne comptent plus."""
    from api.app.auth.rate_limit import LoginBucket, login_blocked, record_login_failure

    clock = 0.0
    monkeypatch.setattr(rate_limit_module, "monotonic", lambda: clock)
    bucket = LoginBucket(pair="10.0.0.1|" + EMAIL, ip="10.0.0.1")

    for _ in range(LoginRateLimit.MAX_FAILURES):
        record_login_failure(bucket)

    clock = 1.0  # dans la fenêtre
    assert login_blocked(bucket)
    clock = LoginRateLimit.WINDOW_SECONDS + 1.0  # fenêtre expirée
    assert not login_blocked(bucket)


def test_spraying_from_one_ip_is_blocked(client, db_session):
    """Le seau IP ferme le password-spraying, que le seau IP+email laisse passer.

    Chaque adresse a son propre seau paire : sans le seau IP, une même origine pourrait tenter
    5 mots de passe sur autant d'adresses qu'elle veut — et écrire autant de lignes dans le
    journal d'authentification.
    """
    from api.app.auth.rate_limit import LoginBucket, login_blocked, record_login_failure

    ip = "10.0.0.2"
    for i in range(LoginRateLimit.MAX_FAILURES_PER_IP):
        record_login_failure(LoginBucket(pair=f"{ip}|victim{i}@example.com", ip=ip))

    # Une adresse encore jamais tentée depuis cette IP est bloquée elle aussi.
    assert login_blocked(LoginBucket(pair=f"{ip}|" + EMAIL, ip=ip))


def test_success_clears_the_pair_bucket_not_the_ip_one(client, db_session):
    """Un succès légitime ne remet pas à zéro le compteur d'une IP qui frappe d'autres comptes."""
    from api.app.auth.rate_limit import (
        LoginBucket,
        clear_login_failures,
        login_blocked,
        record_login_failure,
    )

    ip = "10.0.0.3"
    mine = LoginBucket(pair=f"{ip}|" + EMAIL, ip=ip)
    for i in range(LoginRateLimit.MAX_FAILURES_PER_IP):
        record_login_failure(LoginBucket(pair=f"{ip}|victim{i}@example.com", ip=ip))

    clear_login_failures(mine)

    assert login_blocked(mine)
