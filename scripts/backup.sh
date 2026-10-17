#!/bin/bash
# Sauvegarde quotidienne de la base prod vers un stockage objet S3, chiffrée côté client (age).
#
#   /backup.sh        boucle : dort jusqu'au prochain 03:00 UTC, sauvegarde, recommence.
#   /backup.sh once   une sauvegarde immédiate puis sortie (vérification, test de restauration).
#
# Le remote rclone `s3` vient des variables RCLONE_CONFIG_S3_* posées par le compose : aucun
# fichier de config, aucun secret écrit sur le disque du conteneur. Le conteneur ne détient que la
# clé PUBLIQUE age (BACKUP_AGE_RECIPIENT) : il sait chiffrer, jamais déchiffrer.
# Restauration et garde de la clé privée : docs/ops/backups.md.
set -euo pipefail

BACKUP_HOUR_UTC=3
DAILY="s3:${S3_BUCKET}/db-backups/daily"
WEEKLY="s3:${S3_BUCKET}/db-backups/weekly"
DAILY_RETENTION=30d
WEEKLY_RETENTION=180d

log() { echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] $*"; }

# Une clé publique mal copiée ne doit pas se découvrir à 03:00 : on chiffre un octet au démarrage.
check_recipient() {
    if [[ "${BACKUP_AGE_RECIPIENT:-}" != age1* ]]; then
        log "ERREUR : BACKUP_AGE_RECIPIENT absent ou pas une clé publique age (age1...)"
        exit 1
    fi
    if ! echo ok | age -r "$BACKUP_AGE_RECIPIENT" > /dev/null; then
        log "ERREUR : BACKUP_AGE_RECIPIENT refusée par age"
        exit 1
    fi
}

run_backup() {
    local name file
    name="app_$(date -u +%Y%m%d_%H%M%S).sql.gz.age"
    file="/tmp/${name}"

    log "Dump + chiffrement -> ${name}"
    # pipefail : un pg_dump ou un age en échec fait échouer la ligne, rien n'est envoyé.
    # --no-owner --no-privileges : restaurable sous n'importe quel rôle (Postgres jetable du test
    # de restauration comme prod recréée).
    pg_dump --no-owner --no-privileges | gzip | age -r "$BACKUP_AGE_RECIPIENT" > "$file"

    log "Envoi daily/ ($(du -h "$file" | cut -f1))"
    rclone copy "$file" "$DAILY/"
    if [[ "$(date -u +%u)" == "7" ]]; then
        log "Dimanche : copie weekly/"
        rclone copy "$file" "$WEEKLY/"
    fi
    rm -f "$file"

    # Purge par préfixe, jamais sur la racine db-backups/ : rclone delete est récursif et
    # emporterait les weekly à 30 jours.
    log "Purge daily > ${DAILY_RETENTION}, weekly > ${WEEKLY_RETENTION}"
    rclone delete --min-age "$DAILY_RETENTION" "$DAILY/"
    # weekly/ n'existe pas avant le premier dimanche : sur S3 comme en local, rclone répond
    # "directory not found" et réessaie trois fois en hurlant. On liste d'abord, on purge ensuite.
    if rclone lsf "$WEEKLY/" > /dev/null 2>&1; then
        rclone delete --min-age "$WEEKLY_RETENTION" "$WEEKLY/"
    else
        log "purge weekly ignorée (préfixe absent)"
    fi
    log "OK : ${name}"
}

# Sur S3 un préfixe vide est une erreur rclone, pas une liste vide : d'où l'appel sous `if`.
already_done_today() {
    rclone lsf "$DAILY/" 2>/dev/null | grep -q "^app_$(date -u +%Y%m%d)_"
}

# busybox date ne connaît pas `-d "tomorrow 03:00"` (cf. b542f4d) : arithmétique sur l'epoch.
seconds_until_next_run() {
    local now today_run
    now=$(date -u +%s)
    today_run=$(( now / 86400 * 86400 + BACKUP_HOUR_UTC * 3600 ))
    if (( now < today_run )); then
        echo $(( today_run - now ))
    else
        echo $(( today_run + 86400 - now ))
    fi
}

check_recipient

if [[ "${1:-}" == "once" ]]; then
    run_backup
    exit 0
fi

# bash en PID 1 ignore SIGTERM sans trap : docker stop attendrait 10 s puis SIGKILL. `sleep & wait`
# rend le trap effectif pendant l'attente (même pattern que le service certbot).
trap 'exit 0' TERM INT

# Pas de sauvegarde au démarrage : un redémarrage (déploiement, reboot) ne produit pas de dump
# hors horaire. On dort d'abord, on sauvegarde ensuite.
while true; do
    wait_s=$(seconds_until_next_run)
    log "Prochaine sauvegarde dans ${wait_s}s"
    sleep "$wait_s" & wait $!

    if already_done_today; then
        log "Sauvegarde du jour déjà présente, on passe"
        continue
    fi
    # Sous-processus et non appel de fonction : dans un `if`, bash désactive errexit à l'intérieur
    # d'une fonction, un pg_dump en échec y serait ignoré. Le script relancé a son propre `set -e`.
    if ! "$0" once; then
        log "ÉCHEC de la sauvegarde — nouvel essai dans 1 h"
        sleep 3600 & wait $!
    fi
done
