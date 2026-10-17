"""API FastAPI — point d'entrée (logging, lifespan, CORS, erreurs, routeurs, SPA)."""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from pathlib import Path

import logfire
import sqlalchemy as sa
from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from logfire import LogfireLoggingHandler
from opentelemetry.sdk.trace.sampling import ALWAYS_OFF, ALWAYS_ON, ParentBased, Sampler

load_dotenv()

# Logfire désactivé par défaut : la télémétrie n'est exportée que si LOGFIRE_ENABLED=true est
# explicitement positionné. La seule présence d'un LOGFIRE_TOKEN ne suffit pas à envoyer des
# données. Même activé, on ne capture aucun contenu (cf. bloc ci-dessous : pas de capture_all
# httpx) — uniquement des métadonnées.
_logfire_enabled = os.getenv("LOGFIRE_ENABLED", "").strip().lower() == "true"

_TX_STATEMENTS = frozenset({"BEGIN", "BEGIN;", "COMMIT", "COMMIT;", "ROLLBACK", "ROLLBACK;"})


class _DropTransactionSpans(Sampler):
    """Écarte les spans SQL BEGIN/COMMIT/ROLLBACK : du bruit qui triple le volume exporté."""

    def should_sample(self, parent_context, trace_id, name, *args, **kwargs):
        if name in _TX_STATEMENTS:
            return ALWAYS_OFF.should_sample(parent_context, trace_id, name, *args, **kwargs)
        return ALWAYS_ON.should_sample(parent_context, trace_id, name, *args, **kwargs)

    def get_description(self):
        return "DropTransactionSpans"


if _logfire_enabled:
    logfire.configure(
        send_to_logfire=True,
        sampling=logfire.SamplingOptions(head=ParentBased(_DropTransactionSpans())),
    )
    # Volontairement PAS de capture_all=True : il exporterait les corps et headers de toutes les
    # requêtes HTTP sortantes vers Logfire. On ne conserve que des métadonnées (URL, statut,
    # durée) et les spans SQL sans paramètres.
    logfire.instrument_httpx()
    logfire.instrument_asyncpg()
else:
    logfire.configure(send_to_logfire=False)

_handlers: list[logging.Handler] = [logging.StreamHandler()]
if _logfire_enabled:
    _handlers.append(LogfireLoggingHandler())

logging.basicConfig(
    handlers=_handlers,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)

# Variables exigées en prod (fail-closed) : refuser de démarrer plutôt que de servir dégradé
# (CORS wildcard, route publique ouverte). Pas de SECRET_KEY : les sessions admin sont des
# jetons opaques en base, sans secret de signature.
_PROD_REQUIRED_ENV = ("ALLOWED_ORIGINS", "SERVICE_API_KEY")


async def _retention_loop() -> None:
    """Purge de conservation quotidienne (prod). Premier passage peu après le démarrage."""
    from api.app.config import Retention
    from api.app.retention import purge_expired
    from api.infra.db import _session_factory

    while True:
        try:
            if _session_factory is not None:
                async with _session_factory() as session:
                    await purge_expired(session)
        except Exception:
            logging.getLogger(__name__).exception("retention purge failed")
        await asyncio.sleep(Retention.PURGE_INTERVAL.total_seconds())


@asynccontextmanager
async def lifespan(app: FastAPI):
    from api.app.environment import IS_PROD

    if IS_PROD:
        prod_missing = [k for k in _PROD_REQUIRED_ENV if not os.getenv(k)]
        if prod_missing:
            raise RuntimeError(
                "Production (APP_ENV=production) requires these environment variables "
                f"(fail-closed): {', '.join(prod_missing)}"
            )

    # Warm up DB connection pool so first request isn't slow
    from api.infra.db import engine

    if engine:
        async with engine.connect() as conn:
            await conn.execute(sa.text("SELECT 1"))

    # Purge de conservation (RGPD) : tâche de fond quotidienne, en prod uniquement.
    retention_task = asyncio.create_task(_retention_loop()) if IS_PROD else None

    yield

    if retention_task is not None:
        retention_task.cancel()

    if engine:
        await engine.dispose()


try:
    _version = _pkg_version("boilerplate")
except PackageNotFoundError:
    _version = "0.0.0-dev"

app = FastAPI(title="Boilerplate", version=_version, lifespan=lifespan)
if _logfire_enabled:
    logfire.instrument_fastapi(app)

# CORS middleware - environment-specific origins
# La liste vit dans app/environment.py : elle sert aussi à la garde Origin des routes à cookie
# (app/auth/origin.py). Jamais de fallback wildcard "*" (qui ouvrirait l'API en cross-origin à
# tout site web) ; en prod, ALLOWED_ORIGINS est requis (cf. lifespan, fail-closed), le frontend
# étant servi en same-origin derrière nginx.
from api.app.environment import ALLOWED_ORIGINS  # noqa: E402

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
    max_age=3600,
)

# Custom exception handlers for consistent error responses


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    details = [
        {
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": details,
            }
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    logging.getLogger(__name__).exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": [],
            }
        },
    )


from api.app.auth import enforce_trusted_origin, get_current_user  # noqa: E402
from api.app.auth.routes import router as auth_router  # noqa: E402
from api.app.router import admin_router, public_router  # noqa: E402

# Garde Origin sur les deux routeurs à cookie (défense CSRF en profondeur) — le routeur public
# n'est jamais authentifié par cookie : pas d'authentification ambiante, donc rien à protéger.
# Origine d'abord sur l'admin : une requête cross-origin est refusée sans toucher la base.
app.include_router(auth_router, prefix="/api", dependencies=[Depends(enforce_trusted_origin)])
app.include_router(public_router, prefix="/api")
app.include_router(
    admin_router,
    prefix="/api",
    dependencies=[Depends(enforce_trusted_origin), Depends(get_current_user)],
)

# Serve built frontend in production (after API routes so they take priority)
_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _dist.is_dir():
    from fastapi.responses import FileResponse

    _index = _dist / "index.html"

    # Serve static assets (JS, CSS, images) normally
    app.mount("/assets", StaticFiles(directory=str(_dist / "assets")), name="assets")

    # SPA fallback: serve index.html for all non-API routes
    @app.get("/{path:path}", include_in_schema=False)
    async def spa_fallback(path: str):
        file = _dist / path
        if file.is_file():
            return FileResponse(file)
        return FileResponse(_index)
