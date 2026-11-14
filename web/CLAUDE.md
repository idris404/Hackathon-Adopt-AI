# Contexte du projet

## Problématique

Retourner les résultats d'analyse effectués par le logiciel **Lymfip** (<https://www.lymhoe.com/connexions-lymfip>) et **supprimer l'analyse manuelle** que font les biochimistes lorsqu'ils obtiennent le retour du logiciel.

- Lymfip est utilisé en laboratoire pour le suivi des patients en attente de greffe. Il est connecté aux automates et aux logiciels métiers du laboratoire, et ses comptes rendus validés sont transmis aux équipes de greffe.
- Ce sont des **données de santé** : les traiter comme sensibles (jamais dans les logs, jamais en dur dans le code ou les tests, accès protégé par l'authentification).
- **Ne rien inventer sur Lymfip.** Le format de ses résultats, la manière de les obtenir (API, fichier, autre) et les règles d'analyse ne sont pas encore connus. Tant qu'ils ne sont pas fournis, ne pas supposer de schéma de données ni de règle métier : poser la question.
- Points encore ouverts : comment l'application récupère les résultats, qui les consulte et sous quelle forme, qui les valide une fois l'étape manuelle supprimée. Voir « Problématique » dans `README.md`.

## Architecture

Monorepo avec deux applications séparées (dans `web/`), plus les dépendances d'infrastructure, situées à la **racine du dépôt**, à côté de `web/` :

```
Hackathon-Adopt-AI/
├── dependencies/       # Docker Compose (PostgreSQL + pgvector)
│   ├── compose.yml
│   └── volumes/        # données PostgreSQL — ignoré par git
└── web/
    ├── backend/        # API Python (FastAPI)
    └── frontend/       # SPA Vite + React + TypeScript
```

Dans ce fichier et dans `.claude/rules/`, les chemins `backend/…` et `frontend/…` sont relatifs à `web/`.

## Stack

### Backend — `backend/`

- **Python** avec **FastAPI**
- **SQLAlchemy** pour l'accès aux données (ORM)
- **Pydantic** pour la validation des **entrées et des sorties** : chaque route déclare un schéma de requête et un `response_model`. On ne renvoie jamais un modèle SQLAlchemy directement.
- Gestion des dépendances avec **uv**
- Point d'entrée : `app.main:app`

### Frontend — `frontend/`

- **Vite** + **React** + **TypeScript en mode strict** (`"strict": true`, pas de `any` implicite)
- **Zod** pour la validation des entrées (formulaires, paramètres) ; les types TypeScript sont inférés des schémas Zod (`z.infer`) plutôt que dupliqués à la main.
- **Tailwind CSS** (plugin `@tailwindcss/vite`), **Motion** et **GSAP** pour le style et les animations.
- **React Router** (routes déclarées dans `app/App.tsx`, chemins dans `constants/routes.ts`), **TanStack Query** (appels API), **TanStack Table** (tableaux), **React Hook Form** (formulaires) et **nuqs** (état dans l'URL, adaptateur `nuqs/adapters/react-router/v8` posé dans `app/App.tsx`, à l'intérieur du `BrowserRouter`).

### Base de données

- **PostgreSQL 17 avec l'extension pgvector** (image `pgvector/pgvector:pg17-trixie`), lancé via Docker Compose (`dependencies/compose.yml`, à la racine du dépôt). L'extension doit être activée dans la base (`CREATE EXTENSION IF NOT EXISTS vector;`).
- La configuration (URL de connexion, secrets) passe par les variables d'environnement : `.env` n'est jamais commité, `.env.example` documente les variables attendues.
- Le compose lit `DB_USER`, `DB_PASSWORD`, `DB_NAME` et `DB_PORT`, avec des valeurs par défaut pour le développement local. Docker Compose ne lit automatiquement que `dependencies/.env`, pas `web/.env` : pour utiliser `web/.env`, ajouter `--env-file web/.env` à la commande. Le backend doit se connecter avec les mêmes valeurs.

## API

Base URL en local : `http://localhost:8000/api/v1`. Toutes les routes métier vivent sous `/api/<version>` (voir « Versionnement de l'API » dans `.claude/rules/backend.md`). La documentation OpenAPI reste à la racine : `/docs`, `/redoc`, `/openapi.json`. Le catalogue des endpoints et le journal des décisions sont dans `doc/` (`api-endpoints.md`, `api-decisions.md`) : les mettre à jour dans la même modification que le code, voir `doc/README.md`.

### Route publique : résultat d'analyse

`GET /api/v1/analysis/result` ne demande **aucune authentification** (contexte `backend/app/analysis/`). C'est la seule exception à la règle « données de santé = accès authentifié », et elle ne tient que parce que la réponse est **synthétique** : le schéma `AnalysisResultRead` impose `synthetic: true` (`Literal[True]`) et le service sert pour l'instant le cas de démonstration `DEMO_ANALYSIS_RESULT` (`constants/analysis.py`). Les résultats d'un vrai patient ne doivent jamais passer par cette route : ils iront sur une route authentifiée, avec son propre schéma.

## Patients et patients synthétiques

Deux contextes backend, alimentés par le CSV `data-model/data/patients_synthetiques_v3.csv` (51 000 lignes, **synthétiques**) :

- **`patients`** (`backend/app/patients/`) : `id` (UUID, clé primaire technique), **`patient_id`** (identifiant fonctionnel **unique**, la colonne `patient_id` du CSV, ex. « HIS-00355 » ou « SYN-0001 »), `firstname`, `lastname`, `birth` (nullable), `gender` M/F, `city`, `country`, `created_at`. Le CSV ne contient que `patient_id`, `date_naissance` et `sexe` : prénom, nom, ville et pays sont **fictifs**, tirés de listes (`constants/patients.py`) de façon déterministe à partir du `patient_id`. L'`id` est déduit du `patient_id` (UUID v5) : il ne change pas d'un seed à l'autre. Les relations `Patient.serum_tests` (tri `test_date`) et `Patient.history` (tri `occurred_on`) sont en `lazy="raise"`, chargées par `selectinload` : `GET /patients` et `GET /patients/{id}` renvoient les tests et l'historique.
- **`synthetic_patients`** (`backend/app/synthetic_patients/`) : table `patients_synthetiques`, **toutes les colonnes du CSV** (mêmes noms en minuscules, `hla_A` → `hla_a`) + `id` (clé primaire technique) et `created_at`. **La liaison se fait par `patient_id`** : `patients_synthetiques.patient_id` est une clé étrangère vers `patients.patient_id` (`ON DELETE CASCADE`), pas vers `patients.id`. Un patient peut avoir plusieurs patients synthétiques (`patient_id` n'est donc pas unique dans cette table ; relation `SyntheticPatient.patient`, chargement explicite requis : `lazy="raise"`). Le CSV a une ligne par `patient_id` : l'`id` d'un patient synthétique en est déduit, deux lignes de même `patient_id` seraient comptées « déjà présentes ». Les colonnes `_…` du CSV sont les vérités terrain du générateur, pas des entrées. Les colonnes catégorielles sont des `VARCHAR` libres (pas d'enum : les valeurs sont celles du CSV).

- **`serum_tests`** (`backend/app/serum_tests/`) : table `serum_tests`, une ligne de `data-model/data/serum_test_history.csv`. Liaison par **`patient_id`** (clé étrangère vers `patients.patient_id`, `ON DELETE CASCADE`), pas par l'UUID. (`patient_id`, `test_date`) est unique. L'`id` est un UUID v5 de `patient_id|test_date`. Colonnes du CSV en minuscules (`B12` → `b12`, `B12_output` → `b12_output`). `*_output` vaut 1 si la valeur est ≥ 500. Valeurs **synthétiques**, pas des résultats cliniques.
- **`patient_history`** (`backend/app/patient_history/`) : table `patient_history`, événements fictifs (pas un CSV). Liaison par **`patient_id`**, même clé étrangère. Réservé à dix patients de démonstration, listés dans `constants/patient_history.py` : l'UUID noté est `patients_synthetiques.id`, le lien est le `patient_id` (`HIS-00355`, etc.). Sept événements par patient, datés à partir de la greffe : autre pathologie, accident, transfusion, bilan préopératoire (J-1), greffe, suivi postopératoire (J+7), prochaine consultation (J+10). `kind` est un `VARCHAR` (`illness`, `accident`, `transfusion`, `preop`, `graft`, `postop`, `consultation`). L'`id` est un UUID v5 de `patient_id|code`.
- **`signatures`** (`backend/app/signatures/`) : table `patient_signatures`, la validation d'un cas simple par un soignant (`patient_id` unique, `signed_by`, `signed_at`). Seule donnée saisie par les utilisateurs : `patient_id` n'est **pas** une clé étrangère, pour que `seed --reset` ne la touche pas. Le contexte lit le patient via le service `patients`.

**Seed** : `uv run python -m app.seed [--csv CHEMIN] [--serum-csv CHEMIN] [--only patients|synthetic|serum|history] [--reset]` (depuis `backend/`). Quatre étapes, dans cet ordre : (1) les patients, avec leur `patient_id` ; (2) les patients synthétiques **à partir des patients** ; (3) l'historique sérique ; (4) les événements fictifs. Les étapes 2 à 4 sont filtrées par `existing_patient_ids` (une ligne dont le `patient_id` n'existe pas est comptée « sans patient » et n'est pas insérée). `--serum-csv` défaut : `data-model/data/serum_test_history.csv`. Rejouable, atomique (une seule transaction), sans jamais afficher le contenu du fichier. Le CSV est lu en lots de 400 lignes : asyncpg refuse plus de 32 767 paramètres par requête (voir `constants/seed.py`).

**Pas de migrations** : `create_all` ne modifie pas une table existante. Si le schéma de `patients`, `patients_synthetiques`, `serum_tests` ou `patient_history` a changé depuis sa création, le seed refuse (« schéma obsolète ») ; `--reset` supprime alors les quatre tables et les recrée (leurs données se régénèrent depuis les CSV et les événements fictifs, avec les mêmes `id`). Le backend (`lifespan`) ne vérifie pas le schéma : après un changement d'entité, relancer le seed avec `--reset`.

**Routes** (session requise, pagination, recherche, filtres et tri côté serveur) :

- `GET /api/v1/patients` (recherche `search` sur `patient_id`, prénom et nom) et `GET /api/v1/patients/{id}`. Dans les URL, `{id}` est l'**UUID** du patient, jamais son `patient_id`. Les deux réponses incluent `serum_tests` (tri `test_date`), `history` (tri `occurred_on`) et `serum_evolution` (le même suivi, rangé par année et par antigène, avec le libellé du profil : constant, intermédiaire, fluctuant), liés par `patient_id` (ex. `HIS-00355`).
- `GET /api/v1/synthetic-patients` : filtres `search` (dans le `patient_id`), `patient_id` (exact, sans tenir compte de la casse), `sexe`, `jeu`, `phase`, `statut_parcours`, `organe` ; tri sur une liste blanche (`sort_by`, `sort_order`) ; réponse `{items, total, page, page_size}`. Chaque élément porte les 65 colonnes du CSV sous leur nom (les colonnes `_…` aussi : Pydantic interdit les champs préfixés par `_`, le schéma les lit et les renvoie par alias), plus `id` et `created_at`.
- `GET /api/v1/patients/{id}/synthetic-patients` : les patients synthétiques d'un patient, paginés (`sort_by`, `sort_order`, `page`, `page_size` seulement : le patient est dans l'URL). L'URL désigne le patient par son `id` (UUID), le service en déduit son `patient_id` pour la liaison. **404 `PATIENT_NOT_FOUND` si le patient n'existe pas**, page vide s'il n'a aucun patient synthétique (≠ `?patient_id=` de la liste globale, qui renvoie une page vide dans les deux cas). Le contexte `synthetic_patients` vérifie le patient via le service `patients`, jamais son repository.
- `GET /api/v1/signatures/queue` : au plus 5 cas à signer (profil sérique `A`, au plus 3 événements d'historique, pas encore signés), au format `Patient`, plus `remaining`. `POST /api/v1/signatures` `{patient_id: <UUID>}` : `201`, `404 PATIENT_NOT_FOUND`, `409 PATIENT_ALREADY_SIGNED`. Seuils dans `constants/signatures.py`.

## Authentification

Système **email / mot de passe**, implémenté côté backend FastAPI. Les skills Better Auth de `.claude/skills` (`create-auth`, `email-and-password-best-practices`, …) ciblent une stack TypeScript et ne s'appliquent pas ici.

- Le backend est la source de vérité : toute validation côté frontend (Zod) est une aide à l'utilisateur, jamais une garantie de sécurité. Le backend revalide toujours avec Pydantic.
- Le mot de passe n'est jamais stocké ni loggé en clair, ni renvoyé dans une réponse.
- Bibliothèque : **FastAPI Users** (en mode maintenance : correctifs de sécurité seulement). Son adaptateur SQLAlchemy est **asynchrone** : l'auth utilise `AsyncSession` et `asyncpg`, ce qui déroge à l'exemple synchrone de `.claude/rules/backend.md`.
- Session : jeton opaque **stocké en base** (table `accesstoken`), transporté par un cookie `HttpOnly` / `SameSite=lax`, `Secure` sauf `COOKIE_SECURE=false`. La déconnexion supprime la ligne : la session est révoquée côté serveur. Mots de passe hachés en **Argon2id** (paramètres dans `constants/auth.py`).
- Routes (toutes sous `/api/v1`) : `POST /api/v1/auth/register`, `POST /api/v1/auth/login` (corps JSON `{email, password}`), `POST /api/v1/auth/logout` (appareil courant), `POST /api/v1/auth/logout-all` (tous les appareils : `SessionService.logout_all`), `GET` et `PATCH /api/v1/users/me`. Protéger une route : `Depends(current_active_user)` (`auth/dependencies.py`). Le login et le logout sont écrits dans `auth/router.py` (FastAPI Users impose un formulaire OAuth2 pour le login) ; seules l'inscription et `/users/me` viennent des routers de la librairie. Les identifiants invalides lèvent `InvalidCredentialsError`, convertie en `400 LOGIN_BAD_CREDENTIALS` dans `main.py`.
- **Côté frontend** : pas d'écran d'inscription ni de mot de passe oublié, seulement connexion (`/`) et déconnexion (bouton dans `AuthenticatedLayout`). La session vit dans le cookie HttpOnly, le frontend ne la lit jamais : « qui est connecté » vient de `GET /users/me` (hook `useCurrentUser`, `null` sur 401). `RequireAuth` protège `/dashboard` et `/fiche/:id`, `RedirectIfAuthenticated` renvoie `/` vers `/dashboard` une fois connecté. Connexion et déconnexion ne naviguent pas elles-mêmes : elles mettent à jour la session en cache et les gardes redirigent. À la déconnexion, tout le cache TanStack Query est vidé (données de santé).
- **Pas encore en place** (décisions à prendre) : réinitialisation de mot de passe et vérification d'email (fournisseur d'envoi d'email non choisi), limitation de débit, révocation automatique des sessions au changement de mot de passe (la brique `SessionService.logout_all` existe, elle n'est pas encore appelée par `PATCH /users/me`), migrations (les tables sont créées au démarrage dans `main.py`).

## Commandes

| Action | Commande | Dossier |
| --- | --- | --- |
| Lancer PostgreSQL | `docker compose -f ./dependencies/compose.yml up -d` | racine du dépôt |
| Lancer le backend | `uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` | `web/backend/` |
| Lancer le frontend | `npm run dev -- --strictPort` | `web/frontend/` (port 5173) |
| Ingérer patients, synthétiques, tests sériques et historique d'événements | `uv run python -m app.seed [--csv CHEMIN] [--serum-csv CHEMIN] [--only patients\|synthetic\|serum\|history] [--reset]` | `web/backend/` |
| Tests backend (base mockée, sans PostgreSQL) | `uv run pytest` | `web/backend/` |

## Conventions

- Backend et frontend ne partagent pas de code : le contrat entre les deux est l'API HTTP (schémas Pydantic côté serveur, schémas Zod côté client).
- Toute donnée qui entre dans le système (corps de requête, query params, saisie utilisateur) est validée par un schéma ; toute donnée qui sort de l'API passe par un schéma de réponse Pydantic.
- Aucune valeur en dur : toute valeur littérale qui porte un sens, y compris les valeurs des règles métier, est une constante du dossier global `backend/app/constants/` ou `frontend/src/constants/`. Les valeurs qui changent selon l'environnement et les secrets passent par la configuration (`.env`), jamais par les constantes. Détail dans `.claude/rules/`.
- Ne jamais commiter de secrets : `.env`, `.venv`, `node_modules` et `dependencies/volumes` sont dans les `.gitignore`.
- Design / UI : voir `DESIGN.md`.
