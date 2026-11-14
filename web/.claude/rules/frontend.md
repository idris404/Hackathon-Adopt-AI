---
paths:
  - "frontend/**"
---

# Conventions de code — Frontend (Vite / React / TypeScript)

## Architecture : orientée modules

Chaque **page** a son propre dossier qui contient tout le code de son contexte. Le code réutilisable ailleurs va dans `shared/`. Seule exception : les constantes, regroupées dans le dossier global `constants/` (voir « Constantes : aucune valeur en dur »).

```
frontend/src/
├── app/                         # bootstrap : router, providers (QueryClient…)
├── constants/                   # TOUTES les constantes, un fichier par thème (voir « Constantes »)
├── pages/
│   └── users/                   # une page = un dossier
│       ├── UsersPage.tsx        # PRÉSENTATION uniquement (JSX)
│       ├── components/          # composants propres à cette page
│       ├── hooks/               # un hook par logique métier
│       │   ├── useUsersTable.ts
│       │   └── useCreateUserForm.ts
│       ├── schemas.ts           # schémas Zod (+ types inférés)
│       ├── utils.ts             # JavaScript pur (voir plus bas)
│       └── *.test.ts(x)         # tests Vitest, à côté du fichier testé
└── shared/                      # tout ce qui sert à plusieurs pages
    ├── components/
    ├── hooks/
    ├── utils/
    └── schemas/
```

- Un dossier de page ne contient **que** du code de son contexte.
- Une page n'importe **jamais** depuis une autre page. Si deux pages ont besoin du même code, il passe dans `shared/`.

## Séparation logique métier / présentation

- **Jamais de logique métier et de présentation dans le même fichier.**
- Un composant de présentation contient du JSX, appelle des hooks et branche leurs valeurs de retour. Il ne fait pas d'appel API, ne transforme pas de données, n'applique pas de règle.
- **Un hook par logique métier**, invoqué depuis le composant de présentation. Un hook = une responsabilité (`useUsersTable`, `useCreateUserForm`, `useDeleteUser`) ; si un hook en fait deux, le scinder.
- Les hooks retournent ce dont la vue a besoin (données, états, handlers) sous une forme prête à afficher.

```tsx
// pages/users/UsersPage.tsx — présentation seule
export function UsersPage() {
  const { table, isLoading, error } = useUsersTable()
  if (isLoading) return <Spinner />
  if (error) return <ErrorMessage error={error} />
  return <DataTable table={table} />
}
```

## `utils.ts` / `helpers.ts` : JavaScript pur

Le fichier `utils` (ou `helpers`) d'un contexte contient du code **JavaScript pur**, sans React ni hook : transformations de texte, formules de calcul, appels API (`fetch`), etc.

- Fonctions simples, sans état et testables isolément.
- Si le fichier grossit, le scinder en dossier (`utils/format.ts`, `utils/api.ts`), toujours dans le contexte concerné.
- Un utilitaire utilisé par plusieurs pages va dans `shared/utils/`.

## Formulaires : React Hook Form + Zod

- **Toujours** `react-hook-form` avec un résolveur Zod (`zodResolver`). Pas de formulaire géré à la main avec `useState`.
- Le schéma Zod est défini dans `schemas.ts` du contexte ; le type du formulaire est inféré (`z.infer<typeof schema>`), jamais réécrit à la main.
- La logique du formulaire (`useForm`, `onSubmit`, mutation, gestion d'erreur) vit dans **un hook dédié** (`useCreateUserForm`) ; le composant ne fait que rendre les champs.
- Les erreurs de validation du backend (réponse 422 / 4xx) sont affichées sur les champs concernés.

## Appels externes : toujours valider la sortie avec Zod

- Toute réponse d'un appel externe (API backend, service tiers) est **parsée avec un schéma Zod** avant d'être utilisée : `schema.parse(await response.json())`. On ne caste jamais (`as`) une réponse réseau en type TypeScript.
- Cette validation se fait dans la fonction d'appel (dans `utils`), de sorte que les hooks et les composants reçoivent toujours des données déjà typées et vérifiées.
- Une réponse qui ne respecte pas le schéma est traitée comme une erreur, pas ignorée.

## TanStack Query : tous les appels API

- Toute lecture passe par `useQuery`, toute écriture par `useMutation`. Pas de `useEffect` + `fetch`.
- `useQuery` / `useMutation` sont appelés **dans les hooks** du contexte ; la `queryFn` appelle une fonction de `utils` (qui valide la sortie avec Zod).
- Les clés de requête sont centralisées (une fabrique de clés par contexte) et jamais écrites en dur à plusieurs endroits.
- Après une mutation, invalider les clés concernées.

## TanStack Table : tous les tableaux

- Tout tableau utilise TanStack Table (`@tanstack/react-table`).
- **Le filtrage, le tri et la pagination se font côté backend.** Le frontend n'applique aucun filtre sur les lignes déjà chargées.
- Configuration : `manualFiltering: true`, `manualSorting: true`, `manualPagination: true`, et `rowCount` (ou `pageCount`) fourni par le `total` renvoyé par l'API.
- L'état des filtres, du tri et de la pagination est contrôlé par le hook du tableau, envoyé en query params à l'API, et **inclus dans la clé de requête** TanStack Query.
- Remettre la page à 0 quand un filtre, le tri ou la taille de page change.
- Garder les résultats précédents pendant le chargement (`placeholderData: keepPreviousData`) pour éviter le clignotement.

## `shared/` : ce qui est réutilisable

- Un composant ou un hook qui peut être utilisé ailleurs dans le projet va dans `shared/`.
- Règle pratique : on le crée dans le dossier de la page tant qu'il n'est utile qu'à elle ; dès qu'un second usage apparaît (ou qu'il est clairement générique : bouton, table, champ de formulaire, hook de pagination…), on le déplace dans `shared/`.
- `shared/` n'importe jamais depuis `pages/`.

## Constantes : aucune valeur en dur

Aucune valeur « en dur » dans le code. Toute valeur littérale qui porte un sens est déclarée **une seule fois**, dans le dossier global `frontend/src/constants/`, puis importée là où elle sert. Cela inclut les **valeurs des règles métier**.

### Ce qui va dans `constants/`

- **Valeurs de règles métier** : longueurs minimale et maximale, seuils, plafonds, durées, nombre d'éléments.
- **Limites techniques** : taille de page par défaut et options proposées, délai de debounce, `staleTime` et autres durées de cache, timeouts.
- **Chemins de routes** et **endpoints d'API**.
- **Ensembles fermés** : statuts, rôles, types.
- **Messages** : erreurs de validation Zod, erreurs d'API, libellés réutilisés à plusieurs endroits.
- Clés de stockage, noms de cookies ou d'en-têtes, regex.

### Organisation

```
constants/
├── routes.ts        # ROUTES
├── api.ts           # API_ENDPOINTS
├── pagination.ts    # DEFAULT_PAGE_SIZE, PAGE_SIZE_OPTIONS
├── auth.ts          # PASSWORD_MIN_LENGTH, PASSWORD_MAX_LENGTH
└── users.ts         # règles métier du contexte users
```

- Un fichier par thème ou par contexte, nommé comme lui. Pas de fichier fourre-tout `constants.ts`.
- Noms en `UPPER_SNAKE_CASE`. Pour un groupe de valeurs liées, un objet `as const` (jamais un `enum`), avec le type dérivé : `type Role = (typeof ROLES)[keyof typeof ROLES]`.
- `constants/` est un module **feuille** : aucun import de `pages/`, `shared/` ou `app/`, pas de React. Tout le reste l'importe : schémas Zod, utils, hooks, composants.

```ts
// constants/auth.ts
export const PASSWORD_MIN_LENGTH = 12 // miroir de backend/app/constants/auth.py
export const PASSWORD_MAX_LENGTH = 256

// pages/login/schemas.ts
password: z.string().min(PASSWORD_MIN_LENGTH).max(PASSWORD_MAX_LENGTH)
```

### Règles métier : le backend fait foi

Les règles métier sont définies et appliquées par le backend (`backend/app/constants/`). Le frontend n'en garde une copie que pour aider la saisie, sous le même nom, avec un commentaire qui renvoie au fichier backend. En cas d'écart, le backend a raison.

### Constante ou environnement ?

- **Constante** : valeur fixe, identique dans tous les environnements.
- **Environnement** : valeur qui change selon l'environnement (URL de l'API) → variable `VITE_*`, lue par **un seul module** validé par Zod (`app/env.ts`), pas dans `constants/`. Aucun secret côté frontend.

### Tolérés

`0`, `1`, `-1`, `""`, `null`, `true` / `false`, tableaux et objets vides. Les classes de style et les valeurs visuelles suivent `DESIGN.md`. Un texte statique affiché par un seul composant (titre, libellé de bouton) peut rester dans le JSX ; dès qu'il est réutilisé, ou qu'il s'agit d'un message d'erreur ou de validation, il va dans `constants/`.

## Tests : Vitest et Playwright

Deux niveaux, deux outils. Les tests sont écrits par l'agent `frontend-tester`.

| Niveau | Outil | Ce qu'il couvre | Emplacement |
| --- | --- | --- | --- |
| Unitaire, hook, composant | **Vitest** (avec jsdom et React Testing Library) | `utils`, schémas Zod, hooks, composants de présentation | À côté du fichier testé : `utils.test.ts`, `hooks/useUsersTable.test.ts`, `UsersPage.test.tsx` |
| Parcours utilisateur (e2e) | **Playwright** | Parcours critiques dans un vrai navigateur, contre le vrai backend | `frontend/e2e/<contexte>.spec.ts` |

Scripts attendus dans `package.json` : `test` (Vitest, une exécution), `test:coverage`, `test:e2e` (Playwright).

### Vitest

- Configuration dans `vite.config.ts`, avec `defineConfig` importé de `vitest/config` : `test.environment` à `jsdom`, `test.setupFiles`, et `test.include` limité à `src/**/*.test.{ts,tsx}` pour que Vitest ne ramasse jamais les specs Playwright.
- Fichiers `*.test.ts` et `*.test.tsx` placés dans le dossier de la page, à côté du fichier testé. Les tests du code de `shared/` vivent dans `shared/`.
- **`utils`** : tests purs, sans React. Pour une fonction d'appel API, remplace `fetch` et vérifie deux choses : une réponse valide est renvoyée typée, une réponse qui ne respecte pas le schéma Zod est rejetée.
- **Schémas Zod** : cas valides, invalides et bornes (les bornes sont importées depuis `constants/`).
- **Hooks** : `renderHook` avec un wrapper qui fournit un `QueryClient` **neuf à chaque test**, nouvelles tentatives désactivées. On remplace la fonction d'appel API de `utils` ; on ne simule jamais TanStack Query, Zod ni React Hook Form eux-mêmes.
- **Composants** : React Testing Library et `user-event`, requêtes par rôle ou par libellé (`getByRole`, `getByLabelText`). On teste ce que l'utilisateur voit et fait, pas l'implémentation. Le hook du composant est simulé, ou alimenté par un `QueryClient` de test.
- Pas de snapshot du DOM entier.
- Couverture avec le fournisseur `v8`, via `test:coverage`.

### Playwright

- Configuration dans `frontend/playwright.config.ts`, avec `testDir` sur `e2e/` et `baseURL` lue depuis une variable d'environnement.
- Les tests tournent contre le **vrai frontend et le vrai backend** : c'est la seule façon de vérifier le filtrage, le tri et la pagination côté backend. Le backend utilise une **base de données de test dédiée**, jamais la base de développement ni un environnement réel.
- Le réseau n'est simulé (`page.route`) que pour des cas impossibles à provoquer autrement (erreur 500, expiration de délai). Le cas nominal passe par le vrai backend.
- Les éléments sont ciblés par **rôle, libellé ou texte** (`getByRole`, `getByLabel`), jamais par sélecteur CSS ou XPath fragile. Un élément impossible à cibler ainsi est souvent un défaut d'accessibilité à corriger dans le code.
- Assertions « web-first » (`await expect(locator).toBeVisible()`) qui attendent d'elles-mêmes. Jamais de `waitForTimeout`.
- Tests **indépendants** : chacun crée ses propres données (valeur unique par test) et ne dépend d'aucun ordre. L'état d'authentification est réutilisé (`storageState`) au lieu de se reconnecter à chaque test.
- Les identifiants du compte de test viennent de variables d'environnement `E2E_*`, documentées dans `.env.example`, jamais écrits dans une spec.
- Ne couvrir que les **parcours critiques** (inscription et connexion, création, liste avec filtre, tri et pagination) : peu de tests, stables.

### Règles communes

- Un test vérifie un comportement et porte son nom. Arrange, Act, Assert.
- Déterministe : pas de dépendance à l'horloge réelle, au hasard ni à un réseau externe non maîtrisé.
- Aucune valeur en dur : toute valeur de règle métier ou tout message défini dans `constants/` est **importé**, jamais recopié. Seules les données fictives (emails, noms) restent littérales.
- Jamais de `test.only`, `it.skip` ou `test.fixme`, ni de test affaibli pour faire passer la suite.
- Un bug ou une règle non respectée révélé par un test se **rapporte**, il ne se masque pas.

## TypeScript et style

- Mode `strict` ; pas de `any`, pas de `as` pour « forcer » un type, pas de `// @ts-ignore`.
- Composants en `PascalCase` (`UsersPage.tsx`), hooks en `camelCase` préfixés `use` (`useUsersTable.ts`), utilitaires en `camelCase`.
- Types dérivés des schémas Zod (`z.infer`), pas de types dupliqués à la main.
- Jamais de secret dans le code frontend : seules les variables `VITE_*` publiques y sont lues.
