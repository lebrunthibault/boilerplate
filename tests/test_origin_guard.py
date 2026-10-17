"""Garde Origin sur les routes à cookie — défense CSRF en profondeur.

Le cookie est déjà ``SameSite=lax`` et les routes admin ne lisent que du JSON : cette garde
couvre ce que Lax ne couvre pas — un sous-domaine compromis, et une route future qui
accepterait autre chose que du JSON. Elle ne s'applique **qu'aux méthodes mutantes** et ne
refuse que si une origine est **annoncée et étrangère** : un client non-navigateur (curl, cette
suite de tests) n'annonce rien et passe.
"""

from __future__ import annotations

import pytest

from api.app.auth.origin import _own_origin
from api.app.environment import ALLOWED_ORIGINS

TRUSTED = ALLOWED_ORIGINS[0]
FOREIGN = "https://evil.example"


@pytest.mark.asyncio
async def test_mutation_without_origin_passes(admin_client):
    """Le client de test n'envoie pas d'Origin : la garde ne doit pas s'y opposer."""
    resp = await admin_client.post("/api/auth/logout")

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_mutation_from_trusted_origin_passes(admin_client):
    resp = await admin_client.post("/api/auth/logout", headers={"Origin": TRUSTED})

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_mutation_from_foreign_origin_is_refused(admin_client):
    resp = await admin_client.post("/api/auth/logout", headers={"Origin": FOREIGN})

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Untrusted origin"


@pytest.mark.asyncio
async def test_admin_mutation_from_foreign_origin_is_refused(admin_client):
    """La garde couvre toutes les mutations admin par une dépendance de routeur."""
    resp = await admin_client.delete("/api/notifications/999", headers={"Origin": FOREIGN})

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_origin_checked_before_the_session(client):
    """Origine d'abord : une requête cross-origin est refusée sans toucher la base."""
    resp = await client.delete("/api/notifications/999", headers={"Origin": FOREIGN})

    assert resp.status_code == 403  # et non 401 « Not authenticated »


@pytest.mark.asyncio
async def test_read_from_foreign_origin_passes(admin_client):
    """Seules les méthodes mutantes sont gardées ; un GET cross-origin reste borné par le CORS."""
    resp = await admin_client.get("/api/auth/me", headers={"Origin": FOREIGN})

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_referer_is_the_fallback(admin_client):
    """Sans Origin, le Referer tranche (navigateur qui omet Origin)."""
    refused = await admin_client.post(
        "/api/auth/logout", headers={"Referer": f"{FOREIGN}/page.html"}
    )
    assert refused.status_code == 403

    accepted = await admin_client.post(
        "/api/auth/logout", headers={"Referer": f"{TRUSTED}/admin/accounts"}
    )
    assert accepted.status_code == 200


@pytest.mark.asyncio
async def test_same_origin_prod_is_trusted(admin_client):
    """En prod le SPA est same-origin et n'est donc dans aucune liste : Host + proto le disent.

    Le schéma vient de ``X-Forwarded-Proto`` et non de ``request.url.scheme``, qui vaut ``http``
    derrière nginx (uvicorn tourne sans ``--proxy-headers``) — c'est le piège de cette garde.
    """
    resp = await admin_client.post(
        "/api/auth/logout",
        headers={
            "Host": "app.example.com",
            "X-Forwarded-Proto": "https",
            "Origin": "https://app.example.com",
        },
    )

    assert resp.status_code == 200


def test_own_origin_prefers_the_forwarded_scheme():
    from starlette.requests import Request

    scope = {
        "type": "http",
        "method": "POST",
        "scheme": "http",
        "path": "/api/auth/logout",
        "headers": [
            (b"host", b"app.example.com"),
            (b"x-forwarded-proto", b"https"),
        ],
    }

    assert _own_origin(Request(scope)) == "https://app.example.com"


@pytest.mark.asyncio
async def test_public_routes_are_not_guarded(client):
    """Le routeur public s'authentifie par clé API, jamais par cookie : pas de CSRF à couvrir.

    Un client tiers (extension, app native) n'annonce pas toujours une origine fiable — le
    garder casserait ces clients pour un gain nul.
    """
    resp = await client.post("/api/ping", headers={"Origin": FOREIGN})

    assert resp.status_code == 200
