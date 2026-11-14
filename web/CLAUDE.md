# Contexte du projet

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

## Authentification

Système **email / mot de passe**, implémenté côté backend FastAPI. Les skills Better Auth de `.claude/skills` (`create-auth`, `email-and-password-best-practices`, …) ciblent une stack TypeScript et ne s'appliquent pas ici.

- Le backend est la source de vérité : toute validation côté frontend (Zod) est une aide à l'utilisateur, jamais une garantie de sécurité. Le backend revalide toujours avec Pydantic.
- Le mot de passe n'est jamais stocké ni loggé en clair, ni renvoyé dans une réponse.
- Bibliothèque : **FastAPI Users** (en mode maintenance : correctifs de sécurité seulement). Son adaptateur SQLAlchemy est **asynchrone** : l'auth utilise `AsyncSession` et `asyncpg`, ce qui déroge à l'exemple synchrone de `.claude/rules/backend.md`.
- Session : jeton opaque **stocké en base** (table `accesstoken`), transporté par un cookie `HttpOnly` / `SameSite=lax`, `Secure` sauf `COOKIE_SECURE=false`. La déconnexion supprime la ligne : la session est révoquée côté serveur. Mots de passe hachés en **Argon2id** (paramètres dans `constants/auth.py`).
- Routes : `POST /auth/register`, `POST /auth/login` (formulaire `username` = email + `password`), `POST /auth/logout`, `GET` et `PATCH /users/me`. Protéger une route : `Depends(current_active_user)` (`auth/dependencies.py`).
- **Pas encore en place** (décisions à prendre) : réinitialisation de mot de passe et vérification d'email (fournisseur d'envoi d'email non choisi), limitation de débit, révocation des autres sessions au changement de mot de passe, migrations (les tables sont créées au démarrage dans `main.py`).

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
