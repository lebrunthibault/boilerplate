"""Traces de performance par-requête via ContextVar + décorateur ``@trace_perf``.

On ne mesure que la **vraie durée mur** de chaque appel instrumenté — fiable même quand des
étapes réseau tournent en parallèle — afin de classer et d'agréger les étapes les plus lentes
(à persister par l'appelant s'il le souhaite).

``@trace_perf`` s'utilise exactement comme ``@logfire.instrument`` : on l'empile sur une
fonction async, sans rien changer à son corps.
"""

from __future__ import annotations

import functools
import time
from collections.abc import Awaitable, Callable, Generator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


@dataclass
class PerfTrace:
    """Durée mesurée d'une étape instrumentée.

    Le ``label`` est un libellé clair, et sert aussi de clé d'agrégation côté dashboard.
    ``model`` n'est renseigné que pour les étapes LLM. ``detail`` porte un complément par
    appel (ex. l'URL appelée) pour distinguer plusieurs traces au même ``label`` — libre,
    jamais agrégé.
    """

    label: str
    duration_ms: float
    llm: bool = False
    model: str | None = None
    detail: str | None = None


_perf_traces: ContextVar[list[PerfTrace] | None] = ContextVar("_perf_traces", default=None)


@contextmanager
def capture_perf_traces() -> Generator[list[PerfTrace], None, None]:
    """Collecte les traces de perf le temps d'une requête."""
    traces: list[PerfTrace] = []
    token = _perf_traces.set(traces)
    try:
        yield traces
    finally:
        _perf_traces.reset(token)


def record_perf(
    label: str,
    duration_ms: float,
    llm: bool = False,
    model: str | None = None,
    detail: str | None = None,
) -> None:
    """Ajoute une trace si une capture est active (no-op sinon)."""
    traces = _perf_traces.get(None)
    if traces is None:
        return
    traces.append(
        PerfTrace(label=label, duration_ms=duration_ms, llm=llm, model=model, detail=detail)
    )


def trace_perf(
    label: str,
    llm: bool = False,
    model: str | None = None,
    detail: Callable[..., str | None] | None = None,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Décorateur : mesure le temps mur d'une fonction async et l'enregistre.

    La durée est **toujours** enregistrée, y compris si la fonction lève (la mesure est
    posée dans un ``finally``) — utile pour les étapes fail-open qui ravalent leur erreur.

    ``detail`` est une fonction optionnelle qui reçoit les arguments de l'appel et renvoie un
    complément par trace (ex. l'URL appelée), pour distinguer plusieurs appels au même
    ``label``.
    """

    def decorator(fn: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @functools.wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            t0 = time.monotonic()
            try:
                return await fn(*args, **kwargs)
            finally:
                info = detail(*args, **kwargs) if detail is not None else None
                record_perf(
                    label, (time.monotonic() - t0) * 1000, llm=llm, model=model, detail=info
                )

        return wrapper

    return decorator
