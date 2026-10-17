"""Configuration de l'infrastructure (pool de connexions) — une classe par famille, comme
``api.app.config``."""

from __future__ import annotations


class DbPool:
    """Pool asyncpg du moteur SQLAlchemy (infra/db), partagé par les requêtes HTTP et les
    tâches de fond.

    Sans ces bornes : ni ``pool_pre_ping`` (une connexion tuée par un redémarrage de Postgres ne se
    découvrait qu'en levant), ni ``pool_timeout`` explicite (30 s par défaut à attendre un slot),
    ni timeout de connexion ni ``statement_timeout`` (une requête figée gardait sa connexion
    indéfiniment). Les migrations (alembic/env.py) ont leur propre moteur, hors de ces bornes.
    """

    SIZE = 10  # connexions permanentes
    MAX_OVERFLOW = 5  # connexions supplémentaires en pic, refermées ensuite
    RECYCLE_S = 300  # renouvellement d'une connexion (NAT/idle)
    CHECKOUT_TIMEOUT_S = 10  # attente d'un slot libre du pool avant TimeoutError
    CONNECT_TIMEOUT_S = 10  # établissement d'une connexion asyncpg
    STATEMENT_TIMEOUT_MS = 60_000  # côté serveur : une requête plus longue est tuée
