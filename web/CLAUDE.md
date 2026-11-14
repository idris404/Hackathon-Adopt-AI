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

### Base de données

- **PostgreSQL 17 avec l'extension pgvector** (image `pgvector/pgvector:pg17-trixie`), lancé via Docker Compose (`dependencies/compose.yml`, à la racine du dépôt). L'extension doit être activée dans la base (`CREATE EXTENSION IF NOT EXISTS vector;`).
- La configuration (URL de connexion, secrets) passe par les variables d'environnement : `.env` n'est jamais commité, `.env.example` documente les variables attendues.
- Le compose lit `DB_USER`, `DB_PASSWORD`, `DB_NAME` et `DB_PORT`, avec des valeurs par défaut pour le développement local. Docker Compose ne lit automatiquement que `dependencies/.env`, pas `web/.env` : pour utiliser `web/.env`, ajouter `--env-file web/.env` à la commande. Le backend doit se connecter avec les mêmes valeurs.

## API

Base URL en local : `http://localhost:8000/api/v1`. Toutes les routes métier vivent sous `/api/<version>` (voir « Versionnement de l'API » dans `.claude/rules/backend.md`). La documentation OpenAPI reste à la racine : `/docs`, `/redoc`, `/openapi.json`.

### Route publique : résultat d'analyse

`GET /api/v1/analysis/result` ne demande **aucune authentification** (contexte `backend/app/analysis/`). C'est la seule exception à la règle « données de santé = accès authentifié », et elle ne tient que parce que la réponse est **synthétique** : le schéma `AnalysisResultRead` impose `synthetic: true` (`Literal[True]`) et le service sert pour l'instant le cas de démonstration `DEMO_ANALYSIS_RESULT` (`constants/analysis.py`). Les résultats d'un vrai patient ne doivent jamais passer par cette route : ils iront sur une route authentifiée, avec son propre schéma.

## Authentification

Système **email / mot de passe**, implémenté côté backend FastAPI. Les skills Better Auth de `.claude/skills` (`create-auth`, `email-and-password-best-practices`, …) ciblent une stack TypeScript et ne s'appliquent pas ici.

- Le backend est la source de vérité : toute validation côté frontend (Zod) est une aide à l'utilisateur, jamais une garantie de sécurité. Le backend revalide toujours avec Pydantic.
- Le mot de passe n'est jamais stocké ni loggé en clair, ni renvoyé dans une réponse.
- Bibliothèque : **FastAPI Users** (en mode maintenance : correctifs de sécurité seulement). Son adaptateur SQLAlchemy est **asynchrone** : l'auth utilise `AsyncSession` et `asyncpg`, ce qui déroge à l'exemple synchrone de `.claude/rules/backend.md`.
- Session : jeton opaque **stocké en base** (table `accesstoken`), transporté par un cookie `HttpOnly` / `SameSite=lax`, `Secure` sauf `COOKIE_SECURE=false`. La déconnexion supprime la ligne : la session est révoquée côté serveur. Mots de passe hachés en **Argon2id** (paramètres dans `constants/auth.py`).
- Routes (toutes sous `/api/v1`) : `POST /api/v1/auth/register`, `POST /api/v1/auth/login` (corps JSON `{email, password}`), `POST /api/v1/auth/logout` (appareil courant), `POST /api/v1/auth/logout-all` (tous les appareils : `SessionService.logout_all`), `GET` et `PATCH /api/v1/users/me`. Protéger une route : `Depends(current_active_user)` (`auth/dependencies.py`). Le login et le logout sont écrits dans `auth/router.py` (FastAPI Users impose un formulaire OAuth2 pour le login) ; seules l'inscription et `/users/me` viennent des routers de la librairie. Les identifiants invalides lèvent `InvalidCredentialsError`, convertie en `400 LOGIN_BAD_CREDENTIALS` dans `main.py`.
- **Pas encore en place** (décisions à prendre) : réinitialisation de mot de passe et vérification d'email (fournisseur d'envoi d'email non choisi), limitation de débit, révocation automatique des sessions au changement de mot de passe (la brique `SessionService.logout_all` existe, elle n'est pas encore appelée par `PATCH /users/me`), migrations (les tables sont créées au démarrage dans `main.py`).

## Commandes

| Action | Commande | Dossier |
| --- | --- | --- |
| Lancer PostgreSQL | `docker compose -f ./dependencies/compose.yml up -d` | racine du dépôt |
| Lancer le backend | `uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` | `web/backend/` |
| Lancer le frontend | `npm run dev -- --strictPort` | `web/frontend/` (port 5173) |
| Tests backend (base mockée, sans PostgreSQL) | `uv run pytest` | `web/backend/` |

## Conventions

- Backend et frontend ne partagent pas de code : le contrat entre les deux est l'API HTTP (schémas Pydantic côté serveur, schémas Zod côté client).
- Toute donnée qui entre dans le système (corps de requête, query params, saisie utilisateur) est validée par un schéma ; toute donnée qui sort de l'API passe par un schéma de réponse Pydantic.
- Aucune valeur en dur : toute valeur littérale qui porte un sens, y compris les valeurs des règles métier, est une constante du dossier global `backend/app/constants/` ou `frontend/src/constants/`. Les valeurs qui changent selon l'environnement et les secrets passent par la configuration (`.env`), jamais par les constantes. Détail dans `.claude/rules/`.
- Ne jamais commiter de secrets : `.env`, `.venv`, `node_modules` et `dependencies/volumes` sont dans les `.gitignore`.
- Design / UI : voir `DESIGN.md`.
