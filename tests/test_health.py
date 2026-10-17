"""Smoke test : l'app s'importe, démarre et répond — c'est le gate de la CI avant deploy."""

from __future__ import annotations


async def test_health_answers_ok(client):
    resp = await client.get("/api/health")

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_admin_routes_require_a_session(client):
    resp = await client.get("/api/accounts")

    assert resp.status_code == 401


async def test_public_ping_is_open_without_configured_key(client):
    """Sans ``SERVICE_API_KEY`` (dev/test), la route publique d'exemple reste ouverte."""
    resp = await client.post("/api/ping")

    assert resp.status_code == 200
    assert resp.json() == {"pong": True}
