"""Auth routes: login, logout, me, audit trail."""

import math

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.auth import (
    AuthAudit,
    AuthConfig,
    AuthEvent,
    AuthEventKind,
    AuthSession,
    authenticate,
    clear_login_failures,
    create_session,
    get_current_session,
    login_blocked,
    login_bucket,
    record_auth_event,
    record_login_failure,
    revoke_session,
    session_deadline,
)
from api.app.environment import IS_PROD
from api.infra.db import get_session
from api.infra.db.models import Admin, AdminAuthEvent

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    # Bornes de longueur : l'adresse tentée part dans le journal d'authentification (colonne de
    # 320 caractères) et un mot de passe de plusieurs mégaoctets ne coûterait qu'un hachage argon2.
    email: str = Field(max_length=320)
    password: str = Field(max_length=1024)


@router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    bucket = login_bucket(request, body.email)
    if login_blocked(bucket):
        await record_auth_event(
            session, request, AuthEvent(AuthEventKind.LOGIN_BLOCKED, email=body.email)
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts, retry later",
        )
    admin = await authenticate(session, body.email, body.password)
    if admin is None:
        record_login_failure(bucket)
        # Le journal est écrit avant le 401 : record_auth_event commit lui-même, sinon la ligne
        # partirait avec le rollback de l'exception.
        await record_auth_event(
            session, request, AuthEvent(AuthEventKind.LOGIN_FAILURE, email=body.email)
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    clear_login_failures(bucket)
    raw, row = create_session(session, admin)
    # get_session ne commit pas : sans ceci, last_login_at et la session seraient perdus.
    await session.commit()
    # Échéance lue avant le journal : si l'écriture du journal échoue, son rollback expire les
    # objets de la session et relire `row` déclencherait un lazy load hors contexte.
    expires_at = session_deadline(row)
    await record_auth_event(
        session,
        request,
        AuthEvent(AuthEventKind.LOGIN_SUCCESS, email=admin.email, admin_id=admin.id),
    )
    response.set_cookie(
        key=AuthConfig.COOKIE_NAME,
        value=raw,
        httponly=True,
        secure=IS_PROD,
        samesite="lax",
        max_age=int(AuthConfig.ABSOLUTE_LIFETIME.total_seconds()),
        path="/",
    )
    # expires_at : le cookie est httponly, le SPA ne peut pas lire l'échéance. On lui rend
    # l'échéance effective (glissante : elle recule à chaque /me tant que la session vit)
    # pour qu'il renvoie vers /login à l'expiration au lieu de découvrir la session morte
    # sur un appel API qui échoue.
    return {"ok": True, "expires_at": expires_at.isoformat()}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    # Sans auth exigée : révoquer une session déjà morte reste un no-op idempotent.
    raw = request.cookies.get(AuthConfig.COOKIE_NAME)
    if raw:
        admin_id = await revoke_session(session, raw)
        await session.commit()
        if admin_id is not None:
            await record_auth_event(
                session, request, AuthEvent(AuthEventKind.LOGOUT, admin_id=admin_id)
            )
    response.delete_cookie(key=AuthConfig.COOKIE_NAME, path="/")
    # Cookie JWT d'avant la bascule en sessions serveur : nettoyé au passage.
    response.delete_cookie(key="access_token", path="/")
    return {"ok": True}


@router.get("/me")
async def me(
    auth: AuthSession = Depends(get_current_session),
    session: AsyncSession = Depends(get_session),
):
    # display_name relu en base : la session ne porte que id + email.
    row = await session.execute(select(Admin.display_name).where(Admin.id == auth.admin_id))
    display_name = row.scalar_one_or_none()
    return {
        "email": auth.email,
        "display_name": display_name,
        "expires_at": auth.expires_at.isoformat(),
    }


class AuthEventItem(BaseModel):
    """Une ligne du journal, telle que l'écran « Sécurité » l'affiche.

    ``email`` = l'adresse *tentée* si elle a été stockée, sinon celle du compte concerné, jointe
    à la lecture : une déconnexion ne connaît que son ``admin_id`` et doit quand même nommer
    quelqu'un à l'écran.
    """

    id: int
    occurred_at: str
    kind: str
    email: str | None
    admin_id: int | None
    ip: str | None
    user_agent: str | None
    detail: str | None


class AuthEventPage(BaseModel):
    """Page du journal — même enveloppe que ``GET /users``."""

    items: list[AuthEventItem]
    total: int
    page: int
    per_page: int
    pages: int


@router.get("/events")
async def list_auth_events(
    page: int = Query(1, ge=1),
    per_page: int = Query(AuthAudit.PAGE_SIZE, ge=1, le=AuthAudit.PAGE_SIZE_MAX),
    kind: str | None = Query(None, max_length=32),
    auth: AuthSession = Depends(get_current_session),
    session: AsyncSession = Depends(get_session),
) -> AuthEventPage:
    """Journal d'authentification, du plus récent au plus ancien.

    Garde explicite (``get_current_session``) : le routeur ``auth`` n'a pas de dépendance
    globale, il porte le login et le logout. *auth* n'est pas relu — il n'y a pas de rôles, tout
    admin connecté lit le journal entier.
    """
    conditions = [AdminAuthEvent.kind == kind] if kind else []
    total_row = await session.execute(
        select(func.count()).select_from(AdminAuthEvent).where(*conditions)
    )
    total = total_row.scalar_one()
    rows = await session.execute(
        select(AdminAuthEvent, Admin.email)
        .outerjoin(Admin, Admin.id == AdminAuthEvent.admin_id)
        .where(*conditions)
        .order_by(AdminAuthEvent.occurred_at.desc(), AdminAuthEvent.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    return AuthEventPage(
        items=[
            AuthEventItem(
                id=row.id,
                occurred_at=row.occurred_at.isoformat(),
                kind=row.kind,
                email=row.email or admin_email,
                admin_id=row.admin_id,
                ip=row.ip,
                user_agent=row.user_agent,
                detail=row.detail,
            )
            for row, admin_email in rows
        ],
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total else 0,
    )
