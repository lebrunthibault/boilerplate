"""Admin endpoints for the inbox: read, mark read/unread, delete."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.auth import AdminRef, AuthSession, get_current_session
from api.app.config import NotificationLimits
from api.app.notifications.serializers import NotificationListOut, NotificationOut
from api.infra.db import get_session
from api.infra.db.models import Admin, AdminNotification

router = APIRouter()


class OkOut(BaseModel):
    ok: bool = True


@router.get("/notifications")
async def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(NotificationLimits.LIST_DEFAULT, ge=1, le=NotificationLimits.LIST_MAX),
    auth: AuthSession = Depends(get_current_session),
    session: AsyncSession = Depends(get_session),
) -> NotificationListOut:
    """The caller's inbox. One query, joined — never one lookup per row."""
    rows_q = (
        select(AdminNotification, Admin.display_name, Admin.email)
        .outerjoin(Admin, Admin.id == AdminNotification.actor_admin_id)
        .where(AdminNotification.recipient_admin_id == auth.admin_id)
        .order_by(AdminNotification.created_at.desc(), AdminNotification.id.desc())
        .limit(limit)
    )
    if unread_only:
        rows_q = rows_q.where(AdminNotification.read_at.is_(None))

    rows = await session.execute(rows_q)
    items = [
        NotificationOut(
            id=n.id,
            kind=n.kind,
            actor=_actor(n.actor_admin_id, display_name, email, auth.admin_id),
            target_type=n.target_type,
            target_id=n.target_id,
            title=n.title,
            preview=n.preview,
            payload=n.payload,
            created_at=n.created_at,
            read_at=n.read_at,
        )
        for n, display_name, email in rows
    ]

    # Global on purpose: the sidebar badge must not move when the page filters itself.
    unread = (
        await session.execute(
            select(func.count(AdminNotification.id)).where(
                AdminNotification.recipient_admin_id == auth.admin_id,
                AdminNotification.read_at.is_(None),
            )
        )
    ).scalar_one()

    return NotificationListOut(items=items, unread=unread)


def _actor(
    actor_admin_id: int | None, display_name: str | None, email: str | None, me: int
) -> AdminRef | None:
    """The admin who acted — None when the actor is not an admin."""
    if actor_admin_id is None or email is None:
        return None
    return AdminRef(
        id=actor_admin_id, display_name=display_name, email=email, is_me=actor_admin_id == me
    )


class NotificationReadRequest(BaseModel):
    read: bool


@router.patch("/notifications/{notification_id}")
async def set_notification_read(
    notification_id: int,
    req: NotificationReadRequest,
    auth: AuthSession = Depends(get_current_session),
    session: AsyncSession = Depends(get_session),
) -> OkOut:
    """Mark one row read, or put it back to unread. Only the recipient's own rows."""
    result = await session.execute(
        update(AdminNotification)
        .where(
            AdminNotification.id == notification_id,
            AdminNotification.recipient_admin_id == auth.admin_id,
        )
        .values(read_at=datetime.now(UTC) if req.read else None)
        .returning(AdminNotification.id)
    )
    if not result.one_or_none():
        raise HTTPException(status_code=404, detail="Notification not found")
    await session.commit()
    return OkOut()


@router.post("/notifications/read-all")
async def mark_all_read(
    auth: AuthSession = Depends(get_current_session),
    session: AsyncSession = Depends(get_session),
) -> OkOut:
    await session.execute(
        update(AdminNotification)
        .where(
            AdminNotification.recipient_admin_id == auth.admin_id,
            AdminNotification.read_at.is_(None),
        )
        .values(read_at=datetime.now(UTC))
    )
    await session.commit()
    return OkOut()


@router.delete("/notifications/{notification_id}")
async def delete_notification(
    notification_id: int,
    auth: AuthSession = Depends(get_current_session),
    session: AsyncSession = Depends(get_session),
) -> OkOut:
    result = await session.execute(
        delete(AdminNotification)
        .where(
            AdminNotification.id == notification_id,
            AdminNotification.recipient_admin_id == auth.admin_id,
        )
        .returning(AdminNotification.id)
    )
    if not result.one_or_none():
        raise HTTPException(status_code=404, detail="Notification not found")
    await session.commit()
    return OkOut()
