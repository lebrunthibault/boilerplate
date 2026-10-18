"""Agrégation des routers de l'API (public + admin)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.app.accounts import router as accounts_router
from api.app.api_key import require_api_key
from api.app.debug import router as debug_router
from api.app.llm_calls import router as llm_calls_router
from api.app.notifications import router as notifications_router
from api.app.rate_limit import rate_limit_public


class HealthOut(BaseModel):
    status: str
    version: str


class PingOut(BaseModel):
    pong: bool = True


# Public routes (no session). A route called by a third-party client takes the API key and the
# rate limit as dependencies — cf. /ping, the template for such routes.
public_router = APIRouter()


@public_router.get("/health")
async def health() -> HealthOut:
    from api.main import _version

    return HealthOut(status="ok", version=_version)


@public_router.post("/ping", dependencies=[Depends(rate_limit_public), Depends(require_api_key)])
async def ping() -> PingOut:
    """Exemple de route publique protégée par clé API + rate limit."""
    return PingOut()


# Admin routes (auth dependency applied at inclusion in main.py)
admin_router = APIRouter()
admin_router.include_router(accounts_router)
admin_router.include_router(notifications_router)
admin_router.include_router(llm_calls_router)
admin_router.include_router(debug_router)
