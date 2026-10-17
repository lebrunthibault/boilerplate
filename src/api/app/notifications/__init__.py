"""Admin inbox — events fanned out to the other admins. Public façade."""

from api.app.notifications.routes import router
from api.app.notifications.service import NotificationEvent, notify_admins

__all__ = ["NotificationEvent", "notify_admins", "router"]
