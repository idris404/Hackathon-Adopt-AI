# Web — Hackathon Adopt AI

Application web du projet **Hackathon Adopt AI** : une API Python (FastAPI), une SPA React et une base PostgreSQL, dans un même monorepo.

> **État du projet** : socle posé (architecture, conventions, agents Claude). Le backend a son authentification (voir plus bas) ; le reste du backend et le frontend restent à écrire.

## Problématique

**Retourner les résultats d'analyse effectués par le logiciel [Lymfip](https://www.lymhoe.com/connexions-lymfip) et supprimer l'analyse manuelle que font les biochimistes lorsqu'ils obtiennent le retour du logiciel.**

Contexte, d'après la page des connexions de Lymfip :

- Lymfip est utilisé en laboratoire pour le suivi des patients en attente de greffe. Il est connecté aux automates et aux logiciels métiers du laboratoire.
- Les comptes rendus validés sont transmis aux équipes de greffe via un module d'accès à distance.
- Il échange aussi avec le CHU (création des dossiers patients, facturation) et avec l'ABM pour Cristal (Syrenad à venir) pour les données des patients en attente de greffe.

Objectif de l'application :

1. Récupérer les résultats d'analyse retournés par Lymfip.
2. Les restituer directement, sans que les biochimistes aient à les analyser à la main.

À clarifier :

- Comment l'application obtient les résultats de Lymfip : la page ne décrit ni API ni format de données.
- Qui consulte les résultats restitués (biochimistes, équipes de greffe, …) et sous quelle forme.
- Qui valide les résultats une fois l'étape manuelle supprimée : la page parle de comptes rendus « validés » avant leur transmission aux équipes de greffe.

## Architecture

```
Hackathon-Adopt-AI/
├── dependencies/       # Docker Compose (PostgreSQL + pgvector)
│   ├── compose.yml
│   └── volumes/        # données PostgreSQL, ignoré par git
└── web/
    ├── backend/        # API Python (FastAPI)
    └── frontend/       # SPA Vite + React + TypeScript
```

`dependencies/` est à la racine du dépôt, à côté de `web/`, et non dans `web/`.

Le backend et le frontend ne partagent aucun code. Le contrat entre les deux est l'API HTTP : schémas **Pydantic** côté serveur, schémas **Zod** côté client.

## Stack

| Couche | Technologies |
| --- | --- |
| Backend | Python, FastAPI, SQLAlchemy (ORM), Pydantic, gestion des dépendances avec **uv** |
| Frontend | Vite, React, TypeScript strict, Zod, React Hook Form, TanStack Query, TanStack Table |
| Base de données | PostgreSQL 17 avec l'extension pgvector (Docker Compose) |
| Tests | Backend : pytest. Frontend : Vitest (unitaires) et Playwright (e2e) |

## Prérequis

- [Docker](https://docs.docker.com/get-docker/) (pour PostgreSQL)
- [uv](https://docs.astral.sh/uv/) (backend Python)
- [Node.js](https://nodejs.org/) et npm (frontend)

## Démarrage

### 1. Configuration

Les URLs de connexion et les secrets passent par les variables d'environnement. `.env` n'est jamais commité, `.env.example` documente les variables attendues.

Depuis `web/` :

```bash
cp .env.example .env
```

### 2. Lancer le projet

| Action | Commande | Depuis |
| --- | --- | --- |
| PostgreSQL | `docker compose -f ./dependencies/compose.yml up -d` | racine du dépôt |
| Backend | `uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` | `web/backend/` |
| Frontend | `npm run dev -- --strictPort` | `web/frontend/` |
| Seed : patients, patients synthétiques, historique sérique | `uv run python -m app.seed [--csv CHEMIN] [--serum-csv CHEMIN] [--only patients\|synthetic\|serum] [--reset]` | `web/backend/` |

- Backend : <http://localhost:8000> (documentation OpenAPI sur `/docs`)
- Frontend : <http://localhost:5173>

Dans VS Code, la configuration `dependencies (Docker)` de [.vscode/launch.json](../.vscode/launch.json) lance PostgreSQL.

## Dépendances (PostgreSQL)

Le dossier [dependencies/](../dependencies/) contient le Docker Compose de l'infrastructure.

| | |
| --- | --- |
| Service | `postgres`, conteneur `adopt-ai-postgres` |
| Image | `pgvector/pgvector:pg17-trixie` (PostgreSQL 17 avec pgvector) |
| Données | `dependencies/volumes/postgres`, ignoré par git |

Variables lues par le compose, avec leurs valeurs par défaut (réservées au développement local) :

| Variable | Défaut | Rôle |
| --- | --- | --- |
| `DB_USER` | `adopt_ai` | Utilisateur PostgreSQL |
| `DB_PASSWORD` | `password` | Mot de passe de l'utilisateur |
| `DB_NAME` | `adopt_ai_db` | Base créée au premier démarrage |
| `DB_PORT` | `5432` | Port exposé sur la machine |

```bash
# Depuis la racine du dépôt
docker compose -f ./dependencies/compose.yml up -d     # démarrer
docker compose -f ./dependencies/compose.yml down      # arrêter, les données sont conservées
```

À savoir :

- Docker Compose ne lit automatiquement que `dependencies/.env`, pas `web/.env`. Sans fichier, les valeurs par défaut s'appliquent. Pour réutiliser les variables de `web/.env`, ajouter `--env-file web/.env` à la commande. Le backend doit se connecter avec les mêmes valeurs.
- `DB_USER`, `DB_PASSWORD` et `DB_NAME` ne sont prises en compte qu'à la première initialisation des données. Pour les changer ensuite, arrêter le conteneur et supprimer `dependencies/volumes/postgres` (cela efface la base).
- L'image embarque pgvector, mais l'extension doit être activée dans la base : `CREATE EXTENSION IF NOT EXISTS vector;`.

## Authentification

Authentification **email / mot de passe**, implémentée côté backend FastAPI.

- Le backend est la source de vérité. La validation Zod côté frontend aide l'utilisateur mais ne garantit rien : le backend revalide toujours avec Pydantic.
- Le mot de passe n'est jamais stocké ni loggé en clair, ni renvoyé dans une réponse.
- Implémentée avec [FastAPI Users](https://fastapi-users.github.io/fastapi-users/) : session stockée en base et transportée par un cookie `HttpOnly`, mots de passe hachés en Argon2id (12 à 256 caractères).

Base URL de l'API : `http://localhost:8000/api/v1` (toutes les routes sont préfixées par `/api/<version>`).

| Route | Rôle |
| --- | --- |
| `POST /api/v1/auth/register` | Inscription (`email`, `password`, JSON) |
| `POST /api/v1/auth/login` | Connexion (JSON `email`, `password`), pose le cookie de session |
| `POST /api/v1/auth/logout` | Déconnexion de l'appareil courant, révoque cette session côté serveur |
| `POST /api/v1/auth/logout-all` | Déconnexion de tous les appareils, révoque toutes les sessions de l'utilisateur |
| `GET /api/v1/users/me`, `PATCH /api/v1/users/me` | Lire et modifier son profil |
| `GET /api/v1/analysis/result` | Résultat d'analyse du modèle. **Publique** (sans session) : ne renvoie que des données synthétiques |
| `GET /api/v1/patients` | Liste paginée des patients et de leurs tests sériques (session requise). Query : `search` (`patient_id`, prénom, nom ; mots combinés, sensible aux accents), `gender`, `city`, `country`, `birth_from`, `birth_to`, `sort_by`, `sort_order`, `page`, `page_size` |
| `GET /api/v1/patients/{id}` | Un patient et ses tests sériques, par son UUID `id` (session requise). Les tests sont liés par `patient_id` (ex. `HIS-00355`) |
| `GET /api/v1/synthetic-patients` | Liste paginée des patients synthétiques (session requise). Query : `search` (dans le `patient_id`), `patient_id` (exact), `sexe`, `jeu`, `phase`, `statut_parcours`, `organe`, `sort_by`, `sort_order`, `page`, `page_size` |
| `GET /api/v1/patients/{id}/synthetic-patients` | Les patients synthétiques d'un patient (`id` = son UUID), paginés (session requise). Query : `sort_by`, `sort_order`, `page`, `page_size`. 404 si le patient n'existe pas |

Le frontend doit envoyer le cookie avec chaque requête (`credentials: "include"`). Variables d'environnement dédiées : `DB_HOST`, `FRONTEND_URL`, `COOKIE_SECURE` (voir `.env.example`).

Pas encore en place : réinitialisation de mot de passe, vérification d'email, limitation de débit.

## Conventions de code

Le détail complet est dans [.claude/rules/](.claude/rules/). L'essentiel :

**Backend** ([backend.md](.claude/rules/backend.md))
- DDD simplifié : un dossier par contexte métier (`users`, `auth`, …) avec `entity`, `schemas`, `repository`, `services`, `router`.
- Flux de dépendance unique : `router → services → repository → entity`.
- Chaque route déclare un schéma d'entrée et un `response_model`. On ne renvoie jamais une entité SQLAlchemy.
- Filtrage, tri et pagination des listes côté backend.
- Principes SOLID, dépendances injectées par le constructeur via `Depends`.

**Frontend** ([frontend.md](.claude/rules/frontend.md))
- Un dossier par page ; le code partagé va dans `shared/`.
- Séparation stricte : la présentation (JSX) d'un côté, un hook par logique métier de l'autre.
- Formulaires avec React Hook Form et `zodResolver`.
- Toute réponse d'API est parsée avec Zod avant usage.
- Tous les appels API passent par TanStack Query, tous les tableaux par TanStack Table (filtrage, tri et pagination côté backend).

**Commun**
- **Aucune valeur en dur** : toute valeur qui porte un sens est une constante de `backend/app/constants/` ou `frontend/src/constants/`. Ce qui change selon l'environnement et les secrets vont dans `.env`.
- Ne jamais commiter de secrets (`.env`, `.venv`, `node_modules` et `dependencies/volumes` sont dans les `.gitignore`).
- Design et UI : voir [DESIGN.md](DESIGN.md).

## Tests

| Périmètre | Outil | Emplacement |
| --- | --- | --- |
| Backend (services, routes, repositories) | pytest | `backend/app/<contexte>/test_*.py` |
| Frontend (utils, schémas, hooks, composants) | Vitest | à côté du fichier testé |
| Frontend (parcours critiques) | Playwright | `frontend/e2e/<contexte>.spec.ts` |

Scripts attendus dans `frontend/package.json` : `test`, `test:coverage`, `test:e2e`. Les tests e2e tournent contre le vrai backend avec une base de données de test dédiée.

## Travailler avec Claude Code

Le dossier [.claude/](.claude/) configure des sous-agents spécialisés qui appliquent les règles du projet :

| Agent | Rôle |
| --- | --- |
| `backend-developer` | Code backend : contexte métier, entité, schéma, repository, service, route |
| `backend-auth` | Authentification email / mot de passe et sécurité associée |
| `backend-tester` | Tests backend avec pytest |
| `frontend-developer` | Code frontend : page, composant, hook, formulaire, tableau |
| `frontend-tester` | Tests frontend avec Vitest et Playwright |

Les skills `security-audit` et `ui-ux-pro-max` sont utilisés respectivement pour la sécurité et l'interface. Les skills Better Auth (`create-auth`, …) ciblent une stack TypeScript et ne s'appliquent pas à ce projet.
