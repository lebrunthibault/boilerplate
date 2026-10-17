.DEFAULT_GOAL := help

## ── Python API ───────────────────────────────────────────

BUN := $(HOME)/.bun/bin/bun

.PHONY: install
install: ## Install project with dev dependencies (Python + frontend)
	@if [ ! -f $(BUN) ]; then \
		echo "Installing bun..."; \
		curl -fsSL https://bun.sh/install | bash; \
	fi
	uv sync --extra dev
	cd src/frontend && $(BUN) install

.PHONY: up
up: ## Start all services in Docker (DB + API + frontend)
	docker compose -f docker/docker-compose.yml up --build -d
	@echo "Waiting for Postgres to be ready..."
	@until docker compose -f docker/docker-compose.yml exec -T postgres pg_isready -q; do sleep 1; done
	@$(MAKE) db-migrate
	@echo "API:      http://localhost:8000"
	@echo "Frontend: http://localhost:5173"
	@echo "Logs:     make logs"

.PHONY: down
down: ## Stop all Docker services
	docker compose -f docker/docker-compose.yml down

.PHONY: logs
logs: ## Tail logs from all Docker services
	docker compose -f docker/docker-compose.yml logs -f

.PHONY: lint
lint: lint-black lint-ruff lint-mypy lint-imports lint-frontend ## Run all linters

.PHONY: lint-black
lint-black: ## Check formatting with black
	uv run black --check src/api/

.PHONY: lint-ruff
lint-ruff: ## Lint with ruff
	uv run ruff check src/api/

.PHONY: lint-mypy
lint-mypy: ## Type-check with mypy
	uv run mypy src/api/

.PHONY: lint-imports
lint-imports: ## Check architecture boundaries (onion layers) with import-linter
	PYTHONPATH=src uv run lint-imports

.PHONY: lint-frontend
lint-frontend: ## Type-check frontend with vue-tsc
	cd src/frontend && $(BUN) run vue-tsc -b --noEmit

.PHONY: lint-fix
lint-fix: ## Auto-fix formatting and lint issues
	uv run black src/api/
	uv run ruff check --fix src/api/

## ── Database ────────────────────────────────────────────

.PHONY: db-up
db-up: ## Start Postgres container only
	docker compose -f docker/docker-compose.yml up -d postgres
	@echo "Waiting for Postgres to be ready..."
	@until docker compose -f docker/docker-compose.yml exec -T postgres pg_isready -q; do sleep 1; done

.PHONY: db-migrate
db-migrate: ## Run all pending migrations
	uv run alembic -c src/api/alembic.ini upgrade head

.PHONY: db-rollback
db-rollback: ## Rollback last migration
	uv run alembic -c src/api/alembic.ini downgrade -1

.PHONY: db-revision
db-revision: ## Auto-generate a new migration
	uv run alembic -c src/api/alembic.ini revision --autogenerate -m "$(msg)"

.PHONY: db-reset
db-reset: ## Drop and recreate database
	docker compose -f docker/docker-compose.yml down -v
	docker compose -f docker/docker-compose.yml up -d
	@echo "Waiting for Postgres..."
	@sleep 2
	uv run alembic -c src/api/alembic.ini upgrade head

## ── Admin ───────────────────────────────────────────────

.PHONY: create-admin
create-admin: ## Create an admin account or reset its password (usage: make create-admin email=a@b.fr [name="Alice"])
	@if [ -z "$(email)" ]; then echo "Usage: make create-admin email=a@b.fr [name=\"Alice\"]"; exit 1; fi
	uv run python scripts/set_admin_password.py $(email) --create $(if $(name),--name "$(name)")

# L'image prod n'embarque que `src/api` (cf. docker/Dockerfile.api) : ni `scripts/`, ni `uv`.
# Pour lancer un script sur la prod : monter le dossier scripts du checkout du serveur dans un
# conteneur jetable — `--no-deps` pour ne pas toucher à l'api qui sert le trafic, `--rm` pour ne
# rien laisser derrière. PROD_SSH / PROD_DIR : alias SSH et répertoire de déploiement.
PROD_SSH ?= boilerplate
PROD_DIR ?= /opt/boilerplate
PROD_COMPOSE = docker compose -p boilerplate --env-file .env -f docker/docker-compose.prod.yml

.PHONY: create-admin-prod
create-admin-prod: ## Same, on production over SSH (usage: make create-admin-prod email=a@b.fr)
	@if [ -z "$(email)" ]; then echo "Usage: make create-admin-prod email=a@b.fr"; exit 1; fi
	ssh -t $(PROD_SSH) 'cd $(PROD_DIR) && $(PROD_COMPOSE) run --rm --no-deps \
		-v $(PROD_DIR)/scripts:/app/scripts api python scripts/set_admin_password.py $(email) --create'

## ── Tests ───────────────────────────────────────────────

.PHONY: test
test: ## Run test suite (network blocked, paid evals excluded — see test-evals)
	uv run pytest -q

.PHONY: test-evals
test-evals: ## Run evals only (real paid API calls, marker eval)
	uv run pytest -m eval --force-enable-socket -v -s

## ── Frontend ─────────────────────────────────────────────

.PHONY: install-frontend
install-frontend: ## Install frontend dependencies
	cd src/frontend && $(BUN) install

.PHONY: dev-frontend
dev-frontend: ## Start frontend dev server on :5173
	cd src/frontend && $(BUN) run dev

.PHONY: build-frontend
build-frontend: ## Build frontend for production
	cd src/frontend && $(BUN) run build

## ── Git hooks ────────────────────────────────────────────

.PHONY: git-hook-pre-commit
git-hook-pre-commit: ## Install pre-commit git hook
	ln -sf ../../bin/pre-commit .git/hooks/pre-commit
	chmod +x bin/pre-commit
	@echo "Pre-commit hook installed."

## ── Help ─────────────────────────────────────────────────

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
