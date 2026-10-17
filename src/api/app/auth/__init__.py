"""Authentification (session serveur révocable, comptes en base) — façade publique."""

from __future__ import annotations

from api.app.auth.audit import (
    AuthAudit,
    AuthEvent,
    AuthEventKind,
    purge_auth_events,
    record_auth_event,
)
from api.app.auth.directory import AdminDirectory, AdminRef, load_admin_directory
from api.app.auth.origin import enforce_trusted_origin
from api.app.auth.rate_limit import (
    LoginBucket,
    LoginRateLimit,
    clear_login_failures,
    login_blocked,
    login_bucket,
    record_login_failure,
)
from api.app.auth.service import (
    AuthConfig,
    AuthSession,
    authenticate,
    create_session,
    get_current_session,
    get_current_user,
    hash_password,
    purge_dead_sessions,
    revoke_all_sessions,
    revoke_session,
    session_deadline,
    verify_step_up,
)

__all__ = [
    "AdminDirectory",
    "AdminRef",
    "AuthAudit",
    "AuthConfig",
    "AuthEvent",
    "AuthEventKind",
    "AuthSession",
    "LoginBucket",
    "LoginRateLimit",
    "authenticate",
    "clear_login_failures",
    "create_session",
    "enforce_trusted_origin",
    "get_current_session",
    "get_current_user",
    "hash_password",
    "load_admin_directory",
    "login_blocked",
    "login_bucket",
    "purge_auth_events",
    "purge_dead_sessions",
    "record_auth_event",
    "record_login_failure",
    "revoke_all_sessions",
    "revoke_session",
    "session_deadline",
    "verify_step_up",
]
