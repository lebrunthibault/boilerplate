"""Durcissement piloté par ``APP_ENV`` : la prod ne doit plus pouvoir se croire en dev.

Tout le durcissement (cookie ``Secure`` + préfixe ``__Host-``, rate limit des routes publiques,
purge de rétention, fail-closed CORS/clé API) dépend d'une seule variable : sans ces tests, une
variable renommée ou disparue servirait la prod cookie non-Secure, en silence.
"""

from __future__ import annotations

import importlib

import pytest

from api.app import environment as environment_module
from api.app import rate_limit as rate_limit_module
from api.app.auth import AuthConfig, hash_password
from api.app.auth import routes as auth_routes
from api.app.auth import service as auth_service_module
from api.infra.db.models import Admin

EMAIL = "admin@example.com"
PASSWORD = "correct horse battery staple"


def _reload_all():
    """Recharge, dans l'ordre des dépendances, les modules qui figent ``IS_PROD`` à l'import."""
    importlib.reload(environment_module)
    importlib.reload(rate_limit_module)
    importlib.reload(auth_service_module)


@pytest.fixture
def app_env(monkeypatch):
    """Rejoue l'import des modules de durcissement sous un ``APP_ENV`` donné.

    ``environment.IS_PROD`` est une constante de module, et ``rate_limit.ENABLED`` comme
    ``AuthConfig.COOKIE_NAME`` en dérivent au moment de *leur* propre import : sans reload, un
    ``monkeypatch.setenv`` ne change rien. Le teardown rejoue le reload avec l'environnement
    d'origine, sinon les constantes rechargées fuiraient sur les tests suivants.
    """

    def reload_with(value: str | None):
        if value is None:
            monkeypatch.delenv("APP_ENV", raising=False)
        else:
            monkeypatch.setenv("APP_ENV", value)
        _reload_all()

    yield reload_with

    monkeypatch.undo()
    _reload_all()


def test_production_enables_every_hardening_switch(app_env):
    app_env("production")

    assert environment_module.IS_PROD is True
    assert rate_limit_module.ENABLED is True
    assert auth_service_module.AuthConfig.COOKIE_NAME == "__Host-admin_session"


def test_unknown_app_env_refuses_to_start(app_env):
    """Une faute de frappe ne dégrade plus la sécurité en silence : elle empêche le boot."""
    with pytest.raises(RuntimeError, match="APP_ENV"):
        app_env("prod")


def test_absent_app_env_falls_back_to_local(app_env):
    """L'absence reste du dev (tests, poste local) — c'est deploy.sh et le compose prod qui
    garantissent la valeur côté serveur."""
    app_env(None)

    assert environment_module.APP_ENV == "local"
    assert environment_module.IS_PROD is False
    assert rate_limit_module.ENABLED is False


@pytest.mark.asyncio
async def test_login_cookie_is_secure_and_host_prefixed_in_prod(client, db_session, monkeypatch):
    """Le cookie de session porte bien ``Secure`` et ``__Host-`` dès que le process est en prod.

    On bascule les deux constantes que la route lit à l'appel plutôt que de recharger le module :
    ``auth.routes`` a importé ``IS_PROD`` dans son propre espace de noms, un reload de
    ``environment`` ne le suivrait pas.
    """
    monkeypatch.setattr(auth_routes, "IS_PROD", True)
    monkeypatch.setattr(AuthConfig, "COOKIE_NAME", "__Host-admin_session")
    db_session.add(
        Admin(email=EMAIL, display_name="Alice Martin", password_hash=hash_password(PASSWORD))
    )
    await db_session.commit()

    resp = await client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})

    assert resp.status_code == 200
    set_cookie = resp.headers["set-cookie"]
    assert "__Host-admin_session=" in set_cookie
    assert "Secure" in set_cookie
    assert "HttpOnly" in set_cookie


@pytest.mark.asyncio
async def test_runtime_config_route_reports_effective_hardening(admin_client):
    """La route de debug rend l'état réel du process — de quoi constater la prod sans SSH."""
    resp = await admin_client.get("/api/debug/runtime-config")

    assert resp.status_code == 200
    body = resp.json()
    assert body["app_env"] == environment_module.APP_ENV
    assert body["is_prod"] is environment_module.IS_PROD
    assert body["session_cookie_name"] == AuthConfig.COOKIE_NAME
    assert body["rate_limit_public_enabled"] is rate_limit_module.ENABLED
    # Jamais la valeur des secrets, seulement leur présence.
    assert set(body) & {"service_api_key", "allowed_origins"} == set()
