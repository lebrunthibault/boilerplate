# Titre de la spec

- **Source** — d'où vient le besoin
- **Archi** — [nom-du-doc](../../architecture/AAAA-MM-JJ-nom-du-doc.md)
- **Dépend de** — [nom-de-spec](../todo/AAAA-MM-JJ-nom-de-spec.md)
- **Style** — [coding-style](../../coding-style.md)

## Contexte

Pourquoi ce travail, quel problème il règle, ce qui l'a déclenché.

## Objectif

Le résultat attendu, vu de l'utilisateur. Une phrase.

## Hors périmètre

Ce qu'on ne fait volontairement pas ici.

## Design

Les fichiers touchés, les modèles (dataclass / Pydantic), les routes, les migrations. Les
snippets de code portent leurs docstrings.

## Critères d'acceptation

- [ ] Comportement 1, vérifiable
- [ ] `make lint` et `make test` verts

## Vérification

Comment constater que ça marche de bout en bout (tests, écran, commande).
