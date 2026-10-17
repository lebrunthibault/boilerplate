"""Real client IP behind nginx — one implementation for every caller.

Written twice before this module (the analyse rate limit and the login throttle), in two
slightly different ways; the auth audit trail needed it a third time.
"""

from __future__ import annotations

from fastapi import Request


def client_ip(request: Request) -> str | None:
    """Real client IP of *request*, or None when nothing identifies it.

    ``X-Real-IP`` first: nginx overwrites it on every proxied request (``docker/nginx.conf``),
    so a client cannot forge it in prod. Then the first hop of ``X-Forwarded-For``. Last, the
    connection address — which in prod is only the nginx container, uvicorn running without
    ``--proxy-headers``, but which is the real caller in dev and in tests.
    """
    real = request.headers.get("x-real-ip")
    if real and real.strip():
        return real.strip()
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded and forwarded.split(",")[0].strip():
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None
