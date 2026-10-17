---
name: sync-prod-db
description: Duplicate the production database to local. Use when the user asks to sync, duplicate, copy, or refresh the local database from prod.
---

# Sync Prod DB to Local

Dump the production PostgreSQL database and restore it locally, overwriting existing data.

Parameters (fill in once for the project — see `CLAUDE.md` § Prod):

- `PROD_SSH` — SSH alias of the production server
- prod container `boilerplate-db-1`, local container `boilerplate-postgres-1`
- user / database `app` (values of `POSTGRES_USER` / `POSTGRES_DB`)

## Step 1: Ensure local postgres is running

```bash
docker compose -f docker/docker-compose.yml ps postgres
```

If not running, start it:

```bash
docker compose -f docker/docker-compose.yml up -d postgres
```

Wait for healthy status before proceeding.

## Step 2: Dump prod

```bash
ssh $PROD_SSH 'docker exec boilerplate-db-1 pg_dump -U app -Fc app' > /tmp/app_prod.dump
```

Verify the dump is non-empty (`ls -lh /tmp/app_prod.dump`). If 0 bytes, something went wrong — investigate.

## Step 3: Restore locally

Terminate active connections then restore:

```bash
docker exec boilerplate-postgres-1 psql -U app -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='app' AND pid <> pg_backend_pid();"
docker exec -i boilerplate-postgres-1 pg_restore -U app -d app --clean --if-exists --no-owner -Fc < /tmp/app_prod.dump
```

Then restart the local API (its connection pool died with the terminated connections):
`docker compose -f docker/docker-compose.yml restart api`.

## Step 4: Verify

```bash
docker exec boilerplate-postgres-1 psql -U app -c "SELECT count(*) FROM admin; SELECT version_num FROM alembic_version;"
```

Add the main business tables to this check as they appear. Report the counts to confirm the
restore succeeded, then delete `/tmp/app_prod.dump` (it holds production personal data).
