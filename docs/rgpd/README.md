# RGPD — registres et conformité

Ce dossier tient la conformité RGPD du produit : **registres** (art. 30), **checklist technique**
et renvois vers le code qui applique les durées de conservation.

| Fichier | Rôle |
|---|---|
| [`registre-traitement.md`](registre-traitement.md) | Registre des traitements dont l'éditeur est **responsable** (art. 30.1), au format Markdown — source de vérité, versionnée avec le code. |
| [`checklist-technique.md`](checklist-technique.md) | Points de contrôle techniques à passer avant la mise en production, puis à chaque feature qui touche des données personnelles. |
| `registre-sous-traitant.*` | *(à créer si besoin)* Registre **sous-traitant** (art. 30.2), cf. ci-dessous. |

## Un ou deux registres ?

- **Responsable de traitement** (controller) : vous décidez de la finalité et des moyens. C'est
  toujours le cas pour vos traitements **propres** — comptes administrateurs, journal de
  connexion, prospection, facturation. → `registre-traitement.md`.
- **Sous-traitant** (processor) : vous traitez des données **pour le compte** de vos clients, qui
  en décident la finalité (ex. un SaaS B2B qui héberge les fichiers clients de ses clients). Une
  fiche par catégorie d'activité (pas par client), avec la liste des clients, et un **contrat
  art. 28** (DPA) signé avec chacun. → créer `registre-sous-traitant`.
- Une **réutilisation** de données clients pour votre propre finalité (statistiques, amélioration
  produit, jeux de test) vous rend **responsable** de cette réutilisation : base légale à établir
  et à encadrer dans le DPA, ou anonymisation.

## À compléter au démarrage

- Identité de l'éditeur (raison sociale, forme, SIREN, adresse, contact) dans le registre et dans
  la page `/confidentialite` (`src/frontend/src/pages/ConfidentialitePage.vue`).
- Liste des **sous-traitants** (hébergeur, stockage des sauvegardes, emailing, APIs tierces) avec
  leur pays, et un DPA signé pour chacun. Tout prestataire hors UE = transfert à encadrer (SCC).
- Les **durées de conservation** : une par famille de données, déclarée dans
  `src/api/app/config.py::Retention` et purgée par `src/api/app/retention.py` (boucle
  quotidienne en prod). Registre, notice et code doivent dire la même chose.

## Modèle CNIL

La CNIL publie un modèle de registre simplifié (tableur) sur
<https://www.cnil.fr/fr/RGDP-le-registre-des-activites-de-traitement>. Le Markdown de ce dossier
se transpose dedans quand un registre au format officiel est demandé.
