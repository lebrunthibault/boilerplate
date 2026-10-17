"""Session admin révocable : cookie opaque, table ``admin_session``, comptes en base.

Le cookie ne porte qu'un aléa de 256 bits ; la base ne stocke que son empreinte sha256.
Chaque requête admin vérifie la ligne (révocation, inactivité, plafond absolu, compte
actif) — révoquer une session ou désactiver un compte coupe l'accès immédiatement.
"""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.environment import IS_PROD
from api.infra.db import get_session
from api.infra.db.models import Admin, AdminSession


class AuthConfig:
    """Paramètres de la session admin — une seule source pour cookie + expiration."""

    # __Host- exige Secure + Path=/ + pas de Domain : impossible sur http://localhost,
    # donc le préfixe ne s'applique qu'en prod.
    COOKIE_NAME = "__Host-admin_session" if IS_PROD else "admin_session"
    IDLE_TIMEOUT = timedelta(minutes=60)  # inactivité → re-login
    ABSOLUTE_LIFETIME = timedelta(hours=12)  # plafond dur, non renouvelable
    TOUCH_MIN_INTERVAL = timedelta(seconds=60)  # écriture de last_seen_at au plus 1×/min
    TOKEN_BYTES = 32  # 256 bits d'aléa


_hasher = PasswordHasher()

# Hash factice vérifié quand le compte est introuvable/inutilisable : le temps de réponse
# ne trahit pas l'existence du compte (l'échec reste indistinct, cf. authenticate).
_DUMMY_HASH = _hasher.hash("dummy-password-for-constant-timing")


@dataclass(frozen=True)
class AuthSession:
    """Session portée par le cookie d'une requête authentifiée."""

    admin_id: int
    email: str
    expires_at: datetime


def _verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


async def authenticate(session: AsyncSession, email: str, password: str) -> Admin | None:
    """Vérifie email + mot de passe et rend le compte actif correspondant, sinon None.

    Échec indistinct — email inconnu, compte inactif, hash absent ou mauvais mot de
    passe rendent tous None (et coûtent tous une vérification argon2). Met à jour
    ``last_login_at`` ; le commit reste à la charge de l'appelant.
    """
    normalized = email.strip().lower()
    row = await session.execute(select(Admin).where(func.lower(Admin.email) == normalized))
    admin = row.scalar_one_or_none()

    if admin is None or not admin.is_active or not admin.password_hash:
        _verify_password(_DUMMY_HASH, password)
        return None
    if not _verify_password(admin.password_hash, password):
        return None

    admin.last_login_at = datetime.now(UTC)
    return admin


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _as_utc(dt: datetime) -> datetime:
    # SQLite (tests) rend les DateTime(timezone=True) naïfs : on les re-marque UTC.
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt


def session_deadline(row: AdminSession) -> datetime:
    """Échéance effective : la plus proche entre inactivité et plafond absolu."""
    return min(
        _as_utc(row.last_seen_at) + AuthConfig.IDLE_TIMEOUT,
        _as_utc(row.created_at) + AuthConfig.ABSOLUTE_LIFETIME,
    )


def create_session(db: AsyncSession, admin: Admin) -> tuple[str, AdminSession]:
    """Crée une session pour *admin* et rend (jeton brut pour le cookie, ligne).

    Le jeton brut n'est jamais stocké — seule son empreinte. Les horodatages sont posés
    en Python (le SQLite des tests ne remplit pas les server_default sans refresh).
    Le commit reste à la charge de l'appelant.
    """
    raw = secrets.token_urlsafe(AuthConfig.TOKEN_BYTES)
    now = datetime.now(UTC)
    row = AdminSession(
        admin_id=admin.id, token_hash=_hash_token(raw), created_at=now, last_seen_at=now
    )
    db.add(row)
    return raw, row


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


async def get_current_session(
    request: Request, db: AsyncSession = Depends(get_session)
) -> AuthSession:
    """Garde des routes admin : vérifie le cookie contre la table ``admin_session``.

    Un seul détail (« Session expired ») pour toutes les sessions mortes — révoquée,
    inactive trop longtemps, plafond atteint ou compte désactivé : le porteur d'un
    cookie révoqué n'apprend rien de plus. Rafraîchit ``last_seen_at`` au passage,
    au plus une fois par TOUCH_MIN_INTERVAL (commit en cours de requête, délibéré —
    la factory est en expire_on_commit=False).
    """
    token = request.cookies.get(AuthConfig.COOKIE_NAME)
    if not token:
        raise _unauthorized("Not authenticated")

    result = await db.execute(
        select(AdminSession, Admin)
        .join(Admin, Admin.id == AdminSession.admin_id)
        .where(AdminSession.token_hash == _hash_token(token))
    )
    pair = result.one_or_none()
    if pair is None:
        raise _unauthorized("Invalid session")
    row, admin = pair

    now = datetime.now(UTC)
    dead = (
        row.revoked_at is not None
        or now - _as_utc(row.last_seen_at) > AuthConfig.IDLE_TIMEOUT
        or now - _as_utc(row.created_at) > AuthConfig.ABSOLUTE_LIFETIME
        or not admin.is_active
    )
    if dead:
        raise _unauthorized("Session expired")

    if now - _as_utc(row.last_seen_at) > AuthConfig.TOUCH_MIN_INTERVAL:
        row.last_seen_at = now
        await db.commit()

    return AuthSession(admin.id, admin.email, session_deadline(row))


async def get_current_user(auth: AuthSession = Depends(get_current_session)) -> str:
    return auth.email


async def revoke_session(db: AsyncSession, raw_token: str) -> int | None:
    """Révoque la session portant *raw_token* et rend son ``admin_id``, sinon None.

    Idempotent, silencieux si la session est inconnue ou déjà révoquée. L'``admin_id`` est rendu
    pour que le logout puisse journaliser *qui* s'est déconnecté : il ne dispose que du jeton
    brut. Le commit reste à la charge de l'appelant.
    """
    token_hash = _hash_token(raw_token)
    row = await db.execute(select(AdminSession).where(AdminSession.token_hash == token_hash))
    session_row = row.scalar_one_or_none()
    if session_row is None:
        return None
    if session_row.revoked_at is None:
        session_row.revoked_at = datetime.now(UTC)
    return session_row.admin_id


async def revoke_all_sessions(db: AsyncSession, admin_id: int) -> int:
    """Révoque toutes les sessions vivantes d'un admin (changement de mot de passe).

    Rend le nombre de sessions révoquées ; le commit reste à la charge de l'appelant.
    """
    result = await db.execute(
        update(AdminSession)
        .where(AdminSession.admin_id == admin_id)
        .where(AdminSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    # Un execute DML rend en pratique un CursorResult (porteur de rowcount) ; le type
    # statique Result[Any] ne le sait pas.
    return cast(CursorResult[Any], result).rowcount or 0


async def verify_step_up(db: AsyncSession, admin_id: int, password: str) -> bool:
    """Re-vérifie le mot de passe d'un admin en session (step-up sur acte destructeur).

    Même discipline de timing qu'``authenticate`` : un compte devenu inutilisable coûte
    quand même une vérification argon2.
    """
    row = await db.execute(select(Admin).where(Admin.id == admin_id))
    admin = row.scalar_one_or_none()
    if admin is None or not admin.is_active or not admin.password_hash:
        _verify_password(_DUMMY_HASH, password)
        return False
    return _verify_password(admin.password_hash, password)


async def purge_dead_sessions(db: AsyncSession) -> int:
    """Supprime les sessions révoquées ou expirées (appelé par la purge quotidienne).

    Commit lui-même : il tourne dans sa propre session de fond, pas dans une requête.
    """
    now = datetime.now(UTC)
    result = await db.execute(
        delete(AdminSession).where(
            or_(
                AdminSession.revoked_at.is_not(None),
                AdminSession.last_seen_at < now - AuthConfig.IDLE_TIMEOUT,
                AdminSession.created_at < now - AuthConfig.ABSOLUTE_LIFETIME,
            )
        )
    )
    await db.commit()
    return cast(CursorResult[Any], result).rowcount or 0


def hash_password(password: str) -> str:
    """Hache un mot de passe pour ``admin.password_hash`` (bootstrap et tests)."""
    return _hasher.hash(password)
