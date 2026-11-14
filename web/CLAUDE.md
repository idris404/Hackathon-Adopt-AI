# Contexte du projet

## Architecture

Monorepo avec deux applications séparées, plus les dépendances d'infrastructure :

```
web/
├── backend/        # API Python (FastAPI)
├── frontend/       # SPA Vite + React + TypeScript
└── dependencies/   # Docker Compose (PostgreSQL) — volume de données ignoré par git
```

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

- **PostgreSQL**, lancé via Docker Compose (`dependencies/compose.yml`).
- La configuration (URL de connexion, secrets) passe par les variables d'environnement : `.env` n'est jamais commité, `.env.example` documente les variables attendues.

## Authentification

Système **email / mot de passe**, implémenté côté backend FastAPI. Les skills Better Auth de `.claude/skills` (`create-auth`, `email-and-password-best-practices`, …) ciblent une stack TypeScript et ne s'appliquent pas ici.

- Le backend est la source de vérité : toute validation côté frontend (Zod) est une aide à l'utilisateur, jamais une garantie de sécurité. Le backend revalide toujours avec Pydantic.
- Le mot de passe n'est jamais stocké ni loggé en clair, ni renvoyé dans une réponse.

## Commandes

| Action | Commande | Dossier |
| --- | --- | --- |
| Lancer PostgreSQL | `docker compose -f ./dependencies/compose.yml up -d` | `web/` |
| Lancer le backend | `uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` | `web/backend/` |
| Lancer le frontend | `npm run dev -- --strictPort` | `web/frontend/` (port 5173) |

## Conventions

- Backend et frontend ne partagent pas de code : le contrat entre les deux est l'API HTTP (schémas Pydantic côté serveur, schémas Zod côté client).
- Toute donnée qui entre dans le système (corps de requête, query params, saisie utilisateur) est validée par un schéma ; toute donnée qui sort de l'API passe par un schéma de réponse Pydantic.
- Aucune valeur en dur : toute valeur littérale qui porte un sens, y compris les valeurs des règles métier, est une constante du dossier global `backend/app/constants/` ou `frontend/src/constants/`. Les valeurs qui changent selon l'environnement et les secrets passent par la configuration (`.env`), jamais par les constantes. Détail dans `.claude/rules/`.
- Ne jamais commiter de secrets : `.env`, `.venv`, `node_modules` et `dependencies/volume` sont dans le `.gitignore`.
- Design / UI : voir `DESIGN.md`.
