"""Endpoints admin de gestion des comptes du dashboard."""

from __future__ import annotations

import math
from dataclasses import replace
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.auth import (
    AuthEvent,
    AuthEventKind,
    AuthSession,
    get_current_session,
    login_blocked,
    login_bucket,
    record_auth_event,
    record_login_failure,
    revoke_all_sessions,
    verify_step_up,
)
from api.app.config import AccountsPage
from api.infra.db import get_session
from api.infra.db.models import Admin

router = APIRouter()

# Acte tracé par le step-up, tel qu'il apparaît dans le journal (contexte non nominatif).
_DEACTIVATE_ACT = "accounts/deactivate"


class AccountOut(BaseModel):
    """Un compte admin tel que la liste l'affiche — jamais le hash du mot de passe."""

    id: int
    email: str
    display_name: str | None
    is_active: bool
    has_password: bool
    is_me: bool
    created_at: datetime
    last_login_at: datetime | None


class AccountPage(BaseModel):
    """Page de comptes — même enveloppe que ``GET /auth/events``."""

    items: list[AccountOut]
    total: int
    page: int
    per_page: int
    pages: int


@router.get("/accounts")
async def list_accounts(
    page: int = Query(1, ge=1),
    per_page: int = Query(AccountsPage.SIZE, ge=1, le=AccountsPage.SIZE_MAX),
    auth: AuthSession = Depends(get_current_session),
    session: AsyncSession = Depends(get_session),
) -> AccountPage:
    total = (await session.execute(select(func.count()).select_from(Admin))).scalar_one()
    rows = await session.execute(
        select(Admin)
        .order_by(Admin.last_login_at.desc().nulls_last(), Admin.id)
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    items = [
        AccountOut(
            id=a.id,
            email=a.email,
            display_name=a.display_name,
            is_active=a.is_active,
            has_password=a.password_hash is not None,
            is_me=a.id == auth.admin_id,
            created_at=a.created_at,
            last_login_at=a.last_login_at,
        )
        for a in rows.scalars()
    ]
    pages = math.ceil(total / per_page) if total else 0
    return AccountPage(items=items, total=total, page=page, per_page=per_page, pages=pages)


class StepUpProof(BaseModel):
    """Ré-authentification exigée pour un acte destructeur, session valide ou pas.

    method="password" aujourd'hui ; une passkey pourra ajouter method="passkey" (assertion
    WebAuthn) sans toucher au reste du contrat.
    """

    method: Literal["password"]
    password: str


class DeactivateRequest(BaseModel):
    confirmation: StepUpProof


class DeactivateOut(BaseModel):
    ok: bool
    revoked_sessions: int


@router.post("/accounts/{account_id}/deactivate")
async def deactivate_account(
    account_id: int,
    body: DeactivateRequest,
    request: Request,
    auth: AuthSession = Depends(get_current_session),
    session: AsyncSession = Depends(get_session),
) -> DeactivateOut:
    """Désactive un compte admin et coupe ses sessions — modèle de tout acte sous step-up.

    Step-up : le mot de passe de l'admin appelant est re-vérifié même en session valide — un
    cookie volé ne suffit pas. Les échecs partagent le seau du login (même credential
    brute-forcé) : 5 mots de passe faux bloquent aussi le login 5 min pour ce couple IP/email.
    """
    if account_id == auth.admin_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate yourself")

    bucket = login_bucket(request, auth.email)
    step_up = AuthEvent(
        AuthEventKind.STEP_UP_FAILURE,
        email=auth.email,
        admin_id=auth.admin_id,
        detail=_DEACTIVATE_ACT,
    )
    if login_blocked(bucket):
        await record_auth_event(
            session, request, replace(step_up, kind=AuthEventKind.LOGIN_BLOCKED)
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts, retry later",
        )
    if not await verify_step_up(session, auth.admin_id, body.confirmation.password):
        record_login_failure(bucket)
        await record_auth_event(session, request, step_up)
        # 403, jamais 401 : le front traite tout 401 comme une session morte et déconnecte.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid password")

    target = await session.get(Admin, account_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    target.is_active = False
    revoked = await revoke_all_sessions(session, account_id)
    await session.commit()
    await record_auth_event(session, request, replace(step_up, kind=AuthEventKind.STEP_UP_SUCCESS))
    return DeactivateOut(ok=True, revoked_sessions=revoked)
