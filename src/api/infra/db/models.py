"""ORM models du socle : comptes admin, sessions, journal d'authentification, notifications."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    desc,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from api.infra.db import Base


class Admin(Base):
    """Compte administrateur de la plateforme (dashboard).

    Les admins se connectent par email + mot de passe. ``password_hash`` (argon2) nullable =
    compte provisionné mais connexion impossible tant qu'un mot de passe n'a pas été posé
    (cf. ``scripts/set_admin_password.py``).
    """

    __tablename__ = "admin"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AdminSession(Base):
    """Session serveur d'un compte admin (cookie opaque, hash sha256 en base).

    Le cookie ne porte qu'un aléa de 256 bits ; seule son empreinte est stockée — un dump
    de la base ne permet pas de rejouer une session. Expire par inactivité (last_seen_at)
    ou durée absolue (created_at), cf. AuthConfig. ``revoked_at`` posé au logout ou au
    changement de mot de passe = révocation immédiate.
    """

    __tablename__ = "admin_session"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("admin.id"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AdminAuthEvent(Base):
    """Journal des événements d'authentification du dashboard (piste d'audit).

    Une ligne par événement notable de la vie d'une session admin : connexion réussie ou
    refusée, blocage par le limiteur, déconnexion, révocation en masse, step-up accepté ou
    refusé. ``admin_id`` est NULL quand aucun compte ne correspond à l'adresse tentée — seul
    cas, et raison pour laquelle ``email`` est stocké à part : c'est l'adresse *tentée*,
    normalisée en minuscules et tronquée à la longueur de colonne.

    Écrit une fois, jamais mis à jour, jamais relu par le code : la seule lecture est humaine
    (écran « Sécurité »). Conservation bornée par ``Retention.AUTH_EVENTS``, appliquée par la
    purge quotidienne.
    """

    __tablename__ = "admin_auth_event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Posé en Python : le SQLite des tests ne remplit pas les server_default sans refresh
    # (même raison que create_session, cf. app/auth/service.py).
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    admin_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("admin.id"), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    # 45 caractères = longueur maximale d'une IPv6 en notation textuelle.
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Contexte court et non nominatif (« accounts/deactivate », « 3 sessions ») — jamais de
    # donnée personnelle d'un tiers : le journal survit à un effacement RGPD.
    detail: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (Index("ix_admin_auth_event_occurred_at", "occurred_at"),)


class AdminNotification(Base):
    """One inbox line for one admin: "this happened on that target".

    One row **per recipient** (write-time fan-out): ``read_at`` and the delete action are
    per-admin, so they cannot live on a shared event row. The target is generic — a
    ``target_type`` ("invoice", "ticket"…) and its id — so the socle never holds a foreign key
    into a business table. ``title`` / ``preview`` are copied at write time; ``payload`` carries
    whatever structured context the kind needs, and is the merge point when repeated updates
    fold into one unread row (cf. service).
    """

    __tablename__ = "admin_notification"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recipient_admin_id: Mapped[int] = mapped_column(Integer, ForeignKey("admin.id"), nullable=False)
    # NULL quand l'acteur n'est pas un admin (événement système, action d'un utilisateur final) :
    # personne n'est alors exclu du fan-out.
    actor_admin_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("admin.id"), nullable=True
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preview: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_admin_notification_inbox", "recipient_admin_id", desc("created_at")),
    )
