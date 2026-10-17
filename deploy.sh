#!/usr/bin/env bash
set -euo pipefail

# Tout le corps tient dans un bloc { } : bash lit un script au fil de l'eau, par offset d'octets,
# et le `git reset --hard` ci-dessous réécrit deploy.sh lui-même dès que le commit déployé le
# modifie. Sans le bloc, bash reprend sa lecture au même offset dans un fichier devenu différent
# et s'arrête net — mesuré : le script se termine après le reset, sans exécuter une seule commande
# docker, et sort 0. Le déploiement se croit alors réussi tout en n'ayant rien déployé. Les
# accolades forcent l'analyse syntaxique du corps entier avant la moindre exécution : à partir de
# là le script tourne depuis la mémoire, insensible à sa propre réécriture.
{

# Le VPS est un miroir de origin/main : on reset dur plutôt que `git pull`, qui
# casse sur un force-push (branches divergentes -> "Need to specify how to reconcile")
# et sur un working tree sali. reset --hard ne touche qu'aux fichiers suivis, donc
# le .env (non-suivi) est préservé.
git fetch origin
git reset --hard origin/main

# Garde-fou parité .env : toute clé déclarée dans .env.example doit exister dans .env.
# Sinon un déploiement qui introduit une nouvelle variable requise (ex. une nouvelle clé d'API)
# casse la prod parce que le .env local n'a pas suivi. On échoue AVANT de recréer le
# container (aucun downtime : l'ancien tourne toujours). Valeur vide OK (features optionnelles) ;
# on ne vérifie que la présence de la clé.
missing=()
while IFS= read -r key; do
  grep -qE "^${key}=" .env || missing+=("$key")
done < <(grep -oE '^[A-Za-z_][A-Za-z0-9_]*=' .env.example | sed 's/=$//')
if (( ${#missing[@]} )); then
  echo "ERREUR déploiement : clés présentes dans .env.example mais absentes de .env :" >&2
  printf '  - %s\n' "${missing[@]}" >&2
  echo "Ajoute-les au .env prod (valeur vide acceptée si optionnel) puis relance." >&2
  exit 1
fi

# Garde-fou valeurs : la parité ci-dessus ne vérifie que la PRÉSENCE des clés, or plusieurs ne
# valent que par leur contenu. Même position que la parité : on échoue avant le build et la
# recréation, donc l'ancien container sert toujours.

# Lit une valeur du .env comme compose la lira : sans guillemets ni blancs périphériques. Pas de
# `xargs` : une apostrophe dans un mot de passe le ferait échouer (« unmatched single quote »).
env_value() {
  grep -E "^$1=" .env | head -1 | cut -d= -f2- | tr -d '"' | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//' || true
}

# APP_ENV pilote tout le durcissement (cookie Secure, rate limit, purge de rétention) et se perdrait
# en silence sur un « prod » ou un vide — le compose prod la pose désormais lui-même, ce contrôle
# garde le .env cohérent avec lui.
app_env=$(env_value APP_ENV)
if [[ "$app_env" != "production" ]]; then
  echo "ERREUR déploiement : APP_ENV doit valoir exactement 'production' dans .env (lu : '${app_env}')" >&2
  exit 1
fi
# POSTGRES_PASSWORD ne doit jamais rester sur la valeur d'exemple, ni être vide, ni court.
pg_password=$(env_value POSTGRES_PASSWORD)
if [[ -z "$pg_password" || "$pg_password" == "changeme" || ${#pg_password} -lt 16 ]]; then
  echo "ERREUR déploiement : POSTGRES_PASSWORD vide, égal à l'exemple ('changeme') ou < 16 caractères." >&2
  exit 1
fi
# Sauvegardes : une clé S3 vide ou une clé age absente ne casserait qu'à 03:00, en silence, dans un
# conteneur que personne ne regarde. On refuse le déploiement tout de suite.
for key in S3_ACCESS_KEY S3_SECRET_KEY S3_ENDPOINT S3_REGION S3_BUCKET BACKUP_AGE_RECIPIENT; do
  if [[ -z "$(env_value "$key")" ]]; then
    echo "ERREUR déploiement : ${key} est vide dans .env — les sauvegardes seraient cassées." >&2
    exit 1
  fi
done
if [[ "$(env_value BACKUP_AGE_RECIPIENT)" != age1* ]]; then
  echo "ERREUR déploiement : BACKUP_AGE_RECIPIENT doit être une clé publique age (age1...)." >&2
  exit 1
fi

compose() {
  docker compose -p boilerplate --env-file .env -f docker/docker-compose.prod.yml "$@"
}

compose build api nginx backup

# Garde-fou image, même logique que la parité .env ci-dessus : on échoue AVANT de recréer le
# container, donc l'ancien continue de servir et le déploiement rate sans downtime. Le CMD du
# Dockerfile lance uvicorn sur api.main:app ; si ce module ne s'importe pas, uvicorn meurt aussitôt
# et `restart: unless-stopped` le relance en boucle : la prod part en 502 sans que rien n'ait
# échoué bruyamment (typiquement : du code commité référençant une constante restée dans le
# worktree). L'étape alembic qui suit ne couvre pas ce cas — env.py n'importe que les modèles,
# jamais le router. --no-deps : l'import ne doit dépendre d'aucun service, la base incluse.
compose run --rm --no-deps api python -c "import api.main"

compose run --rm api alembic -c src/api/alembic.ini upgrade head

# Recréation en deux temps plutôt qu'un `up -d api nginx` groupé : nginx repartait en ~1 s quand
# l'API en met ~10, et tout /api/* partait en 502 dans l'intervalle (deux 502 mesurés à chaque
# déploiement). --wait bloque jusqu'à ce que le healthcheck de l'API passe `healthy` (défini dans
# docker-compose.prod.yml), donc nginx ne bascule que sur un backend qui répond déjà.
# Si l'API ne démarre pas, on sort non-zéro au bout de 90 s avec l'ancien nginx encore debout :
# le site reste servi et la CI rougit, au lieu d'une boucle de restart derrière une façade en 200.
compose up -d --force-recreate --wait --wait-timeout 90 api
compose up -d --force-recreate nginx

# Le backup ne sert aucun trafic : pas de --force-recreate, compose ne le recrée que si l'image ou
# l'environnement a changé (c'est aussi ce qui applique une rotation de BACKUP_AGE_RECIPIENT). Sans
# sauvegarde au démarrage (cf. scripts/backup.sh), une recréation ne produit pas de dump hors horaire.
compose up -d backup

}
