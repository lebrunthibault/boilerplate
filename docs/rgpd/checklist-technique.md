# Checklist RGPD technique

À repasser avant la mise en production, puis à chaque feature qui touche des données
personnelles. Les cases déjà cochées sont couvertes par le socle ; les autres dépendent du métier.

## Accès et autorisation

- [x] Console d'administration derrière une session serveur révocable (`app/auth`)
- [x] Cookie de session httponly, `SameSite=lax`, `Secure` + préfixe `__Host-` en prod
- [x] Limitation des tentatives de connexion (par IP+email et par IP)
- [x] Ré-authentification (step-up) avant tout acte destructeur (`accounts/deactivate` en modèle)
- [x] Garde `Origin` sur les mutations à cookie (CSRF en profondeur)
- [ ] **IDOR** : chaque route qui lit une ressource vérifie qu'elle appartient à l'appelant ; un
      identifiant exposé publiquement est opaque (UUID / jeton), jamais un entier séquentiel
- [ ] Routes publiques : clé API (`require_api_key`) + rate limit (`rate_limit_public`)

## Journaux et observabilité

- [x] Journal d'authentification (qui, quand, d'où), conservation bornée
- [x] Logfire désactivé par défaut ; activé, il ne capture ni corps ni headers HTTP
- [ ] Aucune donnée personnelle métier dans les logs applicatifs (identifiants techniques seuls)

## Conservation et effacement

- [x] Durées centralisées (`app/config.py::Retention`) et purge quotidienne (`app/retention.py`)
- [ ] Une durée par nouvelle famille de données, ajoutée à `Retention` et à la purge
- [ ] Droit à l'effacement outillé : une route admin sous step-up qui supprime toutes les données
      d'une personne, sans journaliser l'identité effacée
- [x] Sauvegardes chiffrées côté client (age), rétention 30 j / 180 j

## Exposition et infrastructure

- [x] Fail-closed en prod : refus de démarrer sans `ALLOWED_ORIGINS` / `SERVICE_API_KEY`
- [x] CORS sans wildcard
- [x] Postgres non exposé (bind `127.0.0.1`) ; HTTPS + HSTS ; en-têtes de sécurité nginx
- [ ] Secrets uniquement dans le `.env` du serveur, jamais dans le dépôt ni dans le bundle front

## Information des personnes

- [ ] Page `/confidentialite` (art. 13) complétée : responsable, finalités, bases légales,
      sous-traitants, transferts, durées, droits
- [ ] Registre (`registre-traitement.md`) aligné sur la page et sur le code

## Souveraineté

- [ ] Hébergement et sauvegardes dans l'UE
- [ ] Chaque prestataire hors UE identifié, transfert encadré (SCC), données minimisées
