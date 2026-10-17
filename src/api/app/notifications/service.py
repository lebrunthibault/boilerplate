"""Write side of the admin inbox: turn an event into one row per recipient."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.notifications.serializers import preview_of
from api.infra.db.models import Admin, AdminNotification


@dataclass(frozen=True)
class NotificationEvent:
    """The event to fan out, before recipients are resolved.

    ``kind`` is a short, stable key owned by the emitting package ("invoice_paid"…). The
    target (``target_type`` + ``target_id``) is what the inbox row links to; both stay None for
    an event about nothing in particular. ``actor_admin_id`` is None when the actor is not an
    admin (system job, end user): there is then nobody to leave out of the fan-out.

    ``fold`` merges the event into the recipient's unread row of the same kind on the same
    target instead of stacking a new line — for "updated" events saved several times in a row.
    The row keeps its ``created_at`` and takes the new title/preview; ``payload`` keys are
    merged, the newest value winning.
    """

    kind: str
    actor_admin_id: int | None = None
    target_type: str | None = None
    target_id: int | None = None
    title: str | None = None
    preview: str | None = None
    payload: dict[str, Any] | None = None
    fold: bool = False


async def _recipients(session: AsyncSession, actor_admin_id: int | None) -> list[int]:
    """Active admins other than the actor. Nobody ever notifies themselves."""
    query = select(Admin.id).where(Admin.is_active.is_(True))
    if actor_admin_id is not None:
        query = query.where(Admin.id != actor_admin_id)
    rows = await session.execute(query)
    return list(rows.scalars())


async def _unread_twin(
    session: AsyncSession, recipient_id: int, event: NotificationEvent
) -> AdminNotification | None:
    row = await session.execute(
        select(AdminNotification)
        .where(
            AdminNotification.recipient_admin_id == recipient_id,
            AdminNotification.kind == event.kind,
            AdminNotification.target_type == event.target_type,
            AdminNotification.target_id == event.target_id,
            AdminNotification.read_at.is_(None),
        )
        .limit(1)
    )
    return row.scalar_one_or_none()


async def _fold_into_unread(
    session: AsyncSession, recipient_id: int, event: NotificationEvent
) -> bool:
    """Merge *event* into the recipient's unread twin. False when there is none."""
    existing = await _unread_twin(session, recipient_id, event)
    if existing is None:
        return False
    existing.title = event.title or existing.title
    existing.preview = preview_of(event.preview) or existing.preview
    if event.payload:
        # A new dict, not an in-place update: JSONB columns are not mutation-tracked.
        existing.payload = {**(existing.payload or {}), **event.payload}
    return True


async def notify_admins(session: AsyncSession, event: NotificationEvent) -> None:
    """Insert one inbox row per active admin **other than the actor**. Caller commits.

    Two admins → exactly one row. A single active admin acting produces none: an inbox of
    one's own actions is noise. An event with no admin actor reaches every active admin.
    """
    now = datetime.now(UTC)
    for recipient_id in await _recipients(session, event.actor_admin_id):
        if event.fold and await _fold_into_unread(session, recipient_id, event):
            continue
        session.add(
            AdminNotification(
                recipient_admin_id=recipient_id,
                actor_admin_id=event.actor_admin_id,
                kind=event.kind,
                target_type=event.target_type,
                target_id=event.target_id,
                title=event.title,
                preview=preview_of(event.preview),
                payload=event.payload,
                created_at=now,
            )
        )
