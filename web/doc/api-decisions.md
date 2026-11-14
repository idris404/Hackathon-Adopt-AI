# Décisions sur l'API backend

Journal des décisions prises sur les endpoints de l'API. Les comportements correspondants sont décrits dans [api-endpoints.md](api-endpoints.md).

**Statut** de chaque décision : **Demandée** (l'équipe l'a explicitement demandée), **Choix de conception** (retenue pour appliquer les conventions du projet), **À confirmer** (hypothèse faute de précision, à valider ou corriger). Les points encore ouverts sont regroupés [en fin de document](#points-ouverts).

Dernière mise à jour : 2026-11-14.

| | Décision |
| --- | --- |
| **Conventions transverses** | [D-01](#d-01--versionnement-par-préfixe-apiv1) Versionnement · [D-02](#d-02--toutes-les-routes-métier-exigent-une-session-une-seule-exception) Session · [D-03](#d-03--erreurs-métier-à-code-stable-converties-à-un-seul-endroit) Erreurs · [D-04](#d-04--listes-uniformes-paginées-triées-et-filtrées-côté-serveur) Listes · [D-05](#d-05--tri-sur-liste-blanche-valeurs-nulles-en-dernier-ordre-stable) Tri · [D-06](#d-06--validation-stricte-des-query-params) Query params · [D-07](#d-07--recherche-insensible-à-la-casse-sensible-aux-accents) Recherche · [D-08](#d-08--schémas-de-sortie-dédiés-jamais-dentité) Schémas · [D-09](#d-09--patients-et-patients-synthétiques-en-lecture-seule) Lecture seule |
| **Analyse** | [D-10](#d-10--le-résultat-danalyse-est-public-parce-quil-est-synthétique) Route publique · [D-11](#d-11--types-lâches-là-où-le-format-nest-pas-connu) Types lâches |
| **Patients et patients synthétiques** | [D-12](#d-12--endpoint-de-détail-dun-patient) Détail · [D-13](#d-13--la-liaison-se-fait-par-patient_id-pas-par-id) Liaison · [D-14](#d-14--identités-fictives-et-déterministes) Identités fictives · [D-15](#d-15--lendpoint-imbriqué-distingue-patient-inconnu-et-liste-vide) Route imbriquée · [D-16](#d-16--les-vérités-terrain-sont-exposées-mais-non-triables) Vérités terrain · [D-17](#d-17--taille-de-page-plafonnée-à-100) Taille de page · [D-18](#d-18--un-contexte-à-part-qui-passe-par-le-service-patients) Contextes · [D-19](#d-19--filtres-exposés-sur-les-patients-synthétiques) Filtres · [D-20](#d-20--dans-les-url-id-est-luuid-pas-le-patient_id) Nommage des URL |
| **Données et seed** | [D-21](#d-21--seed-en-deux-étapes-rejouable-à-ids-stables) Seed · [D-22](#d-22--pas-de-migrations-reset-des-tables-et-détection-de-schéma-obsolète) Migrations |
| **Signature** | [D-23](#d-23--signature-clinique-des-cas-simples) Signature clinique |

---

## Conventions transverses

### D-01 — Versionnement par préfixe `/api/v1`

- **Statut** : Choix de conception
- **Décision** : toutes les routes métier sont servies sous `/api/<version>`, aujourd'hui `/api/v1`. Un router de contexte ne porte pas la version, seulement son préfixe de contexte (`/patients`) ; c'est `main.py` qui le rattache à une version. La documentation (`/docs`, `/redoc`, `/openapi.json`) reste à la racine.
- **Pourquoi** : pouvoir introduire une `v2` quand un contrat change de façon incompatible, sans casser les clients de la `v1`.
- **Conséquences** : un test échoue si une route documentée n'est pas sous `/api/v1/`. Une route d'infrastructure (santé) va à la racine avec `include_in_schema=False`. Un ajout compatible (nouvelle route, champ optionnel) ne change pas la version. Les changements incompatibles faits jusqu'ici l'ont été **dans la `v1`**, faute de client connu (voir [D-13](#d-13--la-liaison-se-fait-par-patient_id-pas-par-id)) : à ne plus faire dès que le frontend consomme l'API.

### D-02 — Toutes les routes métier exigent une session, une seule exception

- **Statut** : Choix de conception
- **Décision** : toute route métier exige une session valide (cookie `HttpOnly`). La protection est posée sur le **router** (`dependencies=[Depends(current_active_user)]`), pas route par route : une route ajoutée plus tard est protégée par défaut. Les seules routes sans session sont `POST /auth/register`, `POST /auth/login` (qui ne peuvent pas l'exiger) et `GET /analysis/result` ([D-10](#d-10--le-résultat-danalyse-est-public-parce-quil-est-synthétique)).
- **Pourquoi** : le projet traite des données de santé, même ici synthétiques : l'accès authentifié est la règle, l'exception doit être justifiée.
- **Conséquences** : les endpoints des patients et des patients synthétiques ont chacun un test `401` sans session. Le cookie circulant entre le frontend et l'API, CORS autorise une origine explicite avec les identifiants, jamais `*`.

### D-03 — Erreurs métier à code stable, converties à un seul endroit

- **Statut** : Choix de conception
- **Décision** : une erreur métier est une exception du contexte (ex. `PatientNotFoundError`) levée par le service. Sa conversion en réponse HTTP se fait **uniquement** dans des handlers de `main.py`, avec un corps `{"detail": "<CODE>"}` où le code est une constante (`PATIENT_NOT_FOUND`, `LOGIN_BAD_CREDENTIALS`).
- **Pourquoi** : une seule place décide du code HTTP ; le client teste un code stable plutôt qu'un message. La connexion renvoie le même code pour email inconnu, mauvais mot de passe et compte désactivé, pour ne pas révéler quels comptes existent.
- **Conséquences** : une nouvelle erreur = une exception + une constante + un handler dans `main.py`. Les erreurs de validation gardent le format `422` de FastAPI.

### D-04 — Listes uniformes, paginées, triées et filtrées côté serveur

- **Statut** : Demandée pour `/patients` (filtres, recherche, tri) ; généralisée aux autres listes par convention
- **Décision** : tout endpoint de liste prend `page`, `page_size`, `sort_by`, `sort_order` et ses filtres, et renvoie `{items, total, page, page_size}`. Le frontend n'applique aucun filtre ni tri. Défauts : page 1, 20 éléments ; maximum 100 ([D-17](#d-17--taille-de-page-plafonnée-à-100)).
- **Pourquoi** : 51 000 lignes ne se filtrent pas côté client ; une enveloppe unique évite un cas particulier par écran.
- **Conséquences** : `total` compte tous les résultats filtrés (un second comptage par requête). Une page hors limites renvoie une liste vide avec le bon `total`.

### D-05 — Tri sur liste blanche, valeurs nulles en dernier, ordre stable

- **Statut** : Choix de conception
- **Décision** : `sort_by` n'accepte que des valeurs d'une énumération, que le repository traduit en colonne ; jamais un nom de colonne reçu tel quel. Les `NULL` sont placés **en dernier**, quel que soit le sens. Un départage final sur `id` rend l'ordre déterministe.
- **Pourquoi** : un nom de colonne brut exposerait le schéma (et permettrait de trier sur ce qui ne doit pas l'être) ; 503 patients n'ont pas de date de naissance, ils ne doivent pas encombrer le haut d'un tri ; sans départage, des lignes à valeur égale (très fréquentes : 2 phases pour 51 000 lignes) pourraient apparaître sur deux pages ou sur aucune.
- **Conséquences** : ajouter une colonne triable = une valeur d'énumération + une entrée dans la table de correspondance. Vérifié sur les données réelles : 3 pages triées sur une colonne à fortes égalités donnent 300 `id` distincts.

### D-06 — Validation stricte des query params

- **Statut** : Choix de conception
- **Décision** : un paramètre de requête **inconnu** est refusé (`422`), pas ignoré. Une valeur **vide** (`?search=`) est acceptée et équivaut à l'absence de filtre. Des bornes incohérentes (`birth_from` > `birth_to`) donnent `422`.
- **Pourquoi** : une faute de frappe (`?serach=dup`) renverrait sinon toute la liste sans erreur, ce qui est pire qu'un échec visible. À l'inverse, un formulaire envoie ses champs vides tels quels ; ce n'est pas une erreur.
- **Conséquences** : un client qui ajoute un paramètre non prévu est rejeté ; ajouter un filtre est un ajout compatible.

### D-07 — Recherche insensible à la casse, sensible aux accents

- **Statut** : Choix de conception (limite connue, voir [points ouverts](#points-ouverts))
- **Décision** : `search` est un « contient » insensible à la casse. Pour les patients, chaque mot saisi doit être trouvé dans le `patient_id`, le prénom ou le nom (`jean dup` trouve « Jean Dupont »). Les caractères `%` et `_` sont du texte, pas des jokers SQL. La recherche est **sensible aux accents**.
- **Pourquoi** : la saisie d'un utilisateur ne doit jamais être interprétée comme un motif (`%` renverrait tout) ; rendre la recherche insensible aux accents demande d'activer une extension PostgreSQL (`unaccent`), pas encore décidé.
- **Conséquences** : « andre » ne trouve pas « André » (1 267 résultats contre 1 037 pour « andré » sur les données actuelles). Les filtres exacts (`city`, `jeu`, …) sont insensibles à la casse mais pas aux accents non plus.

### D-08 — Schémas de sortie dédiés, jamais d'entité

- **Statut** : Choix de conception
- **Décision** : chaque route déclare un `response_model` ; on ne renvoie jamais une entité de base de données. Les schémas sont écrits explicitement, un par intention.
- **Pourquoi** : ce qui sort de l'API doit être un choix, pas un effet de bord d'une colonne ajoutée à une table (secrets, hash, relations).
- **Conséquences** : un test garantit que `SyntheticPatientRead` expose **exactement** les colonnes de la table : ajouter une colonne sans l'ajouter au schéma (ou l'inverse) fait échouer la suite.

### D-09 — Patients et patients synthétiques en lecture seule

- **Statut** : Choix de conception
- **Décision** : ces ressources n'ont que des routes `GET`. `POST`, `PUT`, `PATCH` et `DELETE` répondent `405` (testé).
- **Pourquoi** : les données viennent du CSV via le seed ; aucun besoin d'écriture n'a été exprimé, et qui peut écrire des données de santé est une décision à part entière.
- **Conséquences** : créer ou corriger un patient passe par le seed. Une écriture via l'API demandera une décision (qui, avec quelle traçabilité).

---

## Analyse

### D-10 — Le résultat d'analyse est public parce qu'il est synthétique

- **Statut** : Demandée (route sans authentification) ; le chemin `/analysis/result` est un choix par défaut, **à confirmer**
- **Décision** : `GET /analysis/result` ne demande aucune session. C'est la seule exception à [D-02](#d-02--toutes-les-routes-métier-exigent-une-session-une-seule-exception), et elle ne tient que parce que la réponse est synthétique : le schéma impose `synthetic: true` (`Literal[True]`), donc il **ne peut pas représenter** un vrai patient. Le dépôt ne contient pas de modèle : la route sert un cas de démonstration (`SYN-CASE-001`, `generator_version: "demo-v1"`) défini dans les constantes.
- **Pourquoi** : la forme du résultat a été fournie sans authentification, pour la démonstration ; le garde-fou de type empêche que cette ouverture devienne une fuite le jour où le vrai modèle est branché.
- **Conséquences** : les résultats d'un vrai patient devront passer par une route **authentifiée**, avec son propre schéma. Le branchement du modèle se fera dans le service, sans toucher au router.

### D-11 — Types lâches là où le format n'est pas connu

- **Statut** : Choix de conception (provisoire)
- **Décision** : les six listes vides de l'exemple (`factors`, `missing_data`, `assays`, `discordances`, `triggered_rules`, `uncertainties`) sont typées `list[Any]`. Les statuts, phases et catégories (`phase`, `trend`, `review_status`, …) sont des `str`, pas des énumérations.
- **Pourquoi** : l'exemple fourni n'a que des listes vides et une valeur par champ ; en déduire un schéma ou un ensemble fermé de valeurs serait l'inventer (et aucune règle métier ne doit être supposée tant qu'elle n'est pas fournie).
- **Conséquences** : un client ne doit pas supposer que les valeurs listées dans l'exemple sont les seules. Resserrer les types dès qu'un exemple réel avec éléments est disponible.

---

## Patients et patients synthétiques

### D-12 — Endpoint de détail d'un patient

- **Statut** : À confirmer
- **Décision** : en plus de la liste, `GET /patients/{id}` renvoie un patient par son UUID, avec `404 PATIENT_NOT_FOUND` s'il n'existe pas.
- **Pourquoi** : la demande portait sur « 2 endpoints » dont un seul (la liste filtrable) était décrit ; le détail est le complément naturel.
- **Conséquences** : si le second endpoint attendu était autre chose, celui-ci reste utile (il sert aussi de base à [D-15](#d-15--lendpoint-imbriqué-distingue-patient-inconnu-et-liste-vide)) mais ne couvre pas le besoin.

### D-13 — La liaison se fait par `patient_id`, pas par `id`

- **Statut** : Demandée
- **Décision** : `patients.patient_id` (identifiant fonctionnel du CSV, ex. `SYN-0001`) est **unique**. `patients_synthetiques.patient_id` est une clé étrangère vers `patients.patient_id` (`ON DELETE CASCADE`), et non vers `patients.id`. Un patient peut avoir **plusieurs** patients synthétiques : `patient_id` n'est donc pas unique dans `patients_synthetiques`. L'ancienne colonne `code_synthetique` a été supprimée : elle contenait la même valeur.
- **Pourquoi** : c'est l'identifiant lisible et stable de la source ; il évite de dépendre d'un UUID technique pour relier deux tables.
- **Conséquences** : dans l'API, `patient_id` d'un patient synthétique est un **texte** (`SYN-0001`), plus un UUID, et `code_synthetique` n'existe plus : c'est un **changement incompatible**, fait dans la `v1` faute de client connu ([D-01](#d-01--versionnement-par-préfixe-apiv1)). Le CSV ayant une ligne par `patient_id`, c'est aujourd'hui du 1-pour-1 en pratique ; le schéma autorise le 1-pour-plusieurs.

### D-14 — Identités fictives et déterministes

- **Statut** : Choix de conception (contrainte des données)
- **Décision** : le CSV ne contient ni prénom, ni nom, ni ville, ni pays. Le seed les tire de listes fixes (`constants/patients.py`) en partant du `patient_id`, donc de façon **déterministe**. `birth` est nullable : 503 lignes du CSV n'ont pas de date de naissance.
- **Pourquoi** : la table `patients` demandée a ces colonnes ; les inventer au hasard à chaque seed rendrait les données instables.
- **Conséquences** : ces valeurs n'ont aucun sens métier et ne sont pas uniques (deux patients peuvent avoir le même prénom et nom). Ne jamais les présenter comme réelles.

### D-15 — L'endpoint imbriqué distingue patient inconnu et liste vide

- **Statut** : Demandée (l'endpoint) ; la réponse `404` est un choix de conception
- **Décision** : `GET /patients/{id}/synthetic-patients` désigne le patient par son UUID `id`, en déduit son `patient_id` pour la liaison ([D-13](#d-13--la-liaison-se-fait-par-patient_id-pas-par-id)), et répond `404 PATIENT_NOT_FOUND` si le patient n'existe pas, `200` avec une liste vide s'il existe sans patient synthétique. Il n'accepte que le tri et la pagination.
- **Pourquoi** : pour un client, « ce patient n'a rien » et « ce lien est cassé » sont deux situations différentes.
- **Conséquences** : le filtre `GET /synthetic-patients?patient_id=` ne fait pas cette distinction (liste vide dans les deux cas). Le patient est vérifié par le service `patients`, pas par un accès direct à ses tables ([D-18](#d-18--un-contexte-à-part-qui-passe-par-le-service-patients)). Les autres filtres sont refusés (`422`) puisque le patient est dans l'URL.

### D-16 — Les vérités terrain sont exposées, mais non triables

- **Statut** : À confirmer
- **Décision** : les 13 colonnes préfixées par `_` du CSV (`_issue_statut`, `_verite_tgi`, `_verite_p_rejet`, …), qui sont les résultats attendus du générateur, sont renvoyées par l'API avec leur nom d'origine. Elles ne sont ni triables ni filtrables.
- **Pourquoi** : la demande était de reprendre toutes les colonnes du CSV ; Pydantic interdit les champs préfixés par `_`, le schéma les lit donc et les renvoie par **alias**.
- **Conséquences** : un frontend voit la « bonne réponse » à côté des données d'entrée. Si ces données servent à évaluer un modèle à l'aveugle, il faut les retirer du schéma de sortie (une ligne par champ). C'est le premier point ouvert.

### D-17 — Taille de page plafonnée à 100

- **Statut** : À confirmer
- **Décision** : `page_size` vaut 20 par défaut et **100 au maximum** (constante globale), pour toutes les listes.
- **Pourquoi** : la convention du projet exige une borne ; 100 est une valeur raisonnable à défaut d'un besoin connu.
- **Conséquences** : un patient synthétique porte 67 champs : une page de 100 pèse environ **179 Ko**. À baisser si cela pèse sur le réseau ou le rendu.

### D-18 — Un contexte à part qui passe par le service `patients`

- **Statut** : Choix de conception
- **Décision** : les patients synthétiques forment leur propre contexte (`synthetic_patients`), y compris la route imbriquée dont l'URL commence pourtant par `/patients`. Il dépend de `patients` uniquement par son **service** (`get_patient`, `existing_patient_ids`), jamais par son repository, et jamais dans l'autre sens.
- **Pourquoi** : conventions du projet (un dossier par contexte, une seule direction de dépendance : le dépendant connaît le parent).
- **Conséquences** : `Patient` n'a pas de collection `synthetic_records`. Pour retrouver les patients synthétiques d'un patient : la route imbriquée ou `?patient_id=`. La relation `SyntheticPatient.patient` existe mais se charge explicitement (`lazy="raise"`).

### D-19 — Filtres exposés sur les patients synthétiques

- **Statut** : À confirmer
- **Décision** : `GET /synthetic-patients` filtre sur `search` (dans `patient_id`), `patient_id`, `sexe`, `jeu`, `phase`, `statut_parcours` et `organe`, et trie sur dix colonnes. Les autres colonnes (HLA, dates cliniques, vérités terrain) n'ont ni filtre ni tri.
- **Pourquoi** : 65 colonnes ne peuvent pas toutes être des filtres ; ce sont celles qui servent à parcourir la liste.
- **Conséquences** : en ajouter un autre est une ligne de schéma, une ligne de repository et un test, sans changer la version.

### D-20 — Dans les URL, `{id}` est l'UUID, pas le `patient_id`

- **Statut** : Choix de conception
- **Décision** : le paramètre de chemin s'appelle `{id}` (`/patients/{id}`, `/patients/{id}/synthetic-patients`) et contient l'**UUID** du patient. Le `patient_id` fonctionnel ne sert qu'aux filtres et à la liaison.
- **Pourquoi** : une fois [D-13](#d-13--la-liaison-se-fait-par-patient_id-pas-par-id) pris, appeler `{patient_id}` un UUID aurait prêté à confusion avec la colonne `patient_id`.
- **Conséquences** : `/patients/SYN-0001/synthetic-patients` répond `422`. Si les clients préfèrent des URL par identifiant fonctionnel, c'est une route à ajouter (voir [points ouverts](#points-ouverts)).

---

## Données et seed

### D-21 — Seed en deux étapes, rejouable, à ids stables

- **Statut** : Demandée (étapes et dépendance) ; le reste est un choix de conception
- **Décision** : `uv run python -m app.seed [--csv CHEMIN] [--only patients|synthetic] [--reset]` remplit d'abord `patients`, puis `patients_synthetiques` **à partir des patients** : pour chaque ligne du CSV, le service `patients` dit si son `patient_id` existe ; sinon la ligne est comptée « sans patient » et non insérée. L'`id` de chaque ligne est dérivé de son `patient_id` (UUID v5) : relancer le seed ne crée aucun doublon (`ON CONFLICT DO NOTHING`) et retrouve les **mêmes `id`**. Une seule transaction (tout ou rien), insertion par lots de 400 lignes.
- **Pourquoi** : les patients synthétiques ne peuvent pas exister sans leur patient (clé étrangère). Les lots de 400 respectent la limite de 32 767 paramètres par requête d'asyncpg (400 × 67 colonnes).
- **Conséquences** : les URL `/patients/{id}` restent valables après un nouveau seed ou un `--reset` (empreinte des `id` identique avant/après, vérifiée). Si le CSV avait plusieurs lignes pour un même `patient_id`, seule la première serait insérée, les autres comptées « déjà présentes ».

### D-22 — Pas de migrations, reset des tables et détection de schéma obsolète

- **Statut** : Choix de conception (à revoir)
- **Décision** : les tables sont créées par `create_all` (au démarrage du backend ou par le seed), qui **ne modifie pas** une table existante. Le seed compare les colonnes réelles à celles des entités et **refuse de continuer** si elles diffèrent (« schéma obsolète »). `--reset` supprime alors `patients` et `patients_synthetiques` et les recrée. Les tables des utilisateurs et des sessions ne sont jamais touchées.
- **Pourquoi** : aucun outil de migration n'est en place, et ces deux tables se régénèrent intégralement depuis le CSV.
- **Conséquences** : le backend ne vérifie pas le schéma au démarrage : après une modification d'entité, il faut relancer le seed avec `--reset`, sinon les endpoints concernés échouent en `500`. Ce n'est acceptable que tant que les données sont régénérables ; l'arrivée de données saisies par des utilisateurs imposera un vrai outil de migration.

---

## Signature

### D-23 — Signature clinique des cas simples

- **Statut** : Demandée (section « À signer », signature enregistrée côté serveur) ; les seuils sont un choix de conception, **à confirmer**
- **Décision** : `GET /signatures/queue` propose au plus 5 cas simples : profil sérique `A`, au plus 3 événements d'historique, pas encore signés. `POST /signatures` enregistre la signature dans `patient_signatures` : `patient_id` unique, `signed_by` (l'utilisateur de la session), `signed_at` (horodatage serveur). Tout utilisateur connecté peut signer ; une signature ne s'annule pas. Les patients restent en lecture seule ([D-09](#d-09--patients-et-patients-synthétiques-en-lecture-seule)) : la signature est une ressource à part.
- **Pourquoi** : l'algorithme traite seul les cas stables ; le soignant les vérifie et les valide. La traçabilité demandée par D-09 pour toute écriture tient dans `signed_by` et `signed_at`.
- **Conséquences** : `patient_id` n'est pas une clé étrangère : `seed --reset` recrée `patients` sans toucher aux signatures ([D-22](#d-22--pas-de-migrations-reset-des-tables-et-détection-de-schéma-obsolète)), et les `patient_id` sont stables d'un seed à l'autre. Les données actuelles n'ont d'historique que pour dix patients : la file contient en pratique les patients de profil `A` sans historique. Les indicateurs de la page (cas traités hier, cette semaine) sont fictifs côté frontend.

---

## Points ouverts

À trancher par l'équipe ; chacun renvoie à la décision concernée.

1. **Exposer les vérités terrain au frontend ?** ([D-16](#d-16--les-vérités-terrain-sont-exposées-mais-non-triables)) : à retirer du schéma si le frontend ne doit pas voir la « bonne réponse ».
2. **Recherche insensible aux accents ?** ([D-07](#d-07--recherche-insensible-à-la-casse-sensible-aux-accents)) : demande d'activer l'extension PostgreSQL `unaccent`.
3. **Taille maximale de page** ([D-17](#d-17--taille-de-page-plafonnée-à-100)) : 100 est-il adapté (179 Ko pour une page de patients synthétiques) ?
4. **Routes manquantes** : détail d'un patient synthétique (`GET /synthetic-patients/{id}`) ; accès aux patients par `patient_id` dans l'URL ([D-20](#d-20--dans-les-url-id-est-luuid-pas-le-patient_id)). Non faites : pas demandées.
5. **Résultats réels du modèle** ([D-10](#d-10--le-résultat-danalyse-est-public-parce-quil-est-synthétique), [D-11](#d-11--types-lâches-là-où-le-format-nest-pas-connu)) : source des résultats (Lymfip ou autre), format, qui les valide. Il faudra une route authentifiée et resserrer les types.
6. **Écriture** ([D-09](#d-09--patients-et-patients-synthétiques-en-lecture-seule)) : qui peut créer ou modifier des patients, avec quelle traçabilité.
7. **Geler la `v1`** ([D-01](#d-01--versionnement-par-préfixe-apiv1)) : à partir du moment où le frontend consomme l'API, tout changement incompatible demande une `v2`.
8. **Déjà identifiés dans `CLAUDE.md`, toujours non faits** : limitation de débit, réinitialisation de mot de passe, vérification d'email, révocation des sessions au changement de mot de passe, outil de migration ([D-22](#d-22--pas-de-migrations-reset-des-tables-et-détection-de-schéma-obsolète)).
