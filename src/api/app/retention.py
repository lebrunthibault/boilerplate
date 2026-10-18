"""Purge de conservation (RGPD art. 5.1.e) — un seul point d'entrée pour la boucle quotidienne.

Le socle ne purge que ses propres données (sessions mortes, journal d'authentification, journal
des appels LLM). Les
purges métier s'ajoutent ici, une fonction par famille de données, chacune bornée par une durée
de ``app.config.Retention``.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from api.app.auth import purge_auth_events, purge_dead_sessions
from api.app.llm_calls import purge_llm_calls


@dataclass(frozen=True)
class PurgeReport:
    """Lignes supprimées par un passage de purge."""

    sessions: int
    auth_events: int
    llm_calls: int


async def purge_expired(session: AsyncSession) -> PurgeReport:
    """Supprime tout ce qui a dépassé sa durée de conservation. Chaque purge commit elle-même."""
    sessions = await purge_dead_sessions(session)
    auth_events = await purge_auth_events(session)
    llm_calls = await purge_llm_calls(session)
    return PurgeReport(sessions=sessions, auth_events=auth_events, llm_calls=llm_calls)
