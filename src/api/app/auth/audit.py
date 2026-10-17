"""Admin authentication audit trail: who logged in, from where, and what failed.

Two destinations for one call — the ``admin_auth_event`` table (durable, readable from the
dashboard) and the stdlib logger (visible in ``docker logs`` even when the database is not).
Nothing in the code ever reads a row back except the audit screen: it is written once and read
by a human.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, cast

from fastapi import Request
from sqlalchemy import delete
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.client_ip import client_ip
from api.app.config import Retention
from api.infra.db.models import AdminAuthEvent

logger = logging.getLogger(__name__)


class AuthEventKind(StrEnum):
    """Journalled events. The value is what the ``kind`` column carries."""

    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGIN_BLOCKED = "login_blocked"
    LOGOUT = "logout"
    SESSIONS_REVOKED = "sessions_revoked"
    STEP_UP_SUCCESS = "step_up_success"
    STEP_UP_FAILURE = "step_up_failure"


class AuthAudit:
    """Bounds of the audit trail: column caps and the read page size."""

    EMAIL_MAX = 320
    USER_AGENT_MAX = 255
    DETAIL_MAX = 255
    PAGE_SIZE = 50
    PAGE_SIZE_MAX = 200


@dataclass(frozen=True)
class AuthEvent:
    """One event ready to be journalled — the payload, without the request-side context.

    ``email`` is the *attempted* address: it is what identifies a failed login on an address no
    account matches, the only case where ``admin_id`` stays None. ``detail`` is short,
    non-nominative context (``accounts/deactivate``, ``3 sessions``) — never personal data of
    the people the product serves, since the trail outlives a GDPR erasure.
    """

    kind: AuthEventKind
    email: str | None = None
    admin_id: int | None = None
    detail: str | None = None


def _truncate(value: str | None, cap: int) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped[:cap] if stripped else None


async def record_auth_event(db: AsyncSession, request: Request | None, event: AuthEvent) -> None:
    """Write *event* to the audit table and to the logger. Commits; never raises.

    **Commits itself**, unlike the rest of ``app/auth`` where the caller owns the commit: most
    call sites raise an ``HTTPException`` (401/403/429) right after, which would roll the row
    back — losing exactly the events that matter. Call it *after* the business commit, never in
    the middle of a pending write.

    **Swallows its own failure**: a broken audit write must not turn a valid login into a 500.
    It is reported on the logger, which stays the second destination — a line in ``docker logs``
    survives even when the table does not.

    *request* is None outside an HTTP request (``scripts/set_admin_password.py``): no IP, no
    user-agent, the event is journalled all the same.
    """
    ip = client_ip(request) if request is not None else None
    user_agent = (
        _truncate(request.headers.get("user-agent"), AuthAudit.USER_AGENT_MAX)
        if request is not None
        else None
    )
    # Normalisée une fois pour les deux destinations : le journal et la ligne de log doivent
    # dire la même chose (la recherche se fait sur l'adresse en minuscules).
    attempted = _truncate(event.email, AuthAudit.EMAIL_MAX)
    email = attempted.lower() if attempted else None
    logger.info(
        "auth %s email=%s admin=%s ip=%s detail=%s",
        event.kind.value,
        email,
        event.admin_id,
        ip,
        event.detail,
    )
    db.add(
        AdminAuthEvent(
            occurred_at=datetime.now(UTC),
            kind=event.kind.value,
            admin_id=event.admin_id,
            email=email,
            ip=_truncate(ip, 45),
            user_agent=user_agent,
            detail=_truncate(event.detail, AuthAudit.DETAIL_MAX),
        )
    )
    try:
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        logger.exception("auth audit write failed (%s)", event.kind.value)


async def purge_auth_events(db: AsyncSession) -> int:
    """Delete journal rows past ``Retention.AUTH_EVENTS``. Commits itself (background loop)."""
    cutoff = datetime.now(UTC) - Retention.AUTH_EVENTS
    result = await db.execute(delete(AdminAuthEvent).where(AdminAuthEvent.occurred_at < cutoff))
    await db.commit()
    # Un execute DML rend en pratique un CursorResult (porteur de rowcount) ; le type
    # statique Result[Any] ne le sait pas.
    deleted = cast(CursorResult[Any], result).rowcount or 0
    if deleted:
        logger.info("auth audit purge: %d events (cutoff=%s)", deleted, cutoff.date())
    return deleted
