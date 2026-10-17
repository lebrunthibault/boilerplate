"""Rate limit du login admin — fenêtre glissante en mémoire.

Process uvicorn unique : un dict module-level suffit (pas de Redis). Deux seaux par tentative,
cf. ``LoginBucket`` : le couple IP+email et l'IP seule. L'IP est lue par ``client_ip``
(``X-Real-IP`` posé par nginx en prod, repli sur l'adresse de connexion en dev et en test).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from time import monotonic

from fastapi import Request

from api.app.client_ip import client_ip


class LoginRateLimit:
    """Bornes du limiteur : au-delà de ces échecs dans la fenêtre, 429."""

    MAX_FAILURES = 5  # sur le couple IP+email
    MAX_FAILURES_PER_IP = 25  # sur l'IP seule, toutes adresses confondues
    WINDOW_SECONDS = 300
    # Garde-fou mémoire : au-delà, les clés dont la fenêtre est vide sont purgées.
    MAX_TRACKED_KEYS = 1024


@dataclass(frozen=True)
class LoginBucket:
    """Les deux seaux d'une tentative de login : le couple IP+email, et l'IP seule.

    Le seau paire freine le brute-force d'**un** mot de passe sans permettre de verrouiller un
    compte depuis une autre IP. Le seau IP freine le password-spraying — une tentative sur des
    centaines d'adresses différentes, que la paire laisse passer — et borne du même coup le
    nombre de lignes qu'un anonyme peut écrire dans le journal d'authentification.
    """

    pair: str
    ip: str


_failures: dict[str, deque[float]] = {}


def login_bucket(request: Request, email: str) -> LoginBucket:
    """Seaux de la tentative de *email* depuis *request*."""
    ip = client_ip(request) or "?"
    return LoginBucket(pair=f"{ip}|{email.strip().lower()}", ip=ip)


def _prune(attempts: deque[float], now: float) -> None:
    while attempts and now - attempts[0] > LoginRateLimit.WINDOW_SECONDS:
        attempts.popleft()


def _count(key: str) -> int:
    attempts = _failures.get(key)
    if attempts is None:
        return 0
    _prune(attempts, monotonic())
    return len(attempts)


def login_blocked(bucket: LoginBucket) -> bool:
    """Vrai si l'un des deux seaux est plein."""
    return (
        _count(bucket.pair) >= LoginRateLimit.MAX_FAILURES
        or _count(bucket.ip) >= LoginRateLimit.MAX_FAILURES_PER_IP
    )


def record_login_failure(bucket: LoginBucket) -> None:
    """Compte l'échec dans les deux seaux."""
    now = monotonic()
    if len(_failures) >= LoginRateLimit.MAX_TRACKED_KEYS:
        for stale_key, attempts in list(_failures.items()):
            _prune(attempts, now)
            if not attempts:
                del _failures[stale_key]
    for key in (bucket.pair, bucket.ip):
        _failures.setdefault(key, deque()).append(now)


def clear_login_failures(bucket: LoginBucket) -> None:
    """Vide le seau de la paire après un succès — **pas** celui de l'IP.

    Une connexion légitime ne doit pas remettre à zéro le compteur d'une IP qui frappe d'autres
    comptes (poste partagé, NAT d'entreprise) : ce seau-là s'éteint par la fenêtre.
    """
    _failures.pop(bucket.pair, None)
