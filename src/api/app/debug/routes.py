"""Diagnostic : la config de durcissement effective du process qui répond."""

from __future__ import annotations

import os

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class RuntimeConfig(BaseModel):
    """Ce qu'un admin doit pouvoir vérifier en prod sans SSH : le durcissement est-il actif ?"""

    app_env: str
    is_prod: bool
    session_cookie_name: str
    session_cookie_secure: bool
    rate_limit_public_enabled: bool
    rate_limit_public_per_minute: int
    retention_purge_enabled: bool
    allowed_origins_configured: bool
    service_api_key_configured: bool


@router.get("/debug/runtime-config")
async def debug_runtime_config() -> RuntimeConfig:
    """Config de durcissement effective du process qui répond."""
    from api.app import rate_limit
    from api.app.auth import AuthConfig
    from api.app.environment import APP_ENV, IS_PROD

    return RuntimeConfig(
        app_env=APP_ENV,
        is_prod=IS_PROD,
        session_cookie_name=AuthConfig.COOKIE_NAME,
        session_cookie_secure=IS_PROD,
        rate_limit_public_enabled=rate_limit.ENABLED,
        rate_limit_public_per_minute=rate_limit.PUBLIC_PER_MINUTE,
        retention_purge_enabled=IS_PROD,
        allowed_origins_configured=bool(os.environ.get("ALLOWED_ORIGINS")),
        service_api_key_configured=bool(os.environ.get("SERVICE_API_KEY")),
    )
