# Coding style & conventions

Source unique des conventions de code (macro + micro). Référencé depuis `CLAUDE.md` (chargé à
chaque session) et `docs/specs/README.md` : **toute grosse feature ou spec doit le respecter**.

Court et actionnable, pas un cours de DDD. En cas de doute, le code du socle (`app/auth`,
`app/notifications`) prime comme exemple.

## 1. Architecture (macro)

- **Oignon `app → domain → infra`**. Les dépendances pointent vers le bas. `infra`
  (db, config technique, traces de perf) est **injectée / importée par le bas**, jamais importée
  « vers le haut » par le domaine. Chaque couche porte sa config en module feuille (stdlib
  uniquement, importable sans cycle) : `app/config.py`, `infra/config.py` (et `domain/config.py`
  quand le métier en aura).
  - `app/` — entrypoints : routers FastAPI, auth, persistance, tâches de fond, rétention.
  - `domain/` — le cœur métier, **sans état** : ni SQLAlchemy, ni FastAPI, ni `api.infra.db`
    (contrat import-linter `domain-stateless`). Il reçoit et rend des modèles typés.
  - `infra/` — technique transverse : `db`, `config`, `perf_trace`.
- **1 package = 1 point d'entrée public** : une façade `__init__.py` (re-export explicite + `__all__`)
  ou un `service.py`. On importe **la façade** d'un autre package, **jamais un de ses sous-fichiers**.
  Imposé en CI par `import-linter` (`make lint`) dès qu'un contrat le déclare. Modèle de référence :
  `app/auth/__init__.py`.
- **Placement des modèles** : un type qui **traverse** plusieurs étapes / packages → *shared kernel*
  bas (ex. `domain/contracts.py`). Un type interne à un seul package → **co-localisé** avec la
  fonction qui le produit (`<package>/models.py`). Surtout **pas de `models.py` fourre-tout** à la
  racine. Exception : les modèles ORM, regroupés dans `infra/db/models.py` (une table = une classe).
- **Config centralisée par couche**, constantes **groupées par famille dans des classes** (façon
  `AuthConfig`, `Retention`, `DbPool` — pas de constante module isolée sauf singleton sans famille).
  Une valeur = un seul endroit ; une constante à consommateur unique se co-localise avec son appelant.
- **Temps / horloge** : résoudre `now()` **au bord** (couche `app`) et passer la valeur (`date` /
  `datetime`) vers le domaine. Jamais de `date.today()` enfoui dans le domaine (entrée cachée qui
  casse la pureté et le déterminisme des tests).
- **Transformations immuables** : une étape renvoie un **nouvel** objet (`model_copy` /
  `dataclasses.replace`), elle ne mute pas l'entité partagée en place.
- **Commits explicites** : `get_session` ne commit jamais. Un handler qui écrit commit lui-même ;
  une écriture qui doit survivre à une exception levée juste après (journal d'audit) commit seule.
- **Horodatages posés en Python** (`datetime.now(UTC)`) plutôt que par `server_default` quand le
  code relit la valeur : le SQLite des tests ne remplit pas les `server_default` sans refresh.

## 2. Langue & vocabulaire du domaine

- **Specs & prose de doc** : français.
- **Textes affichés aux utilisateurs** : français, **vouvoiement**, ton sobre.
- **Identifiants** (modules, fonctions, variables, classes) **& vocabulaire métier** : anglais.
- **Commentaires de code** (docstrings + `#`) : **anglais**. Les commentaires français rencontrés
  sont convertis **au passage** (même esprit que « nettoyer le dead code », §3), pas de sweep dédié.

**Vocabulaire canonique : [`docs/vocabulary.md`](vocabulary.md)** — un concept = un nom, le même
dans le code, les specs, le frontend et les commentaires.

**Bannir** les noms inventés et vagues (« manager », « helper », « service_ia », « collector ») :
**nommer par la responsabilité**.

## 3. Style micro (surtout sur le cœur métier)

S'applique en priorité au cœur (`domain/`) et aux routers/serializers `app/`. Les helpers purement
techniques (HTTP, parsing bas niveau) sont plus tolérants.

- **Tout est typé** : paramètres **et** retours.
- **Le moins de `dict`/`tuple` possible.** Un tuple de statut `(str, bool)` passe ; pour une fonction
  importante, retourner une `@dataclass` typée. **Jamais `dict` comme type d'une donnée structurée**
  (`-> dict` / `: dict` pour une entité) — un vrai mapping homogène `dict[str, int]` reste OK.
  **Pydantic** aux frontières HTTP (modèles de réponse des routes compris).
- **Fonctions rarement > 30 lignes.** Préférer le **return-early**, inverser les conditions, éviter
  les gros blocs `if …:` imbriqués (sortir tôt sur les cas d'erreur/bord).
- **Fichiers cœur < 300 lignes.** Au-delà, découper (un `utils.py` par package si ça aère).
- **Inliner les dataclasses de contexte évidentes** au point d'appel — garder le **type en
  signature** (pour la lisibilité), pas besoin d'une variable intermédiaire :
  `notify_admins(session, NotificationEvent(kind=…, target_id=…))` plutôt qu'un `event = …`
  au-dessus.
- **Logique dérivée des champs → `@property` sur le value object**, pas recalculée à l'extérieur.
  Un booléen prédicat, un résumé pour les logs, une valeur dérivée se calculent **sur le modèle qui
  porte les champs**, et s'appellent directement sans helper externe qui re-construit les champs.
- **Signatures** : pas de séparateur keyword-only `*` dans nos signatures (`def f(a, b, c=None)`, pas
  `def f(a, *, b)`). `*args`/`**kwargs` restent OK. **Trop de paramètres → une dataclass de config**
  passée en un seul argument.
- **Nettoyer le dead code** rencontré au passage.

## 4. Frontend

- **Composants réutilisables** dans `components/` uniquement ; un sous-composant propre à une page
  vit dans un dossier par page (`pages/admin/inbox/Index.vue` + ses voisins).
- **Appels API via `authFetch`** (`composables/useAuth.ts`) : un 401 renvoie vers `/login` sans
  jamais rendre l'erreur à l'écran. Les listes paginées passent par `usePaginatedList`.
- **Tokens de design** (`style.css`, préfixe `app-`) et primitives (`.btn`, `.card`, `.tag`,
  `.field`…) plutôt que des couleurs en dur. Typo : Geist (texte) / JetBrains Mono (code, chiffres).
- **Feature flags** centralisés dans `config/features.ts`.
- **Aucun secret ni règle métier sensible dans le bundle** : il est téléchargeable sans
  authentification.

## 5. Qualité (gates)

- `make test` vert (pytest + pytest-asyncio ; SQLite en mémoire via `conftest`, réseau bloqué).
  Les tests `eval` font des appels réels payants (non déterministes) → exclus par défaut,
  `make test-evals`.
- `make lint` vert : `black` + `ruff` (line-length **100**) + `mypy` + `lint-imports`
  (`import-linter` : prouve l'oignon et l'absence d'imports profonds) + `vue-tsc` côté frontend.
