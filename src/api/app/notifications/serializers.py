"""HTTP shapes of the admin inbox (Pydantic at the HTTP boundary)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from api.app.auth import AdminRef
from api.app.config import NotificationLimits


class NotificationOut(BaseModel):
    """One inbox line: what happened, on which target, and who did it.

    ``actor`` is None when the event has no admin actor (system job, end user).
    """

    id: int
    kind: str
    actor: AdminRef | None
    target_type: str | None
    target_id: int | None
    title: str | None
    preview: str | None
    payload: dict[str, Any] | None
    created_at: datetime
    read_at: datetime | None


class NotificationListOut(BaseModel):
    """The inbox itself. ``unread`` is always the recipient's global count, never filtered."""

    items: list[NotificationOut]
    unread: int


def preview_of(text: str | None) -> str | None:
    """Cap a preview to what an inbox row can display."""
    if not text:
        return None
    stripped = text.strip()
    if len(stripped) <= NotificationLimits.PREVIEW_CHARS:
        return stripped
    return stripped[: NotificationLimits.PREVIEW_CHARS].rstrip() + "…"
