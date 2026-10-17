"""Détection de l'environnement d'exécution (runtime) — source unique de vérité.

``APP_ENV=production`` sur le serveur de prod ; ``local`` (défaut) en dev et en test.
Sert à durcir la prod : cookie de session ``Secure`` + préfixe ``__Host-``, rate limit des routes
publiques, purge de rétention, refus de démarrer sans ``ALLOWED_ORIGINS`` ni ``SERVICE_API_KEY``
(fail-closed).

Deux garde-fous encadrent cette variable, parce qu'une prod qui se croit en dev ne fait aucun
bruit : ``docker-compose.prod.yml`` la pose lui-même (la prod-ité vient de l'artefact déployé,
plus d'une ligne du ``.env`` du serveur non suivie en git), et ``deploy.sh`` refuse de déployer
si le ``.env`` prod ne la porte pas exactement. Ici, une valeur *inconnue* (« prod », « PROD-1 »)
empêche le démarrage plutôt que de dégrader la sécurité en silence.
"""

from __future__ import annotations

import os

VALID_APP_ENVS = frozenset({"production", "local", "test"})

APP_ENV = os.environ.get("APP_ENV", "").strip().lower() or "local"
if APP_ENV not in VALID_APP_ENVS:
    raise RuntimeError(
        f"APP_ENV={APP_ENV!r} inconnu — valeurs acceptées : {sorted(VALID_APP_ENVS)}"
    )

IS_PROD = APP_ENV == "production"

# Origines externes autorisées à parler à l'API. En prod le SPA est servi en same-origin derrière
# nginx : la liste ne couvre donc que les origines *externes* légitimes (dev local par défaut).
# Une seule source pour le CORS (``main.py``) et pour la garde Origin des routes à cookie
# (``app/auth/origin.py``) — deux listes dériveraient. Jamais de repli wildcard : sans
# configuration, seules les origines de dev local sont acceptées, et le ``lifespan`` refuse de
# démarrer en prod si la variable est absente.
_DEV_ORIGINS = ["http://localhost:5173", "http://localhost:3000", "https://localhost:3000"]

ALLOWED_ORIGINS: list[str] = [
    origin.strip() for origin in os.environ.get("ALLOWED_ORIGINS", "").split(",") if origin.strip()
] or _DEV_ORIGINS
