# Boilerplate

## Prod

- **SSH** : `ssh <alias-ssh>` *(à renseigner)*
- **Répertoire** : `/opt/boilerplate`
- **Déploiement** : `git push` sur `main` → la CI teste puis lance `deploy.sh` sur le serveur.

## Git

- **Toujours travailler sur `main`.** Ne jamais créer de branche.

## Spec-driven workflow

Avant toute tâche de dev, lire `docs/specs/in-progress/` pour le contexte courant.

Pour démarrer une feature, prendre une spec dans `docs/specs/todo/` et la déplacer
en `docs/specs/in-progress/` via `git mv` ; une fois le travail mergé, la déplacer
en `docs/specs/done/`.

Voir `docs/specs/README.md` pour le cycle de vie complet (modèle : `docs/specs/_template.md`).

## Conventions de code

**Référence complète (macro + micro) : [`docs/coding-style.md`](docs/coding-style.md)** — à
respecter pour toute grosse feature ou spec. Architecture en oignon `app → domain → infra`,
façade par package (pas d'import de sous-fichiers), modèles proches de leur usage, vocabulaire du
domaine.

**Vocabulaire du domaine (ubiquitous language) : [`docs/vocabulary.md`](docs/vocabulary.md)** — un
concept = un seul nom, le même dans le code, les specs, la doc, le frontend et les commentaires.
Bannir les noms inventés ou vagues : nommer par la responsabilité.

Rappel des règles micro les plus structurantes :

- **Jamais de `dict` comme type pour des données structurées** : pas de `-> dict`
  ni `: dict` pour représenter une entité. Utiliser une `@dataclass` typée (ou un
  modèle Pydantic aux frontières HTTP). Les vrais mappings homogènes
  (`dict[str, int]`) restent OK.
- **Pas de séparateur keyword-only `*`** dans les signatures qu'on écrit
  (`def f(a, b, c=None)`, pas `def f(a, *, b)`). Les `*args`/`**kwargs` restent OK.
- **Trop de paramètres → dataclass de config** passée en un seul argument.
- **Centraliser les valeurs de config** (ex. TTL) en un seul endroit, groupées par famille dans
  des classes (`app/config.py`, `infra/config.py`).
- **Tout typer** ; fonctions rarement > 30 lignes (return-early, éviter les `if` imbriqués) ;
  fichiers cœur < 300 lignes.
- **`api.domain` est sans état** : ni SQLAlchemy, ni FastAPI, ni `api.infra.db` (vérifié par
  import-linter). La persistance vit dans `api.app`.
- **`get_session` ne commit jamais** : un handler qui écrit commit explicitement.

## Linting

- **`make lint`** — lance tout le linting (black, ruff, mypy, import-linter, vue-tsc front).
- **`make lint-fix`** — corrige automatiquement les erreurs black et ruff.

## Tests

- **`make test`** — suite complète. Réseau bloqué (pytest-socket) ; les evals payantes
  (marker `eval`) sont exclues.
- **`make test-evals`** — les evals uniquement (vrais appels payants), à la discrétion de
  l'utilisateur.

## Admin

- **`make create-admin email=… [name=…]`** — crée un compte admin (ou repose son mot de passe).
  Aucun compte n'est seedé par les migrations.
