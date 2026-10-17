# Sauvegardes de la base de production

Runbook opérationnel.

## Quoi, où, quand

| | |
| --- | --- |
| Contenu | `pg_dump` plain SQL (`--no-owner --no-privileges`), gzip, chiffré **age** (clé publique) |
| Nom | `app_<YYYYMMDD_HHMMSS>.sql.gz.age` |
| Destination | Stockage objet S3, bucket `S3_BUCKET`, préfixes `db-backups/daily/` et `db-backups/weekly/` |
| Fréquence | 1 dump/jour à **03:00 UTC** ; sauté si un objet du jour existe déjà dans `daily/` |
| Rétention | `daily/` 30 jours ; `weekly/` (copie du dimanche) 180 jours |
| Service | conteneur `boilerplate-backup-1` (`docker/Dockerfile.backup`, `scripts/backup.sh`) |
| RPO / RTO | 24 h / 1 h cible |

Ce que le conteneur connaît : la clé **publique** age (`BACKUP_AGE_RECIPIENT`) et les clés S3, en
variables d'environnement (`RCLONE_CONFIG_S3_*`), donc visibles par `docker inspect` mais jamais
écrites sur son disque. Ce qu'il ne connaît pas : la clé privée. Il ne peut pas lire ce qu'il envoie.

## La clé privée

- Générée sur le poste de dev : `age-keygen -o ~/.config/age/boilerplate-backup.key`
  (`chmod 600`). La ligne `# public key: age1…` est la valeur de `BACKUP_AGE_RECIPIENT`.
- Copie de la clé privée dans le gestionnaire de mots de passe.
- **Sa perte rend toutes les sauvegardes illisibles.** Ni le dépôt ni le serveur ne la portent.

## Sauvegarde manuelle

```sh
ssh <alias-ssh>
docker exec boilerplate-backup-1 /backup.sh once
docker logs --tail 20 boilerplate-backup-1
```

## Test de restauration (trimestriel)

Depuis le poste de dev, dans un Postgres jetable, jamais la base de dev :

```sh
scripts/restore_backup.sh                                  # dernier dump de daily/
scripts/restore_backup.sh app_20260101_030002.sql.gz.age   # un dump précis
```

Prérequis : `sudo apt install rclone age`, les `S3_*` du serveur recopiés dans le `.env` racine, la
clé privée en place. Résultat attendu : comptages plausibles (compléter la requête de vérification
de `scripts/restore_backup.sh` avec les tables métier) et `alembic_version` égal à
`uv run alembic -c src/api/alembic.ini heads` (ou une révision de retard si un déploiement a eu lieu
depuis le dump).

### Journal des tests

| Date | Objet | Comptages | alembic | Résultat |
| --- | --- | --- | --- | --- |
| | | | | |

## Restauration réelle en prod

1. `ssh <alias-ssh> && cd /opt/boilerplate`
2. Arrêter ce qui écrit : `docker compose -p boilerplate --env-file .env -f docker/docker-compose.prod.yml stop api backup`
3. Récupérer le dump sur le poste : `rclone copy s3:<bucket>/db-backups/daily/<objet> .`
4. Recréer la base vide sur le serveur :
   `docker exec boilerplate-db-1 psql -U app -d postgres -c 'DROP DATABASE app' -c 'CREATE DATABASE app'`
5. Restaurer en flux depuis le poste, sans SQL en clair sur disque :
   `age -d -i ~/.config/age/boilerplate-backup.key <objet> | gunzip | ssh <alias-ssh> 'docker exec -i boilerplate-db-1 psql -U app -d app -q -v ON_ERROR_STOP=1'`
6. `compose up -d api nginx backup` — l'API rejoue `alembic upgrade head` au besoin.

(`app` = valeurs de `POSTGRES_USER` / `POSTGRES_DB` du `.env` prod.)

## Restauration dans la base de dev

Le format est du plain SQL : `psql`, pas `pg_restore`.

```sh
make db-reset
age -d -i ~/.config/age/boilerplate-backup.key <objet> | gunzip | psql -h localhost -p 5433 -U app -d app -q
```

## Rotation

- **Clé age** : nouvelle paire, `BACKUP_AGE_RECIPIENT` mise à jour dans `/opt/boilerplate/.env`,
  `./deploy.sh` (recrée le conteneur backup). Garder l'ancienne clé privée **180 jours**, le temps que
  les weekly chiffrés avec expirent.
- **Clés S3** : nouvelles clés dans `.env`, `./deploy.sh`.

## Hors portée (backlog)

Alerte « aucune sauvegarde depuis 26 h » ; conteneur non-root ; chiffrement au repos de la base.
