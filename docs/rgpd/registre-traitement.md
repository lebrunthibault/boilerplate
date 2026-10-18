# Registre des activités de traitement (simplifié)

> Registre art. 30.1 (responsable de traitement), à transposer au besoin dans le modèle CNIL.
> Établi le [date]. Champs `[à compléter]` = informations propres à l'entité.

## Responsable de traitement

- **Entité** : [Raison sociale — à compléter] (éditeur de [Nom du produit], [domaine])
- **Contact** : [contact@exemple.fr]
- **DPO** : [non désigné (structure de petite taille) — contact ci-dessus]

---

## Traitement n°1 — [Activité principale du produit]

| Rubrique | Contenu |
|---|---|
| **Finalité principale** | [Ce que le traitement permet de faire, pour qui] |
| **Base légale** | [Contrat (art. 6.1.b) / intérêt légitime (art. 6.1.f) / obligation légale (art. 6.1.c) / consentement (art. 6.1.a)] |
| **Catégories de personnes** | [Utilisateurs, clients, prospects, tiers…] |
| **Catégories de données** | [Identité, coordonnées, données de connexion, contenu…] — **minimiser** : ne collecter que ce dont la finalité a besoin |
| **Destinataires / sous-traitants** | [Hébergeur (pays)] ; [stockage des sauvegardes (pays)] ; [API tierce (pays) — rôle] |
| **Transferts hors UE** | [Aucun] / [Prestataire X (pays) — encadré par clauses contractuelles types] |
| **Durée de conservation** | [Durée] puis suppression automatique (`Retention.[FAMILLE]`). Sauvegardes : 30 jours quotidiennes + 180 jours hebdomadaires, chiffrées côté client (age, clé privée hors serveur). |
| **Mesures de sécurité** | HTTPS/TLS + HSTS ; base non exposée (réseau interne, bind loopback) ; secrets hors dépôt ; console d'administration derrière authentification ; sauvegardes chiffrées avant envoi ; test de restauration trimestriel ([runbook](../ops/backups.md)) |

---

## Traitement n°2 — Comptes de la console d'administration

| Rubrique | Contenu |
|---|---|
| **Finalité principale** | Authentifier les administrateurs et gérer leurs accès à la console |
| **Base légale** | Intérêt légitime (art. 6.1.f) — sécurité du système d'information |
| **Catégories de personnes** | Administrateurs de la plateforme |
| **Catégories de données** | Email, nom affiché, empreinte argon2 du mot de passe (jamais le mot de passe), dates de création et de dernière connexion ; sessions : empreinte sha256 du jeton, horodatages |
| **Destinataires / sous-traitants** | Aucun — base interne ([hébergeur], [pays]) |
| **Durée de conservation** | Compte : durée de la fonction, désactivé au départ. Sessions : purgées à l'expiration (12 h max, 60 min d'inactivité) |
| **Mesures de sécurité** | Mots de passe argon2 ; cookie de session httponly, `Secure` + `__Host-` en prod ; limitation des tentatives ; ré-authentification (step-up) avant tout acte destructeur |

---

## Traitement n°3 — Journal d'authentification de la console d'administration

| Rubrique | Contenu |
|---|---|
| **Finalité principale** | Traçabilité des accès à la console d'administration : détecter et enquêter sur un accès illégitime (art. 32) |
| **Base légale** | Intérêt légitime (art. 6.1.f) — sécurité du système d'information |
| **Catégories de personnes** | Administrateurs de la plateforme ; toute personne tentant de se connecter |
| **Catégories de données** | Adresse email tentée, identifiant du compte admin, adresse IP, user-agent, type d'événement et horodatage. **Jamais** de mot de passe, jamais de donnée personnelle de tiers — le journal survit à un effacement RGPD |
| **Destinataires / sous-traitants** | Aucun — journal interne ; les administrateurs le consultent depuis la console (écran « Sécurité ») |
| **Durée de conservation** | **12 mois** puis suppression automatique (purge quotidienne, `Retention.AUTH_EVENTS`), aligné sur la norme française applicable aux journaux de connexion |
| **Mesures de sécurité** | Lecture réservée aux administrateurs authentifiés ; journal en écriture seule (jamais modifié) ; second exemplaire des lignes dans les journaux du conteneur |

---

## Traitement n°4 — Journal des appels LLM

| Rubrique | Contenu |
|---|---|
| **Finalité principale** | Mise au point et contrôle des traitements automatisés par IA : relire ce qui a été envoyé au modèle et ce qu'il a répondu, diagnostiquer un échec, suivre les coûts |
| **Base légale** | Intérêt légitime (art. 6.1.f) — [à confirmer selon la finalité métier des appels] |
| **Catégories de personnes** | [Personnes dont les données figurent dans les inputs envoyés au modèle — à compléter] |
| **Catégories de données** | Prompt système (texte du code, sans donnée personnelle) ; input envoyé au modèle et output reçu, [catégories à compléter] ; modèle, tokens, coût, durée, erreur ; référence générique de l'objet traité (type + id) |
| **Destinataires / sous-traitants** | Fournisseur du modèle : [Sous-traitant LLM — pays, DPA, engagement de non-rétention / non-entraînement] ; journal interne consulté par les administrateurs (écran « Appels LLM ») |
| **Transferts hors UE** | [Selon le fournisseur retenu — aucun si fournisseur opéré en UE] |
| **Durée de conservation** | **90 jours** puis suppression automatique (purge quotidienne, `Retention.LLM_CALLS`) ; prompts système conservés (pas de donnée personnelle) |
| **Mesures de sécurité** | Lecture réservée aux administrateurs authentifiés ; input tronqué (`LlmCall.INPUT_LOG_CHARS`) ; aucun contenu dans les logs applicatifs ni dans Logfire (pas d'`instrument_pydantic_ai`) |

---

## Points de vigilance

- [Sous-traitants : DPA signés et archivés ?]
- [Transferts hors UE : liste à jour ?]
- [Droit à l'effacement : outillé (route admin sous step-up) ?]
