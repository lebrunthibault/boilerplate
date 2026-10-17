"""Boîte de réception admin : fan-out vers les autres admins, lecture, pliage, suppression."""

from __future__ import annotations

from sqlalchemy import select

from api.app.notifications import NotificationEvent, notify_admins
from api.infra.db.models import AdminNotification
from tests.conftest import SeededAdmins


async def test_actor_is_never_notified(admins: SeededAdmins, db_session):
    await notify_admins(
        db_session,
        NotificationEvent(kind="item_created", actor_admin_id=admins.other.id, title="Item 1"),
    )
    await db_session.commit()

    rows = (await db_session.execute(select(AdminNotification))).scalars().all()
    assert [r.recipient_admin_id for r in rows] == [admins.me.id]


async def test_event_without_actor_reaches_every_admin(admins: SeededAdmins, db_session):
    await notify_admins(db_session, NotificationEvent(kind="system_alert", title="Disk"))
    await db_session.commit()

    rows = (await db_session.execute(select(AdminNotification))).scalars().all()
    assert {r.recipient_admin_id for r in rows} == {admins.me.id, admins.other.id}


async def test_inbox_lists_and_counts_unread(admins: SeededAdmins, db_session):
    await notify_admins(
        db_session,
        NotificationEvent(
            kind="item_created",
            actor_admin_id=admins.other.id,
            target_type="item",
            target_id=7,
            title="Item 7",
            preview="x" * 500,
        ),
    )
    await db_session.commit()

    body = (await admins.client.get("/api/notifications")).json()

    assert body["unread"] == 1
    item = body["items"][0]
    assert item["actor"]["is_me"] is False
    assert item["target_type"] == "item" and item["target_id"] == 7
    assert item["preview"].endswith("…")


async def test_fold_merges_repeated_updates(admins: SeededAdmins, db_session):
    for value in ("20", "30"):
        await notify_admins(
            db_session,
            NotificationEvent(
                kind="item_updated",
                actor_admin_id=admins.other.id,
                target_type="item",
                target_id=1,
                payload={"score": value},
                fold=True,
            ),
        )
        await db_session.commit()

    rows = (await db_session.execute(select(AdminNotification))).scalars().all()
    assert len(rows) == 1
    assert rows[0].payload == {"score": "30"}


async def test_read_then_delete_own_row_only(admins: SeededAdmins, db_session):
    await notify_admins(db_session, NotificationEvent(kind="system_alert"))
    await db_session.commit()
    rows = (await db_session.execute(select(AdminNotification))).scalars().all()
    mine = next(r for r in rows if r.recipient_admin_id == admins.me.id)
    theirs = next(r for r in rows if r.recipient_admin_id == admins.other.id)

    assert (await admins.client.patch(f"/api/notifications/{mine.id}", json={"read": True})).json()
    assert (await admins.client.get("/api/notifications")).json()["unread"] == 0
    assert (await admins.client.delete(f"/api/notifications/{theirs.id}")).status_code == 404
    assert (await admins.client.delete(f"/api/notifications/{mine.id}")).status_code == 200
