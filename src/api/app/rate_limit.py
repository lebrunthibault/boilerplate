"""Rate limit par IP des routes publiques (dépendance ``rate_limit_public``).

Fenêtre fixe d'une minute, compteur en mémoire par IP. Actif en prod uniquement (``IS_PROD``) :
les tests et le dev local ne doivent jamais être bridés. Défense en profondeur derrière la clé
API (une clé fuitée reste bornée en débit). Par-processus : suffisant en mono-instance.
"""

from __future__ import annotations

import os
import time

from fastapi import HTTPException, Request, status

from api.app.client_ip import client_ip
from api.app.environment import IS_PROD

PUBLIC_PER_MINUTE = int(os.environ.get("RATE_LIMIT_PUBLIC_PER_MINUTE", "20"))
ENABLED = IS_PROD

_WINDOW_SECONDS = 60
_hits: dict[str, tuple[int, int]] = {}  # ip -> (début_de_fenêtre, compte)


def rate_limit_public(request: Request) -> None:
    if not ENABLED:
        return
    ip = client_ip(request) or "unknown"
    now = int(time.time())
    window = now - (now % _WINDOW_SECONDS)
    start, count = _hits.get(ip, (window, 0))
    if start != window:
        start, count = window, 0
    count += 1
    _hits[ip] = (start, count)
    if count > PUBLIC_PER_MINUTE:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Trop de requêtes, réessayez dans un instant.",
        )
