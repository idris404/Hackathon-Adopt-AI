# Documentation

Décisions et références du projet, côté **backend / API**. Ce dossier complète `README.md` (démarrage) et `CLAUDE.md` (conventions) sans les remplacer.

| Fichier | Contenu |
| --- | --- |
| [api-endpoints.md](api-endpoints.md) | Catalogue des endpoints : méthode, chemin, protection, paramètres, réponses, format des erreurs. C'est la référence à consulter pour **appeler** l'API. |
| [api-decisions.md](api-decisions.md) | Journal des décisions prises sur l'API, avec le pourquoi et leurs conséquences. C'est la référence à consulter pour **comprendre ou faire évoluer** l'API. |

La documentation interactive générée par FastAPI reste la source exacte des schémas : `http://localhost:8000/docs` (OpenAPI : `/openapi.json`).

## Tenir cette documentation à jour

- **Un endpoint ajouté, retiré ou modifié** : mettre à jour `api-endpoints.md` dans la même modification que le code.
- **Une décision prise** (comportement d'un endpoint, convention, compromis) : ajouter une entrée à `api-decisions.md`, à la suite, avec le numéro suivant. Ne pas renuméroter ; une décision remplacée est marquée « Remplacée par D-xx », pas supprimée.
- Une entrée suit ce modèle :

```markdown
### D-xx — Titre court

- **Statut** : Demandée | Choix de conception | À confirmer
- **Décision** : ce qui a été retenu.
- **Pourquoi** : la contrainte ou la raison.
- **Conséquences** : ce que cela implique pour ceux qui appellent ou font évoluer l'API.
```

Statuts : **Demandée** = l'équipe l'a explicitement demandé ; **Choix de conception** = retenu pour appliquer les conventions du projet ; **À confirmer** = hypothèse faute de précision, à valider ou corriger.
