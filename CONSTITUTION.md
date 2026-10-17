# Constitution

> Document de gouvernance haut niveau du projet (spec-driven development). Il fige les décisions
> structurantes et oriente le développement de chaque feature. Trois piliers : **Mission**,
> **Tech stack**, **Roadmap**, complétés par les **Principes directeurs**. Pour le détail, suivre
> les renvois vers `docs/` — la Constitution ne duplique pas, elle pointe.

## 1. Mission

*(à compléter dès le premier jour — une ligne par puce)*

- **Le pourquoi** : [quel problème, pour qui].
- **Flux** : [l'utilisateur fait X → le système fait Y → il rend Z].
- **Audience** : [clients cibles].
- **Cas d'usage principal** : [le cas qui justifie le produit].
- **Périmètre** : [ce qui est dedans]. **Hors périmètre** : [ce qu'on refuse explicitement].
- **Renvois** : [`README.md`](README.md) (vue d'ensemble), [`docs/vocabulary.md`](docs/vocabulary.md)
  (langage métier canonique — ubiquitous language).

## 2. Tech stack

- **Architecture** : monolithe `src/` en deux composants — `api/` (backend FastAPI + SQLAlchemy
  async + PostgreSQL, cœur métier), `frontend/` (dashboard Vue 3 + Vite + Tailwind 4, package
  manager bun).
- **Backend** : Python 3.12, FastAPI, SQLAlchemy 2 async (asyncpg), Alembic (migrations),
  Pydantic, Logfire (observabilité, désactivée par défaut). Gestion des dépendances : `uv`.
- **Auth** : comptes admin en base, mot de passe argon2, session serveur opaque révocable
  (cookie httponly), journal d'authentification, step-up sur actes destructeurs.
- **Données** : PostgreSQL 16.
- **Tests** : pytest + pytest-asyncio (+ aiosqlite en mémoire), réseau bloqué (pytest-socket).
- **Qualité** : Black, Ruff, MyPy, import-linter (frontières d'architecture), vue-tsc.
- **Déploiement** : Docker / docker-compose (dev & prod), VPS `/opt/boilerplate`, CI GitHub
  Actions sur push `main` → `deploy.sh` (SSH), nginx + certbot / Let's Encrypt, sauvegardes
  quotidiennes chiffrées (age) vers un stockage S3. → [`docs/ops/backups.md`](docs/ops/backups.md)
- **Renvoi** : [`docs/coding-style.md`](docs/coding-style.md) pour l'architecture en oignon et les
  conventions.

## 3. Principes directeurs

*(condensé en pointeurs — la spécification complète vit dans `docs/`)*

- **Architecture en oignon** `app → domain → infra` ; 1 package = 1 façade ; imports de façades
  uniquement (vérifié par import-linter). → [`docs/coding-style.md`](docs/coding-style.md)
- **Domaine sans état** : `domain/` ne touche ni la base ni HTTP ; il reçoit et rend des modèles
  typés. La persistance et le cycle de vie vivent dans `app/`.
- **Langage du domaine unifié** (ubiquitous language) : un concept = un seul nom, partout (code,
  specs, doc, frontend, commentaires). → [`docs/vocabulary.md`](docs/vocabulary.md)
- **Sécurité fail-closed** : en prod, l'app refuse de démarrer plutôt que de servir dégradée
  (CORS, clé API) ; `deploy.sh` refuse un `.env` incohérent.
- **RGPD dès la conception** : durées de conservation centralisées et purgées automatiquement,
  registre et notice tenus à jour. → [`docs/rgpd/`](docs/rgpd/)
- **Discipline de code** : tout typer ; jamais de `dict` pour des données structurées (dataclass /
  Pydantic) ; fonctions rarement > 30 lignes ; fichiers cœur < 300 lignes. → [`CLAUDE.md`](CLAUDE.md),
  [`docs/coding-style.md`](docs/coding-style.md)

## 4. Roadmap

- **Document vivant** géré via le process de spec : une unité de travail = une spec, écrite **avant**
  l'implémentation ; le dossier porte le statut (pas de champ dupliqué).
- **Cycle de vie** : `backlog/` → `todo/` → `in-progress/` → `done/` (+ `cancelled/`).
  → [`docs/specs/README.md`](docs/specs/README.md)
- **Source de vérité de la roadmap** : `docs/specs/{todo,in-progress,done}/` — ne pas dupliquer ici.
  - **Livré** : [`docs/specs/done/`](docs/specs/done/)
  - **En cours** : [`docs/specs/in-progress/`](docs/specs/in-progress/)
  - **À venir** : [`docs/specs/todo/`](docs/specs/todo/)
- **Replanification** entre features : réviser cette Constitution et mettre à jour la roadmap.
