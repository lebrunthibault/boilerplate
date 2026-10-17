"""Naming admins in payloads: who wrote this, and is it me?

The admin identity is owned by this package, so the shape every other package uses to point
at an admin lives here too — rather than each of them re-reading the ``admin`` table.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.infra.db.models import Admin


class AdminRef(BaseModel):
    """An admin as displayed next to what they did.

    ``is_me`` is resolved server-side from the caller's session: the SPA never has to know
    who it is logged in as to style its own messages.
    """

    id: int
    display_name: str | None
    email: str
    is_me: bool


@dataclass(frozen=True)
class AdminDirectory:
    """The admins referenced by one payload, resolved in a single query."""

    by_id: dict[int, Admin]
    viewer_id: int

    def ref(self, admin_id: int | None) -> AdminRef | None:
        """The reference to display, or None — an unknown id reads as "no author"."""
        admin = self.by_id.get(admin_id) if admin_id is not None else None
        if admin is None:
            return None
        return AdminRef(
            id=admin.id,
            display_name=admin.display_name,
            email=admin.email,
            is_me=admin.id == self.viewer_id,
        )


async def load_admin_directory(
    session: AsyncSession, viewer_id: int, admin_ids: set[int | None]
) -> AdminDirectory:
    """Load the named admins at once. An empty set still yields a usable directory."""
    wanted = {a for a in admin_ids if a is not None}
    if not wanted:
        return AdminDirectory({}, viewer_id)
    rows = await session.execute(select(Admin).where(Admin.id.in_(wanted)))
    return AdminDirectory({a.id: a for a in rows.scalars()}, viewer_id)
