# Boilerplate

Socle d'application web : API FastAPI + PostgreSQL, dashboard d'administration Vue 3, déploiement
Docker sur un VPS par `git push`, sauvegardes chiffrées, process de specs et base RGPD. Le métier
reste à écrire — dans `src/api/domain/` et les pages admin.

## Ce qui est déjà là

- **Auth admin** : comptes en base, mots de passe argon2, session serveur opaque et révocable
  (cookie httponly, `Secure` + `__Host-` en prod), expiration par inactivité (60 min) et plafond
  absolu (12 h), limitation des tentatives, journal d'authentification, ré-authentification
  (step-up) avant les actes destructeurs, garde `Origin` (CSRF en profondeur).
- **Console admin** : connexion, comptes (liste, désactivation sous step-up), journal de sécurité,
  boîte de réception (notifications fan-out vers les autres admins, lu/non-lu, pliage des mises à
  jour répétées).
- **Appels LLM** (pydantic-ai, tout fournisseur) : une tâche déclarée (`LlmTask`), un seul point
  d'appel (`run_llm`), et chaque appel journalisé automatiquement en base — prompt système
  (dédoublonné), input, output, tokens, coût, durée, retries, erreur — consultable dans l'écran
  admin « Appels LLM ». Inerte tant que `LLM_MODEL_*` est vide.
- **Pages publiques** : landing et politique de confidentialité (art. 13) en placeholders.
- **Durcissement prod** piloté par `APP_ENV` : fail-closed sans `ALLOWED_ORIGINS` /
  `SERVICE_API_KEY`, CORS sans wildcard, rate limit des routes publiques, purge de rétention
  quotidienne.
- **Ops** : compose dev et prod, nginx + Let's Encrypt (renouvellement et reload automatiques),
  `deploy.sh` à garde-fous (parité `.env`, valeurs critiques, import de l'app avant recréation,
  bascule api puis nginx sans 502), CI GitHub Actions (tests puis déploiement SSH puis
  healthcheck), sauvegardes Postgres quotidiennes chiffrées (age) vers S3 avec script de test de
  restauration.
- **Qualité** : black, ruff, mypy, import-linter (oignon `app → domain → infra`, domaine sans
  état), vue-tsc, pytest avec réseau bloqué.
- **Process** : specs (`docs/specs/`), Constitution, conventions de code, vocabulaire, changelog
  client, skills Claude Code (`commit`, `update-changelog`, `sync-prod-db`, `oss-best-practices`).

## Architecture

```
boilerplate/
├── src/
│   ├── api/                # Backend Python (FastAPI) — oignon app -> domain -> infra
│   │   ├── main.py         # Point d'entrée : logging, lifespan, CORS, erreurs, routeurs, SPA
│   │   ├── app/            # Routers, auth, comptes, notifications, rétention, config
│   │   ├── domain/         # Cœur métier, sans état (à écrire)
│   │   ├── infra/          # DB (moteur, modèles ORM), LLM, config technique, traces de perf
│   │   └── alembic/        # Migrations
│   └── frontend/           # Dashboard (Vite + Vue 3 + Tailwind 4 + bun)
├── docker/                 # Dockerfiles, compose dev/prod, nginx
├── tests/                  # Tests Python (SQLite en mémoire)
├── scripts/                # Création d'admin, sauvegarde, restauration
├── docs/                   # Specs, conventions, vocabulaire, ops, RGPD
├── deploy.sh               # Déploiement sur le serveur (appelé par la CI)
├── pyproject.toml          # Deps Python (uv) et config des outils
└── Makefile                # Commandes dev (`make help`)
```

## Démarrer

```bash
make install
cp .env.example .env
make up                                  # Postgres + API (:8000) + frontend (:5173), migrations
make create-admin email=vous@exemple.fr name="Vous"
```

Puis <http://localhost:5173/login>.

```bash
make test        # tests (réseau bloqué)
make lint        # black, ruff, mypy, import-linter, vue-tsc
make help        # toutes les commandes
```

## Renommer le projet

Le nom `boilerplate` apparaît comme nom de paquet (`pyproject.toml`, `src/frontend/package.json`),
nom de projet compose (`docker/docker-compose.yml`, `deploy.sh`, `Makefile`), répertoire de
déploiement (`/opt/boilerplate`), titre (`index.html`, `main.py`) et wordmark (`AppHeader.vue`,
`AdminSidebar.vue`, `LoginPage.vue`) : `grep -ri boilerplate` les liste tous. Le domaine
`example.com` est dans `docker/nginx.conf`.

## Mettre en production

1. VPS avec Docker ; cloner le dépôt dans `/opt/boilerplate` ; y créer le `.env` à partir de
   `.env.example` (`APP_ENV=production`, mots de passe, `ALLOWED_ORIGINS`, `SERVICE_API_KEY`,
   `S3_*`, `BACKUP_AGE_RECIPIENT` — cf. [`docs/ops/backups.md`](docs/ops/backups.md)).
2. Renseigner le domaine dans `docker/nginx.conf`, puis obtenir le premier certificat
   (`certbot certonly --webroot -w /var/www/certbot -d <domaine>` via le service `certbot`).
3. GitHub : secrets `VPS_HOST`, `VPS_SSH_USER`, `VPS_SSH_KEY` ; variables `APP_URL`, `APP_DIR`.
4. `git push` sur `main` : la CI teste, déploie et vérifie `/api/health`.
5. `make create-admin-prod email=…` pour le premier compte.

## Appels LLM

1. Choisir le modèle dans `.env` : `LLM_MODEL_SMALL=mistral:mistral-small-latest` (format
   pydantic-ai `provider:model`) et la clé du fournisseur (`MISTRAL_API_KEY`…). Tarif dans
   `src/api/infra/llm/config.py::MODEL_PRICING` pour avoir le coût.
2. Déclarer la tâche et l'appeler — depuis `domain/` comme depuis `app/` :

   ```python
   from pydantic import BaseModel
   from api.infra.llm import LlmTask, run_llm

   class Summary(BaseModel):
       title: str
       key_points: list[str]

   SUMMARIZE = LlmTask(name="summarize", system_prompt="Résume le texte.", output_type=Summary)

   async def summarize(text: str) -> Summary:
       return await run_llm(SUMMARIZE, text)
   ```

3. Envelopper l'unité de travail (route, tâche de fond) dans le journal, côté `app/` :

   ```python
   from api.app.llm_calls import LlmSubject, llm_journal

   async with llm_journal(session, LlmSubject("ticket", str(ticket.id))):
       summary = await summarize(ticket.body)
   ```

   À la sortie, chaque appel du bloc est écrit dans `llm_call` (échecs compris) et commité. Hors
   `llm_journal`, `run_llm` marche aussi mais ne laisse qu'une ligne de log sans contenu.
4. Tests sans réseau : `monkeypatch.setenv("LLM_MODEL_SMALL", "test")` (modèle `TestModel` de
   pydantic-ai), ou `with agent_for(TASK).override(model=TestModel(custom_output_args={…})):` —
   cf. `tests/test_llm_calls.py`.

Le journal garde les inputs 90 jours (`Retention.LLM_CALLS`) : ils peuvent contenir des données
personnelles, et le fournisseur LLM est un sous-traitant à déclarer (`docs/rgpd/`).

## Ajouter une feature métier

1. Écrire la spec (`docs/specs/_template.md`) et la poser dans `docs/specs/todo/`.
2. Modèles purs et logique dans `src/api/domain/<capacité>/` (façade `__init__.py`).
3. Tables dans `src/api/infra/db/models.py` + `make db-revision msg="…"`.
4. Routes dans `src/api/app/<package>/`, branchées dans `src/api/app/router.py`.
5. Écran dans `src/frontend/src/pages/admin/`, route dans `router.ts`, entrée dans
   `AdminSidebar.vue`.
6. Données personnelles : durée dans `Retention`, purge dans `app/retention.py`, registre et
   notice à jour (`docs/rgpd/checklist-technique.md`).
