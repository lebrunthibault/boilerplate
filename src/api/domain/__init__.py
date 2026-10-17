"""Couche métier — le cœur du produit, sans état ni base.

Placée entre ``api.app`` (HTTP, persistance, cycle de vie) et ``api.infra`` (base, clients) dans
l'architecture en oignon (cf. ``.importlinter``, ``docs/coding-style.md``). Elle ne connaît ni
FastAPI ni SQLAlchemy : elle reçoit des modèles typés et rend des modèles typés. Un sous-package
par capacité, chacun avec sa façade ``__init__.py``.
"""
