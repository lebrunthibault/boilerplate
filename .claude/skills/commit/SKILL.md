---
name: c
description: "Commit and push current work. Use when the user types 'c', 'commit', or asks to commit and push current work."
allowed-tools: Bash(git *)
---

Commite le travail en cours, puis push. Suis ces étapes dans l'ordre :

## 1. Analyser les changements

Ne pas afficher de diff dans le terminal. Les changements ont déjà été faits dans cette conversation, tu as le contexte.

- `git status` pour voir les fichiers modifiés/ajoutés
- `git log --oneline -5` pour voir le style des messages récents

## 2. Spec liée (docs/specs)

Si ce commit implémente une spec présente dans `docs/specs/` (typiquement sous
`in-progress/`), alors :

- **Référencer la spec dans le message de commit** : ajouter sur une ligne dédiée
  le nom du fichier de spec, **sans son dossier de statut**. Par exemple :
  `Implements: 2026-01-15-export-csv.md`. Cela permet de retrouver
  facilement dans l'historique git ce qui a été implémenté.
- **Passer la spec en `done/`** dans le même commit, via
  `git mv docs/specs/in-progress/<spec>.md docs/specs/done/` (préserve
  l'historique). Le déplacement doit faire partie des fichiers stagés du commit.

## 3. Stage, commit et push

- `git add` **les fichiers de ce travail, nommés explicitement** — jamais `git add -A` ni `git add .` :
  d'autres modifications en cours (session parallèle) peuvent traîner dans l'arbre.
- Rédiger un message de commit concis au format conventionnel (feat:, fix:, chore:, refactor:, etc.) basé sur les changements réels. Une ligne, en anglais.
- Si une spec est concernée (cf. étape 2), ajouter la ligne `Implements: <spec>.md` dans le corps du message.
- `git commit`
- `git push`
