"""Clé API partagée pour les routes publiques appelées par un client tiers (``X-API-Key``).

Garde-fou anti-abus/coût, PAS de l'authentification utilisateur : si la clé est embarquée dans
un client distribué (extension, app mobile, widget), elle est lisible côté client — c'est un
ralentisseur contre les scanners/bots, à combiner avec le rate limit. Si ``SERVICE_API_KEY``
n'est pas configurée (dev/test), la route reste ouverte ; en prod elle est requise
(fail-closed, cf. ``main.lifespan``).
"""

from __future__ import annotations

import os
import secrets

from fastapi import HTTPException, Request, status

_SERVICE_API_KEY = os.environ.get("SERVICE_API_KEY", "")


def require_api_key(request: Request) -> None:
    """Exige un ``X-API-Key`` valide quand une clé est configurée ; sinon laisse passer."""
    if not _SERVICE_API_KEY:
        return
    provided = request.headers.get("X-API-Key", "")
    if provided and secrets.compare_digest(provided, _SERVICE_API_KEY):
        return
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid API key",
    )
