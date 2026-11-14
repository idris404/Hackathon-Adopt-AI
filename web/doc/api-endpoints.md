# Catalogue des endpoints

Base URL en local : `http://localhost:8000/api/v1`. Toutes les routes métier vivent sous `/api/v1` ([D-01](api-decisions.md#d-01--versionnement-par-préfixe-apiv1)). Les décisions derrière chaque comportement sont dans [api-decisions.md](api-decisions.md) ; les renvois `D-xx` y mènent.

Dernière mise à jour : 2026-11-14 · 16 opérations.

## Vue d'ensemble

| Méthode | Chemin | Protection | Rôle |
| --- | --- | --- | --- |
| `GET` | `/analysis/result` | **Publique** | Résultat d'analyse du modèle (cas synthétique) |
| `POST` | `/auth/register` | Publique | Inscription |
| `POST` | `/auth/login` | Publique | Connexion (pose le cookie de session) |
| `POST` | `/auth/logout` | Session | Déconnexion de l'appareil courant |
| `POST` | `/auth/logout-all` | Session | Déconnexion de tous les appareils |
| `GET` · `PATCH` | `/users/me` | Session | Lire / modifier son profil |
| `GET` · `PATCH` · `DELETE` | `/users/{id}` | Session **superutilisateur** | Gestion d'un utilisateur |
| `GET` | `/patients` | Session | Liste paginée des patients, avec leurs tests sériques |
| `GET` | `/patients/{id}` | Session | Un patient, avec ses tests sériques |
| `GET` | `/synthetic-patients` | Session | Liste paginée des patients synthétiques |
| `GET` | `/patients/{id}/synthetic-patients` | Session | Les patients synthétiques d'un patient |

**Protection « Session »** : cookie `HttpOnly` posé par `POST /auth/login`. Le client doit l'envoyer avec chaque requête (`credentials: "include"`). Sans session valide : `401`.

**Identifiants, à ne pas confondre** : `id` est l'**UUID** d'un patient (clé technique, utilisé dans les URL) ; `patient_id` est son **identifiant fonctionnel** unique, du type `HIS-00355` ou `SYN-0001` (utilisé pour la liaison avec les patients synthétiques et les tests sériques, et dans les filtres). Voir [D-13](api-decisions.md#d-13--la-liaison-se-fait-par-patient_id-pas-par-id).

## Conventions communes

### Listes paginées

Les endpoints de liste (`/patients`, `/synthetic-patients`, `/patients/{id}/synthetic-patients`) renvoient tous la même enveloppe ([D-04](api-decisions.md#d-04--liste-uniforme-pagination-tri-et-filtres-côté-serveur)) :

```json
{ "items": [ … ], "total": 51000, "page": 1, "page_size": 20 }
```

| Paramètre | Type | Défaut | Contrainte |
| --- | --- | --- | --- |
| `page` | entier | `1` | ≥ 1 |
| `page_size` | entier | `20` | entre 1 et **100** |
| `sort_by` | énumération | selon l'endpoint | valeurs listées par endpoint ; toute autre → `422` |
| `sort_order` | `asc` \| `desc` | `asc` | |

- `total` compte **tous** les résultats correspondant aux filtres, pas seulement la page.
- Les valeurs `NULL` arrivent **toujours en dernier**, dans les deux sens de tri. L'ordre reste stable d'une page à l'autre ([D-05](api-decisions.md#d-05--tri-sur-liste-blanche-valeurs-nulles-en-dernier-ordre-stable)).
- Un **paramètre inconnu** est refusé (`422`), pas ignoré ([D-06](api-decisions.md#d-06--validation-stricte-des-query-params)). Un paramètre **vide** (`?search=`) est accepté et équivaut à l'absence de filtre.
- Une page au-delà de la fin renvoie `items: []` avec le `total` correct.

### Recherche et filtres texte

- `search` : « contient », sans tenir compte de la casse, `%` et `_` traités comme du texte. **Sensible aux accents** (« andre » ne trouve pas « André »). Voir [D-07](api-decisions.md#d-07--recherche-insensible-à-la-casse-sensible-aux-accents).
- Les filtres texte exacts (`city`, `country`, `patient_id`, `jeu`, `phase`, …) comparent l'égalité complète, sans tenir compte de la casse (« rein » ne trouve pas « Rein-Pancréas »).

### Erreurs

| Code | Corps | Quand |
| --- | --- | --- |
| `401` | `{"detail": "Unauthorized"}` | Pas de session valide ou compte inactif |
| `403` | `{"detail": "Forbidden"}` | Session valide mais droits insuffisants (`/users/{id}`) |
| `404` | `{"detail": "PATIENT_NOT_FOUND"}` | Patient inconnu |
| `400` | `{"detail": "LOGIN_BAD_CREDENTIALS"}` | Identifiants invalides (même code pour email inconnu, mauvais mot de passe ou compte désactivé) |
| `405` | `{"detail": "Method Not Allowed"}` | Écriture tentée sur une ressource en lecture seule ([D-09](api-decisions.md#d-09--patients-et-patients-synthétiques-en-lecture-seule)) |
| `422` | `{"detail": [ {loc, msg, type}, … ]}` | Entrée invalide : format de FastAPI, un objet par champ fautif |

Les erreurs métier ont un `detail` **constant et stable** (code en majuscules), à tester côté client ; ne pas dépendre d'un message libre ([D-03](api-decisions.md#d-03--erreurs-métier-un-code-stable-converti-à-un-seul-endroit)).

---

## Analyse

### `GET /analysis/result` — publique

Renvoie le résultat du modèle pour un cas. **Aucune authentification** ([D-02](api-decisions.md#d-02--toutes-les-routes-métier-exigent-une-session-une-seule-exception)). Données **synthétiques uniquement** : `synthetic` vaut toujours `true` ([D-10](api-decisions.md#d-10--le-résultat-danalyse-est-public-parce-quil-est-synthétique)).

Pas de paramètre. Réponse `200` :

```json
{
  "case_id": "SYN-CASE-001",
  "synthetic": true,
  "phase": "pre_transplant",
  "profile": {
    "profile_score": 4,
    "score_status": "pending_review",
    "proposed_risk_category": "medium",
    "category_status": "pending_review",
    "factors": [],
    "missing_data": []
  },
  "assays": [],
  "history_pattern": "negative_constant",
  "history_pattern_status": "pending_review",
  "trend": "stable",
  "discordances": [],
  "review_status": "human_review_required",
  "candidate_for_simplified_review": false,
  "triggered_rules": [],
  "ruleset_version": "pending_review",
  "uncertainties": [],
  "human_validation_required": true,
  "provenance": { "source_record_copied": false, "generator_version": "demo-v1" }
}
```

Les champs de statut sont des chaînes libres, les listes vides n'ont pas de schéma d'éléments connu ([D-11](api-decisions.md#d-11--types-lâches-là-où-le-format-nest-pas-connu)).

---

## Authentification et utilisateurs

Détail du mécanisme (cookie, Argon2id, durée de session) : `CLAUDE.md`, section « Authentification ».

| Endpoint | Corps | Succès | Erreurs |
| --- | --- | --- | --- |
| `POST /auth/register` | JSON `{email, password}` (mot de passe 12–256 caractères) | `201`, l'utilisateur (jamais de mot de passe ni de hash) | `400` (email déjà utilisé), `422` |
| `POST /auth/login` | JSON `{email, password}` | `204`, cookie de session posé | `400 LOGIN_BAD_CREDENTIALS`, `422` |
| `POST /auth/logout` | — | `204`, session courante révoquée côté serveur | `401` |
| `POST /auth/logout-all` | — | `204`, toutes les sessions de l'utilisateur révoquées | `401` |
| `GET /users/me` | — | `200`, l'utilisateur | `401` |
| `PATCH /users/me` | JSON, champs à modifier | `200`, l'utilisateur | `400`, `401`, `422` |
| `GET` · `PATCH` · `DELETE /users/{id}` | — / JSON / — | `200` / `200` / `204` | `401`, `403`, `404`, `422` |

---

## Patients

Table `patients` : identité uniquement. Les prénoms, noms, villes et pays sont **fictifs** ([D-14](api-decisions.md#d-14--identités-fictives-et-déterministes)). Chaque patient embarque ses tests sériques (`serum_tests`), liés par `patient_id`. La liste est vide si aucun historique n'a été seedé pour lui.

L'historique vient de `data-model/data/serum_test_history.csv`. Ce sont des valeurs **synthétiques** de démonstration, pas des résultats biologiques cliniques. `*_output` vaut `1` si la valeur de l'antigène est ≥ 500, sinon `0`.

### Objet `SerumTest`

| Champ | Type | Remarque |
| --- | --- | --- |
| `id` | UUID | Déduit de `patient_id` + `test_date` |
| `patient_id` | texte | Identifiant fonctionnel du patient (ex. `HIS-00355`) |
| `graft_date`, `test_date` | date ISO | |
| `b12`, `b13`, `dr53`, `dr51`, `dq10` | entier | Valeur simulée (noms du CSV en minuscules : `B12` → `b12`) |
| `b12_output`, `b13_output`, `dr53_output`, `dr51_output`, `dq10_output` | `0` \| `1` | Positivité au seuil 500 |
| `profile` | `A` \| `B` \| `C` | Stabilité complète, fluctuations partielles, très fluctuant |

Les tests d'un patient sont triés par `test_date` croissante.

### Objet `Patient`

| Champ | Type | Remarque |
| --- | --- | --- |
| `id` | UUID | Clé technique ; c'est lui qui est dans les URL |
| `patient_id` | texte | Identifiant fonctionnel **unique** (ex. `HIS-00355`) |
| `firstname`, `lastname` | texte | |
| `birth` | date ISO ou `null` | `null` quand la source n'a pas de date de naissance |
| `gender` | `M` \| `F` | |
| `city`, `country` | texte | |
| `created_at` | date-heure ISO | |
| `serum_tests` | liste de `SerumTest` | `[]` si le patient n'a pas d'historique |

### `GET /patients`

Liste paginée. Paramètres, en plus de la pagination ci-dessus :

| Paramètre | Type | Effet |
| --- | --- | --- |
| `search` | texte, ≤ 100 caractères | Cherche dans `patient_id`, `firstname` **et** `lastname`. Chaque mot doit être trouvé (`jean dup`), dans n'importe lequel des trois champs |
| `gender` | `M` \| `F` | Filtre exact |
| `city`, `country` | texte, ≤ 100 | Égalité exacte, sans tenir compte de la casse |
| `birth_from`, `birth_to` | date ISO | Bornes **incluses** sur `birth`. Les patients sans date de naissance sont exclus dès qu'une borne est donnée. `birth_from` > `birth_to` → `422` |
| `sort_by` | `patient_id` \| `firstname` \| `lastname` \| `birth` \| `gender` \| `city` \| `country` \| `created_at` | Défaut : `lastname` |

Réponse `200` : `{items: [Patient], total, page, page_size}`. Chaque `Patient` contient `serum_tests`. Erreurs : `401`, `422`.

### `GET /patients/{id}`

Un patient par son UUID, avec `serum_tests`. `200` : un `Patient`. Erreurs : `401`, `404 PATIENT_NOT_FOUND`, `422` (`id` n'est pas un UUID ; un `patient_id` comme `HIS-00355` n'est **pas** accepté ici).

---

## Patients synthétiques

Table `patients_synthetiques` : une ligne du CSV `patients_synthetiques_v3.csv`. Un patient peut en avoir plusieurs ([D-13](api-decisions.md#d-13--la-liaison-se-fait-par-patient_id-pas-par-id)).

### Objet `SyntheticPatient`

Chaque élément porte **67 champs** : `id` (UUID), `created_at`, et les **65 colonnes du CSV**, sous leur nom (en minuscules : `hla_A` du CSV devient `hla_a`). Extrait :

```json
{
  "id": "…",
  "created_at": "…",
  "patient_id": "SYN-0001",
  "jeu": "actuel",
  "synthetic": true,
  "date_reference": "2026-11-14",
  "date_naissance": "1991-01-25",
  "age": 35,
  "sexe": "M",
  "phase": "pre_greffe",
  "…": "…",
  "_issue_statut": "…",
  "_verite_tgi": 0.3826
}
```

- `patient_id` est le `patient_id` du **patient** (clé étrangère vers `patients.patient_id`), pas son UUID.
- Les colonnes préfixées par `_` sont les **vérités terrain du générateur** (résultats à retrouver), exposées telles quelles ([D-16](api-decisions.md#d-16--les-vérités-terrain-sont-exposées-mais-non-triables)). Elles gardent leur `_` dans le JSON.
- Les colonnes parfois vides dans le CSV sont `null` ; les listes (dates, HLA) sont des chaînes libres telles que dans le CSV.
- La liste complète des colonnes est dans le schéma OpenAPI (`SyntheticPatientRead`).

### `GET /synthetic-patients`

Liste paginée, en plus de la pagination ci-dessus :

| Paramètre | Type | Effet |
| --- | --- | --- |
| `search` | texte, ≤ 100 | « Contient » dans le `patient_id` (`syn-00`) |
| `patient_id` | texte, ≤ 50 | `patient_id` **exact** (sans tenir compte de la casse). Renvoie une page vide si le patient n'existe pas, voir l'endpoint imbriqué ci-dessous |
| `sexe` | `M` \| `F` | Filtre exact |
| `jeu`, `phase`, `statut_parcours`, `organe` | texte, ≤ 100 | Égalité exacte, sans tenir compte de la casse |
| `sort_by` | `patient_id` \| `date_reference` \| `date_naissance` \| `age` \| `jeu` \| `phase` \| `statut_parcours` \| `statut_date` \| `organe` \| `created_at` | Défaut : `patient_id`. Les colonnes `_…` ne sont **pas** triables |

Réponse `200` : `{items: [SyntheticPatient], total, page, page_size}`. Erreurs : `401`, `422`. Une page de 100 éléments pèse environ 184 Ko ([D-17](api-decisions.md#d-17--taille-de-page-maximale-100)).

### `GET /patients/{id}/synthetic-patients`

Les patients synthétiques **d'un patient**, par l'UUID `id` du patient. Paramètres : uniquement `sort_by`, `sort_order`, `page`, `page_size` (mêmes valeurs que ci-dessus) ; le patient est dans l'URL, donc `patient_id`, `search` ou `jeu` donnent `422`.

| Cas | Réponse |
| --- | --- |
| Patient connu, avec des patients synthétiques | `200`, la page |
| Patient connu, sans patient synthétique | `200`, `items: []`, `total: 0` |
| **Patient inconnu** | `404 PATIENT_NOT_FOUND` |
| `id` qui n'est pas un UUID | `422` |

La différence entre « patient sans patient synthétique » (`200` vide) et « patient inexistant » (`404`) est volontaire ([D-15](api-decisions.md#d-15--lendpoint-imbriqué-distingue-patient-inconnu-et-liste-vide)) ; `GET /synthetic-patients?patient_id=` ne fait pas cette distinction.
