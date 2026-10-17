#!/usr/bin/env bash
# Test de restauration d'une sauvegarde chiffrée, depuis le poste de dev, dans un Postgres JETABLE
# (jamais la base de dev : pour restaurer dans la dev, voir docs/ops/backups.md).
#
# Usage : scripts/restore_backup.sh [NOM_OBJET]     défaut : le plus récent de db-backups/daily/
#
# Prérequis : docker, rclone, age (sudo apt install rclone age) ; S3_* renseignés dans le .env
# racine (mêmes noms que sur le VPS) ; clé privée dans ~/.config/age/boilerplate-backup.key
# (ou AGE_KEY_FILE). Le SQL en clair ne touche jamais le disque : age → gunzip → psql en flux.
set -euo pipefail
cd "$(dirname "$0")/.."

AGE_KEY_FILE="${AGE_KEY_FILE:-$HOME/.config/age/boilerplate-backup.key}"
CONTAINER=boilerplate-restore-test
PG_IMAGE=postgres:16-alpine   # même majeure que la prod (docker/docker-compose.prod.yml)
PG_USER=app
PG_DB=app

need() { command -v "$1" > /dev/null || { echo "Outil manquant : $1" >&2; exit 1; }; }
need docker; need rclone; need age
[[ -r "$AGE_KEY_FILE" ]] || { echo "Clé privée introuvable : $AGE_KEY_FILE" >&2; exit 1; }

# Même lecture que deploy.sh : sans guillemets ni blancs, pas de xargs (apostrophes).
env_value() {
    grep -E "^$1=" .env | head -1 | cut -d= -f2- | tr -d '"' | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//' || true
}

export RCLONE_CONFIG_S3_TYPE=s3 RCLONE_CONFIG_S3_PROVIDER=Other
RCLONE_CONFIG_S3_ACCESS_KEY_ID="$(env_value S3_ACCESS_KEY)"
RCLONE_CONFIG_S3_SECRET_ACCESS_KEY="$(env_value S3_SECRET_KEY)"
RCLONE_CONFIG_S3_ENDPOINT="$(env_value S3_ENDPOINT)"
RCLONE_CONFIG_S3_REGION="$(env_value S3_REGION)"
export RCLONE_CONFIG_S3_ACCESS_KEY_ID RCLONE_CONFIG_S3_SECRET_ACCESS_KEY RCLONE_CONFIG_S3_ENDPOINT RCLONE_CONFIG_S3_REGION
BUCKET="$(env_value S3_BUCKET)"
[[ -n "$RCLONE_CONFIG_S3_ACCESS_KEY_ID" && -n "$BUCKET" ]] || { echo "S3_* manquants dans .env" >&2; exit 1; }
DAILY="s3:${BUCKET}/db-backups/daily"

name="${1:-$(rclone lsf "$DAILY/" | sort | tail -1)}"
[[ -n "$name" ]] || { echo "Aucune sauvegarde sous $DAILY" >&2; exit 1; }

work=$(mktemp -d)
cleanup() { docker rm -f "$CONTAINER" > /dev/null 2>&1 || true; rm -rf "$work"; }
trap cleanup EXIT

echo "== Téléchargement $name"
rclone copy "$DAILY/$name" "$work/"

echo "== Postgres jetable ($CONTAINER, sans port publié)"
docker rm -f "$CONTAINER" > /dev/null 2>&1 || true
docker run --rm -d --name "$CONTAINER" -e POSTGRES_USER="$PG_USER" -e POSTGRES_PASSWORD=throwaway \
    -e POSTGRES_DB="$PG_DB" "$PG_IMAGE" > /dev/null
# Sonde TCP : le serveur temporaire d'initialisation de l'image n'écoute que sur socket Unix.
for _ in $(seq 1 30); do
    docker exec "$CONTAINER" pg_isready -h 127.0.0.1 -U "$PG_USER" -q && break
    sleep 1
done

echo "== Déchiffrement + restauration"
age -d -i "$AGE_KEY_FILE" "$work/$name" | gunzip \
    | docker exec -i "$CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -q -v ON_ERROR_STOP=1 > /dev/null

echo "== Vérifications"
docker exec "$CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -At -F ' = ' -c "
  SELECT 'admin', count(*)::text FROM admin
  UNION ALL SELECT 'alembic_version', version_num FROM alembic_version"

echo "Restauration OK : $name. Comparer alembic_version à \`uv run alembic -c src/api/alembic.ini heads\`."
echo "Reporter la date dans docs/ops/backups.md (journal des tests)."
