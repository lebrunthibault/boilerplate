"""Crée un compte admin ou pose (remplace) son mot de passe.

Usage :
  python scripts/set_admin_password.py <email>                     # change le mot de passe
  python scripts/set_admin_password.py <email> --create [--name N]  # crée le compte d'abord

Le mot de passe est demandé au TTY (jamais en argument : il resterait dans l'historique
shell), haché en argon2 et écrit dans ``admin.password_hash``. Tant que le hash est NULL,
la connexion est refusée. En prod :
``docker compose exec api python scripts/set_admin_password.py <email> --create``.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
# Avant les imports api : infra/db lit DATABASE_URL à l'import.
load_dotenv()

from api.app.auth import (  # noqa: E402
    AuthEvent,
    AuthEventKind,
    hash_password,
    record_auth_event,
    revoke_all_sessions,
)
from api.infra.db import DATABASE_URL  # noqa: E402
from api.infra.db.models import Admin  # noqa: E402


@dataclass(frozen=True)
class Request:
    """Ce que l'opérateur a demandé."""

    email: str
    password: str
    create: bool
    display_name: str | None


async def _find_or_create(session: AsyncSession, req: Request) -> Admin | None:
    row = await session.execute(select(Admin).where(func.lower(Admin.email) == req.email))
    admin = row.scalar_one_or_none()
    if admin is not None or not req.create:
        return admin
    admin = Admin(email=req.email, display_name=req.display_name, is_active=True)
    session.add(admin)
    await session.flush()
    return admin


async def run(db_url: str, req: Request) -> int:
    engine = create_async_engine(db_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            admin = await _find_or_create(session, req)
            if admin is None:
                print(f"Aucun compte admin pour {req.email} (ajouter --create)", file=sys.stderr)
                return 1
            admin.password_hash = hash_password(req.password)
            # Un changement de mot de passe déconnecte partout : sessions révoquées en masse.
            revoked = await revoke_all_sessions(session, admin.id)
            await session.commit()
            # Journalisé comme les événements d'auth de l'API — sans requête HTTP, donc sans IP.
            await record_auth_event(
                session,
                None,
                AuthEvent(
                    AuthEventKind.SESSIONS_REVOKED,
                    email=admin.email,
                    admin_id=admin.id,
                    detail=f"{revoked} sessions (password change)",
                ),
            )
    finally:
        await engine.dispose()
    print(f"Mot de passe posé pour {req.email} ({revoked} session(s) révoquée(s))")
    return 0


def _ask_password() -> str | None:
    password = getpass.getpass("Mot de passe : ")
    if not password:
        print("Mot de passe vide, abandon", file=sys.stderr)
        return None
    if getpass.getpass("Confirmation : ") != password:
        print("Les deux saisies diffèrent, abandon", file=sys.stderr)
        return None
    return password


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("email")
    parser.add_argument("--create", action="store_true", help="crée le compte s'il n'existe pas")
    parser.add_argument("--name", default=None, help="nom affiché (avec --create)")
    args = parser.parse_args()

    password = _ask_password()
    if password is None:
        return 2

    req = Request(args.email.strip().lower(), password, args.create, args.name)
    return asyncio.run(run(DATABASE_URL, req))


if __name__ == "__main__":
    sys.exit(main())
