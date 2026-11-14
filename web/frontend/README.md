# Frontend

SPA Vite + React + TypeScript (strict). Conventions d'architecture et de code : [`../.claude/rules/frontend.md`](../.claude/rules/frontend.md).

## Démarrage

```bash
cp .env.example .env        # VITE_API_URL : origine du backend
npm install
npm run dev -- --strictPort # http://localhost:5173
```

Le backend doit autoriser cette origine (`FRONTEND_URL` dans `../.env`) : le cookie de session circule entre les deux.

## Scripts

| Script | Rôle |
| --- | --- |
| `npm run dev` | Serveur de développement |
| `npm run build` | Vérification des types (`tsc -b`) puis build de production |
| `npm run lint` | oxlint |
| `npm run preview` | Sert le build de production |

## Stack

React 19, Vite, TypeScript strict, Tailwind CSS 4, Motion, GSAP, TanStack Query, TanStack Table, Zod, React Hook Form, nuqs.
