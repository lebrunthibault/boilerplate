# Développement piloté par les specs

Une spec est un court document Markdown décrivant une unité de travail — une
feature, un refactor ou une investigation — écrit **avant** l'implémentation.
Chaque spec vit dans **un seul** dossier à la fois ; le dossier où elle se
trouve **est** son statut.

## Cycle de vie

```
backlog/  →  todo/  →  in-progress/  →  done/
```

- **backlog/** — idées et specs futures, pas encore priorisées. Peuvent être
  brouillonnes ou incomplètes. Ignorables quand on choisit du travail.
- **todo/** — priorisées et prêtes à être implémentées. Une spec ici doit avoir
  assez de détail pour qu'on puisse démarrer sans clarification supplémentaire.
- **in-progress/** — en cours d'implémentation. Au plus une ou deux specs ici à
  la fois.
- **done/** — implémentation mergée. Conservées pour le contexte historique et
  pour retracer les décisions jusqu'à la spec qui les a motivées.
- **cancelled/** — abandonnées (piste explorée puis écartée). Conservées pour
  garder trace du « pourquoi on ne l'a pas fait ».

## Faire transiter une spec

Déplacer avec `git mv` pour préserver l'historique :

```sh
git mv docs/specs/<from>/<spec>.md docs/specs/<to>/
```

Par exemple, pour démarrer le travail sur une spec todo :

```sh
git mv docs/specs/todo/2026-01-15-export-csv.md docs/specs/in-progress/
```

## Convention de nommage

`YYYY-MM-DD-titre-en-kebab-case.md` où la date est celle de la **première**
écriture de la spec (pas celle de sa promotion entre dossiers). Exemples :

- `2026-01-15-export-csv.md`
- `2026-01-20-notifications-par-email.md`

## Métadonnées

Partir de [`_template.md`](_template.md). Chaque spec commence — **juste après le titre `#`** — par un court bloc de
métadonnées en liste, qui formalise ses liens vers le contexte d'architecture et
les autres specs. Contrairement à un frontmatter YAML (masqué par la plupart des
lecteurs Markdown), ce bloc est **visible et cliquable** partout, tout en restant
lisible d'un coup d'œil comme graphe de dépendances.

```markdown
# Titre de la spec

- **Source** — retour client du 14/01, ticket #12
- **Archi** — [choix-du-format-d-export](../../architecture/2026-01-14-choix-du-format-d-export.md)
- **Dépend de** — [comptes-clients](../in-progress/2026-01-10-comptes-clients.md)
- **Absorbe** — [export-excel](../cancelled/2026-01-05-export-excel.md)
```

Champs (tous optionnels) :

- **Source** — d'où vient le besoin (retour client, incident, audit…).
- **Jalon** — jalon de roadmap, si le projet en a. Omis sinon.
- **Cas** — cas concrets servant de tests d'acceptation (ids, scénarios).
- **Vocabulaire** — termes de `docs/vocabulary.md` introduits ou modifiés.
- **Archi** — doc(s) de `docs/architecture/` qui motivent/cadrent la spec.
- **Dépend de** — specs prérequises.
- **Absorbe** (ou **Remplace**) — specs reprises tout ou partie ici.

Règles :

- **Texte du lien = nom de fichier** (sans la date ni `.md`) : identité stable et
  lisible. La cible est un **chemin relatif** vers l'emplacement courant du fichier.
- **Liens `Archi`** : pointent sous `docs/architecture/` — ces docs ne changent
  pas de dossier, le lien ne casse jamais.
- **Liens vers d'autres specs** (`Dépend de` / `Absorbe`) : une spec change de
  dossier au fil de son cycle (`git mv`), donc son chemin peut pourrir. Repointer le
  lien lors du `git mv` ; comme le **texte** reste le nom de fichier, la référence
  demeure identifiable même si le chemin a bougé entre-temps.
- **Pas de champ `statut`** : le dossier **est** le statut (cf. Cycle de vie). Ne pas
  le dupliquer (risque de dérive).
- Une petite spec isolée peut n'avoir qu'un **Archi**, voire pas de bloc du tout.

## Conventions de code

Toute spec / feature doit respecter les conventions de [`docs/coding-style.md`](../coding-style.md)
(architecture en oignon `app → domain → infra`, façade par package, style micro). Le citer dans le
bloc de métadonnées via un champ **Style** quand c'est pertinent.

## Avant de démarrer une tâche

1. Lire tout ce qui est sous `docs/specs/in-progress/` pour le contexte courant.
2. Puis regarder `docs/specs/todo/` pour voir ce qui est en file d'attente.

Ces dossiers sont la source de vérité pour « ce sur quoi on travaille » et « ce
qui est planifié » — à privilégier sur l'historique de chat ou la mémoire.
