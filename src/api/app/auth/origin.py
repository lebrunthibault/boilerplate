"""Origin check on cookie-authenticated mutations — CSRF defence in depth.

The session cookie is ``SameSite=lax`` and every admin route reads JSON, so a cross-site form
already carries neither the cookie (Lax withholds it on a cross-site POST) nor an acceptable body
(FastAPI answers 422 to anything that is not ``application/json``, and a form cannot send that).
This guard covers what Lax does not: a compromised sub-domain — same-site, so the cookie *is*
sent, but not same-origin — and any future route accepting something other than JSON.
"""

from __future__ import annotations

import logging
from urllib.parse import urlsplit

from fastapi import HTTPException, Request, status

from api.app.environment import ALLOWED_ORIGINS

logger = logging.getLogger(__name__)

_UNSAFE_METHODS = frozenset({"POST", "PATCH", "PUT", "DELETE"})


def _origin_of(url: str) -> str | None:
    """Scheme + host + port of *url*, or None when it is not a usable absolute URL."""
    parsed = urlsplit(url.strip())
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _own_origin(request: Request) -> str | None:
    """The origin the site is served on, rebuilt from the proxy headers.

    In prod the admin SPA is same-origin with the API (served behind the same nginx), so it is
    never listed in ``ALLOWED_ORIGINS`` — the guard has to recognise it on its own. The scheme
    comes from ``X-Forwarded-Proto`` (set by nginx) and **not** from ``request.url.scheme``,
    which reads ``http`` because uvicorn runs without ``--proxy-headers``.
    """
    host = request.headers.get("host")
    if not host:
        return None
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme).split(",")[0].strip()
    return f"{scheme}://{host}"


async def enforce_trusted_origin(request: Request) -> None:
    """Reject a mutating request that states a third-party origin.

    A non-browser client (curl, the test suite, a script) sends neither ``Origin`` nor
    ``Referer``: it is let through — nothing ambient authenticates it, so there is no CSRF to
    speak of. Every browser sets ``Origin`` on a mutating method, so the guard bites exactly
    where the risk is; ``Referer`` is only a fallback for a browser that omits ``Origin``.

    Refusals are logged, never persisted: an anonymous cross-origin caller must not be able to
    write rows into the audit trail.
    """
    if request.method not in _UNSAFE_METHODS:
        return
    stated = request.headers.get("origin") or request.headers.get("referer")
    if stated is None:
        return
    trusted = {*ALLOWED_ORIGINS, _own_origin(request)}
    if _origin_of(stated) in trusted:
        return
    logger.warning("untrusted origin %s on %s %s", stated, request.method, request.url.path)
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Untrusted origin")
