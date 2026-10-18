"""Valeurs de configuration de la couche app — une classe par famille, une valeur un endroit."""

from __future__ import annotations

from datetime import timedelta


class NotificationLimits:
    """Boîte de réception admin — plafonds de lecture."""

    # Lignes rendues par GET /notifications quand l'appelant n'impose pas de limite.
    LIST_DEFAULT = 50
    LIST_MAX = 200
    # Aperçu servi à la liste : tronqué côté serveur, la ligne ne l'affiche que sur un rang.
    PREVIEW_CHARS = 200


class AccountsPage:
    """Pagination de la liste des comptes admin."""

    SIZE = 25
    SIZE_MAX = 100


class LlmCallsPage:
    """Pagination du journal des appels LLM."""

    SIZE = 25
    SIZE_MAX = 100


# --- Conservation des données personnelles (RGPD) ----------------------------


class Retention:
    """Durées de conservation (RGPD art. 5.1.e) — la purge quotidienne s'y réfère seule.

    Politique de confidentialité, pas des fenêtres du runtime : elles ne bougent qu'avec la
    notice publiée (``ConfidentialitePage.vue``) et le registre (``docs/rgpd/``).
    """

    # Journal d'authentification admin (app/auth/audit.py) : un an, la norme française pour les
    # logs de connexion. Assez long pour enquêter sur une intrusion découverte tardivement,
    # assez court pour ne pas accumuler indéfiniment des IP d'administrateurs.
    AUTH_EVENTS = timedelta(days=365)  # 12 mois

    # Journal des appels LLM (app/llm_calls) : l'input envoyé au modèle peut contenir des données
    # personnelles. 90 jours suffisent pour déboguer un prompt et suivre les coûts ; à ajuster
    # avec la finalité réelle (et à reporter dans le registre).
    LLM_CALLS = timedelta(days=90)

    # Cadence de la boucle de purge (main.py::_retention_loop).
    PURGE_INTERVAL = timedelta(days=1)
