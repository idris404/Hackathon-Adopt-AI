---
paths:
  - "backend/**"
---

# Conventions de code — Backend (Python / FastAPI)

## Architecture : DDD simplifié, orienté modules

Un **dossier par contexte métier** (`users`, `auth`, …). Tout ce qui concerne un contexte vit dans son dossier ; on ne range jamais par type technique (pas de dossier global `models/`, `services/`, `routers/`). Seule exception : les constantes, regroupées dans le dossier global `constants/` (voir « Constantes : aucune valeur en dur »).

```
backend/app/
├── main.py                  # création de l'app FastAPI, inclusion des routers
├── core/                    # transverse : config, session DB, sécurité, exceptions de base
├── constants/               # TOUTES les constantes, un fichier par thème (voir « Constantes »)
└── users/                   # un contexte = un dossier
    ├── entity.py            # modèle SQLAlchemy
    ├── schemas.py           # schémas Pydantic (entrées / sorties)
    ├── repository.py        # accès base de données
    ├── services.py          # logique métier
    ├── router.py            # routes HTTP
    ├── exceptions.py        # erreurs métier du contexte
    ├── dependencies.py      # providers FastAPI (Depends) du contexte
    └── test_services.py     # tests du contexte (voir « Tests »)
```

N'ajouter un fichier que s'il est utile : un contexte simple n'a pas besoin de `dependencies.py` ou `exceptions.py`. En revanche, ne jamais fusionner deux responsabilités dans un même fichier.

### Rôle de chaque couche

Le flux de dépendance est unique : `router → services → repository → entity`. Aucune couche ne connaît celle qui est au-dessus d'elle.

| Fichier | Responsabilité | Interdit |
| --- | --- | --- |
| `entity.py` | Modèle SQLAlchemy 2.x (`Mapped`, `mapped_column`) : colonnes, relations, invariants simples. | Logique applicative, import de Pydantic ou de FastAPI. |
| `schemas.py` | Schémas Pydantic : un par intention (`UserCreate`, `UserUpdate`, `UserRead`, `UserFilters`…). | Réutiliser un même schéma en entrée et en sortie. |
| `repository.py` | Requêtes SQL via `select()` ; retourne des entités. Fait `flush`, pas de règle métier. | Règle métier, `HTTPException`, schémas Pydantic. |
| `services.py` | Logique métier, orchestration de plusieurs repositories, gestion de la transaction (`commit`). | `HTTPException`, `Request`, tout ce qui est HTTP. |
| `router.py` | HTTP uniquement : valide l'entrée (schéma), appelle **un** service, renvoie un `response_model`. | Requête SQL, règle métier. |

## Principes SOLID (dans la mesure du possible)

- **S — Responsabilité unique** : un fichier, une raison de changer. Une classe de service par agrégat ; si elle grossit, la scinder (`UserRegistrationService`, `UserProfileService`…).
- **O — Ouvert/fermé** : étendre par ajout (nouvelle stratégie, nouveau service) plutôt que par `if/elif` sur des types dans du code existant.
- **L — Substitution de Liskov** : toute implémentation d'un `Protocol` ou d'une classe abstraite doit pouvoir remplacer l'autre sans changer le comportement attendu.
- **I — Ségrégation des interfaces** : des `Protocol` petits et ciblés plutôt qu'une grosse interface « fourre-tout ».
- **D — Inversion de dépendance** : un service reçoit ses dépendances (repository, session, hasher…) **par le constructeur**, fournies via `Depends`. Jamais de session ou de client instancié à l'intérieur d'un service. Cela permet de les remplacer dans les tests.

```python
# users/dependencies.py
def get_user_service(session: Session = Depends(get_session)) -> UserService:
    return UserService(UserRepository(session))
```

## Pydantic : valider les entrées ET les sorties

- Chaque route déclare un schéma d'entrée (corps, query, path) et un `response_model`.
- On ne renvoie **jamais** une entité SQLAlchemy directement : le router renvoie un schéma `*Read` (`model_config = ConfigDict(from_attributes=True)`).
- Les champs sensibles (hash de mot de passe, tokens…) n'apparaissent dans aucun schéma de sortie.
- Les schémas d'entrée sont stricts : contraintes de type et de forme (`EmailStr`, `Field(min_length=…)`) déclarées dans le schéma, pas revérifiées à la main dans le service.

## Listes : filtrage, tri et pagination côté backend

Le frontend n'applique aucun filtre sur les tableaux : tout est fait ici.

- Les endpoints de liste acceptent des query params validés par un schéma (`filters`, `sort_by`, `sort_order`, `page`, `page_size`).
- Les filtres sont traduits en SQL dans le **repository** ; le tri se fait sur une liste blanche de colonnes (jamais un nom de colonne brut venant du client).
- `page_size` est borné par une constante (`MAX_PAGE_SIZE`, dans `constants/pagination.py`).
- Réponse paginée uniforme : `{ "items": [...], "total": int, "page": int, "page_size": int }`.

## Erreurs

- Les services lèvent des **exceptions métier** définies dans `exceptions.py` du contexte (`UserAlreadyExistsError`, `InvalidCredentialsError`…), qui héritent d'une base commune dans `core/`.
- Leur conversion en code HTTP (404, 409, 401…) se fait à un seul endroit : des exception handlers enregistrés dans `main.py`, pas des `try/except` dans chaque route.

## Dépendances entre contextes

- Un contexte n'importe pas le `repository` ni les détails internes d'un autre contexte. Il passe par son **service** (son API publique).
- Les relations SQLAlchemy entre entités de contextes différents sont déclarées avec des références en chaîne (`relationship("Order")`) pour éviter les imports circulaires.
- Le code réellement transverse (config, session DB, sécurité) va dans `core/`, pas dans un contexte « fourre-tout ».

## Constantes : aucune valeur en dur

Aucune valeur « en dur » dans le code. Toute valeur littérale qui porte un sens est déclarée **une seule fois**, dans une constante du dossier global `backend/app/constants/`, puis importée là où elle sert. Cela inclut les **valeurs des règles métier**.

### Ce qui va dans `constants/`

- **Valeurs de règles métier** : longueurs minimale et maximale, seuils, plafonds, quotas, durées de validité, délais, taux, nombre de tentatives autorisées.
- **Limites techniques** : taille de page par défaut et maximale, bornes de validation, longueurs de colonnes.
- **Ensembles fermés** : statuts, rôles, types, déclarés en `StrEnum`.
- **Messages et codes d'erreur**, motifs regex, noms de cookies et d'en-têtes, préfixes de routes, valeurs par défaut.

### Organisation

```
constants/
├── pagination.py    # DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
├── auth.py          # PASSWORD_MIN_LENGTH, PASSWORD_MAX_LENGTH, RESET_TOKEN_TTL_MINUTES
└── users.py         # règles métier du contexte users
```

- Un fichier par thème ou par contexte, nommé comme lui. Pas de fichier fourre-tout `constants.py`.
- Noms en `UPPER_SNAKE_CASE`, annotées `Final`. L'unité figure dans le nom pour une durée ou une taille (`_SECONDS`, `_MINUTES`, `_BYTES`).
- `constants/` est un module **feuille** : il n'importe rien d'autre de `app/`, pour éviter les imports circulaires. Les contextes, `core/` et les tests l'importent.

```python
# constants/auth.py
from typing import Final

PASSWORD_MIN_LENGTH: Final = 12
PASSWORD_MAX_LENGTH: Final = 256

# users/schemas.py
password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)
```

### Constante ou configuration ?

- **Constante** : valeur fixe, identique dans tous les environnements (règle métier, limite, message).
- **Configuration** (`core/config.py`, variables d'environnement) : valeur qui **change selon l'environnement** ou qui est **secrète** (URL de base de données, clés, URL du frontend). Jamais de secret dans `constants/`.
- Une valeur par défaut de configuration peut venir de `constants/`.

### Règle métier : la valeur ici, la logique dans le service

Le service contient la **logique** d'une règle métier ; seule sa **valeur** (le seuil, la durée, la limite) va dans `constants/`. Changer une règle ne doit demander de modifier qu'une constante.

### Tolérés

`0`, `1`, `-1`, `""`, `None`, `True` / `False`, collections vides et messages de log purement locaux. Dans les tests, toute valeur d'une règle métier est **importée** depuis `constants/` (un test ne doit pas continuer à passer avec une ancienne valeur recopiée) ; les données fictives (emails, noms) peuvent rester littérales.

## Style

- Annotations de type partout (paramètres, retours, attributs). Pas de `Any` sauf justification en commentaire.
- `snake_case` pour fonctions, variables et fichiers ; `PascalCase` pour les classes.
- Configuration lue depuis les variables d'environnement via un objet de settings dans `core/config.py` ; jamais de `os.environ` dispersé dans le code.
- Pas de secrets en dur ni dans les logs.

## Tests

- `pytest`, **dans le dossier du contexte**, nommés `test_*.py` (sinon pytest ne les découvre pas) : `test_services.py`, `test_router.py`, `test_repository.py`.
- Les tests de service remplacent le repository par un faux ou un mock (c'est le bénéfice de l'injection par constructeur).
- Les tests de router utilisent `TestClient` avec `app.dependency_overrides`.
- Tout nouveau service ou toute nouvelle règle métier arrive avec au moins un test du cas nominal et un test d'erreur.
