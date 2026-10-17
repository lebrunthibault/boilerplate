---
name: update-changelog
description: "Met à jour le changelog client (docs/CHANGELOG.md) en ajoutant une section « Du X au Y » qui résume les étapes principales. Use when the user says 'mets à jour le changelog', 'update le changelog', or asks to add/refresh a changelog entry."
allowed-tools: Bash(git log:*), Read, Edit
---

# Mise à jour du changelog

Ajoute une nouvelle section « Du X au Y » en haut de `docs/CHANGELOG.md`, orientée
client (peu technique, concise), résumant les étapes principales de la période.
**Ne modifie QUE `docs/CHANGELOG.md`. Ne commite pas, ne push pas.**

## 1. Déterminer le point de départ

Lire le haut de `docs/CHANGELOG.md` et chercher, sous l'en-tête de la dernière
section, le marqueur `<!-- last-commit: <sha> -->`.

- **Cas normal — marqueur présent** : le point de départ est ce `<sha>`. Les commits
  à traiter sont ceux d'après : `git log <sha>..HEAD`.
- **Fallback — pas de marqueur (1er run)** : calculer deux dates candidates et
  prendre **la plus ancienne** comme début :
  - (1) date de fin de la dernière section (`## Du … au <Y>`, si elle existe) ;
  - (2) `git log -1 --format='%ad' --date=short -- docs/CHANGELOG.md`.
  Les commits à traiter sont ceux `--since=<date la plus ancienne>`.

## 2. Récupérer les étapes principales

Lister les commits de la période, du plus ancien au plus récent (selon le cas) :

```bash
git log --no-merges --date=short --pretty=format:'%h %ad %s' <sha>..HEAD --reverse
# ou, en fallback :
git log --no-merges --date=short --pretty=format:'%h %ad %s' --since=<X> --reverse
```

Récupérer aussi le **SHA complet de HEAD** (= dernier commit traité, à inscrire en
étape 5) : `git log -1 --format='%H'`.

**Dates de l'en-tête** : `X` = date du 1er commit de la liste, `Y` = date du dernier
(`git log -1 --format='%ad' --date=short`). Format français :
`## Du <j> au <j> <mois> <année>` — mois en minuscule, pas de zéro initial
(ex. `## Du 19 au 28 juin 2026`). Mois différents → l'écrire pour chacun
(ex. `## Du 28 juin au 3 juillet 2026`).

**Ne pas dupliquer** ce qui figure déjà dans la section la plus récente du changelog.

## 3. Lire le changelog existant pour caler le style

Lire `docs/CHANGELOG.md` en entier et **reproduire son style** :

- Français, **pas d'emoji**, puces `-` (jamais de liste numérotée).
- Puces qui commencent par un **concept en gras** puis le bénéfice en clair :
  `- **Suivi des temps de traitement** : onglet Perf et tableau de bord.`
- Regrouper en quelques sections thématiques `###` (réutiliser le vocabulaire
  existant quand pertinent : `Nouveautés`, `Améliorations`, `Corrections`,
  `Améliorations interface`, `Refacto architecture`, `Tests, outillages & specs`…).
- Backticks pour les identifiants de code, mais avec parcimonie côté client.

## 4. Rédiger l'entrée — orientée client, concise

Traduire les commits techniques en **valeur produit / utilisateur**, pas en « comment ».

- **Pas trop technique** : le lecteur est un client, pas un dev. Dire ce qui change
  pour lui (détection plus fiable, nouvel écran, action dispo), pas l'implémentation.
- **Pas trop verbeux** : fusionner les commits liés en une seule puce ; viser
  ~4 à 8 sections de 1 à 5 puces. Ne pas lister chaque commit.
- **Détails techniques en fin d'entrée** : regrouper refacto / archi (DDD) / tests /
  outillage / dépendances dans une ou deux sections techniques **à la fin**
  (ex. `### Refacto architecture`,
  `### Tests, outillages & specs`). Omettre ce qui n'a aucun intérêt client.

## 5. Insérer et s'arrêter

Insérer la nouvelle section **juste sous le titre `# Changelog`**, au-dessus de la
section précédente (ordre antéchronologique). Structure :

```markdown
## Du 19 au 28 juin 2026
<!-- last-commit: <SHA complet de HEAD> -->

### …
- …
```

Le commentaire `<!-- last-commit: … -->` est **invisible** dans le rendu client mais
sert d'ancre de reprise au prochain run (étape 1).

- **Modifier uniquement `docs/CHANGELOG.md`** via Edit. Ne toucher à aucun autre
  fichier. **Ne pas commiter ni push.**
- Résumer brièvement la période ajoutée (dates + nb de sections) et préciser que le
  fichier n'est pas commité.
