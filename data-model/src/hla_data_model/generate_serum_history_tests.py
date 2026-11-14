#!/usr/bin/env python3
"""Historique longitudinal synthétique de tests sériques.

Les résultats produits servent à des expérimentations techniques et à des
démonstrations. Ce ne sont pas des mesures biologiques cliniques.

Fichier source observé
----------------------
``2_patient_greffé_synthetiques_v3.csv`` ne contient que trois colonnes :

- ``patient_id``
- ``statut_parcours`` (tous les patients sont « Greffé »)
- ``date_greffe_actuelle`` au format ISO ``AAAA-MM-JJ``

Aucune valeur de B12, B13, DR53, DR51 ou DQ10 n'est présente. La date de
greffe utilisée est donc ``date_greffe_actuelle``, recopiée en sortie dans
``graft_date``. Les cinq antigènes sont simulés de bout en bout.

Règles de calendrier
---------------------
Un test est créé pour chaque année civile entre l'année de greffe et
l'année de ``END_DATE``, incluses. La date est tirée dans cette année, puis
bornée : pas avant la greffe pour la première année, pas après ``END_DATE``
pour la dernière. Un patient dont la greffe est postérieure à ``END_DATE``
ne reçoit aucun test.
"""

from __future__ import annotations

import math
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------------
# Paramètres de génération. Modifier ces constantes, pas le reste du script.
# ---------------------------------------------------------------------------

PATIENT_LIMIT = 1000
END_DATE = "2026-11-14"
RANDOM_SEED = 42
POSITIVITY_THRESHOLD = 500

# Parts des trois profils. La somme doit valoir 100.
# Défaut de démonstration, sans signification clinique.
PROFILE_DISTRIBUTION = {
    "A": 50,  # stabilité complète : les cinq antigènes restent fixes
    "B": 30,  # fluctuations partielles : 1 ou 2 antigènes évoluent
    "C": 20,  # très fluctuant : 3 antigènes sautent, 2 restent fixes
}

# Nombre d'antigènes autorisés à changer, selon le profil.
FLUCTUATING_ANTIGEN_COUNTS = {
    "A": (0, 0),
    "B": (1, 2),
    "C": (3, 3),
}

ANTIGENS = ("B12", "B13", "DR53", "DR51", "DQ10")

# Échelle synthétique de type MFI. Le statut positif/négatif est indépendant
# du profil : seule la comparaison au seuil compte.
MFI_MIN = 0
MFI_MAX = 15_000
P_INITIAL_POSITIVE = 0.40

# Pas d'une année sur l'autre pour un antigène du profil B.
RELATIVE_STEP = (0.10, 0.40)
ABSOLUTE_STEP_MIN = 80
ABSOLUTE_STEP_MAX = 1_200

# Profil C : chaque année est retirée sur une échelle large, sans dérive.
# Un antigène instable passe de 0 ou d'une valeur négative à un positif
# élevé, pour que l'écart d'une année à l'autre soit net.
C_ZERO_PROBABILITY = 0.15
C_NEGATIVE_PROBABILITY = 0.35
C_HIGH_MAX = 12_000
C_MIN_RANGE = 3_000

SOURCE_CSV = Path(__file__).resolve().parent / "2_patient_greffé_synthetiques_v3.csv"
OUTPUT_CSV = Path(__file__).resolve().parent / "historique_tests_seriques.csv"

SOURCE_ID_COLUMN = "patient_id"
SOURCE_GRAFT_COLUMN = "date_greffe_actuelle"
GRAFT_DATE_COLUMN = "graft_date"
TEST_DATE_COLUMN = "test_date"
PROFILE_COLUMN = "profile"


def colonne_output(antigene: str) -> str:
    """Colonne binaire : 1 si l'antigène atteint le seuil, 0 sinon."""
    return f"{antigene}_output"


OUTPUT_COLUMNS = (
    "patient_id",
    GRAFT_DATE_COLUMN,
    TEST_DATE_COLUMN,
    *(colonne for antigene in ANTIGENS for colonne in (antigene, colonne_output(antigene))),
    PROFILE_COLUMN,
)

PROFILE_LABELS = {
    "A": "full constancy",
    "B": "partial fluctuations",
    "C": "highly fluctuating",
}


def valider_configuration() -> date:
    """Contrôle les constantes avant tout tirage aléatoire."""
    if PATIENT_LIMIT < 0:
        raise ValueError("PATIENT_LIMIT doit être positif ou nul.")
    if not 0 <= P_INITIAL_POSITIVE <= 1:
        raise ValueError("P_INITIAL_POSITIVE doit être compris entre 0 et 1.")
    if POSITIVITY_THRESHOLD <= MFI_MIN or POSITIVITY_THRESHOLD > MFI_MAX:
        raise ValueError("POSITIVITY_THRESHOLD doit être dans l'intervalle ]MFI_MIN, MFI_MAX].")
    if ABSOLUTE_STEP_MIN <= 0 or ABSOLUTE_STEP_MAX < ABSOLUTE_STEP_MIN:
        raise ValueError("Les pas absolus doivent être strictement positifs et ordonnés.")
    if not 0 < RELATIVE_STEP[0] <= RELATIVE_STEP[1]:
        raise ValueError("RELATIVE_STEP doit être un intervalle relatif strictement positif.")
    if set(PROFILE_DISTRIBUTION) != {"A", "B", "C"}:
        raise ValueError("PROFILE_DISTRIBUTION doit contenir exactement les profils A, B et C.")
    total = sum(PROFILE_DISTRIBUTION.values())
    if abs(total - 100) > 1e-6:
        raise ValueError(f"La somme des profils doit valoir 100 %, obtenu {total}.")
    if any(part < 0 for part in PROFILE_DISTRIBUTION.values()):
        raise ValueError("Les pourcentages de profils ne peuvent pas être négatifs.")
    for profil, (bas, haut) in FLUCTUATING_ANTIGEN_COUNTS.items():
        if not 0 <= bas <= haut <= len(ANTIGENS):
            raise ValueError(f"Nombre d'antigènes fluctuants invalide pour le profil {profil}.")
    if FLUCTUATING_ANTIGEN_COUNTS["A"] != (0, 0):
        raise ValueError("Le profil A ne doit faire fluctuer aucun antigène.")
    if FLUCTUATING_ANTIGEN_COUNTS["B"][1] >= len(ANTIGENS):
        raise ValueError("Le profil B doit conserver au moins un antigène constant.")
    if FLUCTUATING_ANTIGEN_COUNTS["C"][1] >= len(ANTIGENS):
        raise ValueError("Le profil C doit conserver au moins un antigène constant.")
    if not (0 <= C_ZERO_PROBABILITY and C_ZERO_PROBABILITY + C_NEGATIVE_PROBABILITY <= 1):
        raise ValueError("Les probabilités du profil C doivent tenir dans [0, 1].")
    if POSITIVITY_THRESHOLD >= C_HIGH_MAX or C_HIGH_MAX > MFI_MAX:
        raise ValueError("C_HIGH_MAX doit être au-dessus du seuil et au plus égal à MFI_MAX.")
    if C_MIN_RANGE <= 0 or C_MIN_RANGE > C_HIGH_MAX:
        raise ValueError("C_MIN_RANGE doit être compris entre 1 et C_HIGH_MAX.")
    if OUTPUT_CSV.resolve() == SOURCE_CSV.resolve():
        raise ValueError("Le fichier de sortie ne peut pas être le fichier source.")
    return datetime.strptime(END_DATE, "%Y-%m-%d").date()


def comptes_profils(nombre_patients: int) -> dict[str, int]:
    """Convertit les pourcentages en effectifs entiers (méthode du plus fort reste)."""
    bruts = {profil: nombre_patients * part / 100 for profil, part in PROFILE_DISTRIBUTION.items()}
    comptes = {profil: math.floor(valeur) for profil, valeur in bruts.items()}
    reste = nombre_patients - sum(comptes.values())
    ordre = sorted(
        bruts,
        key=lambda profil: (bruts[profil] - comptes[profil], profil),
        reverse=True,
    )
    for profil in ordre[:reste]:
        comptes[profil] += 1
    return comptes


def attribuer_profils(nombre_patients: int, rng: random.Random) -> list[str]:
    comptes = comptes_profils(nombre_patients)
    profils = [profil for profil, effectif in comptes.items() for _ in range(effectif)]
    rng.shuffle(profils)
    return profils


def fenetres_annuelles(greffe: date, fin_suivi: date) -> list[tuple[date, date]]:
    """Une fenêtre inclusive par année civile, coupée par la greffe et la date limite."""
    if greffe > fin_suivi:
        return []
    fenetres = []
    for annee in range(greffe.year, fin_suivi.year + 1):
        debut = date(annee, 1, 1)
        fin = date(annee, 12, 31)
        if annee == greffe.year:
            debut = greffe
        if annee == fin_suivi.year:
            fin = min(fin, fin_suivi)
        if debut <= fin:
            fenetres.append((debut, fin))
    return fenetres


def date_aleatoire(debut: date, fin: date, rng: random.Random) -> date:
    return debut + timedelta(days=rng.randrange((fin - debut).days + 1))


def clamper(valeur: int) -> int:
    return max(MFI_MIN, min(MFI_MAX, int(valeur)))


def valeur_initiale(rng: random.Random) -> int:
    """Tire un niveau de départ positif ou négatif, indépendamment du profil."""
    if rng.random() < P_INITIAL_POSITIVE:
        exposant = rng.uniform(math.log(POSITIVITY_THRESHOLD), math.log(MFI_MAX))
        return clamper(max(POSITIVITY_THRESHOLD, int(round(math.exp(exposant)))))

    plafond = POSITIVITY_THRESHOLD - 1
    milieu = MFI_MIN + (plafond - MFI_MIN) // 2
    if rng.random() < 0.5:
        return rng.randint(MFI_MIN, milieu)
    return rng.randint(milieu, plafond)


def amplitude(valeur: int, rng: random.Random) -> int:
    """Pas annuel visible. Le plancher est lui-même tiré, pour éviter un pas fixe."""
    relatif = int(abs(valeur) * rng.uniform(*RELATIVE_STEP))
    plancher = rng.randint(ABSOLUTE_STEP_MIN, ABSOLUTE_STEP_MIN * 3)
    return min(ABSOLUTE_STEP_MAX, max(plancher, relatif))


def pas_suivant(valeur: int, rng: random.Random) -> int:
    """Avance ou recule d'un pas visible, en restant dans l'échelle synthétique."""
    signe = rng.choice((-1, 1))
    pas = amplitude(valeur, rng)
    suivant = clamper(valeur + signe * pas)
    if suivant == valeur:
        suivant = clamper(valeur - signe * pas)
    if suivant == valeur:
        suivant = clamper(valeur + ABSOLUTE_STEP_MIN if valeur < MFI_MAX else valeur - ABSOLUTE_STEP_MIN)
    return suivant


def valeur_differente(valeur: int, rng: random.Random) -> int:
    if valeur <= MFI_MIN:
        return clamper(valeur + ABSOLUTE_STEP_MIN)
    if valeur >= MFI_MAX:
        return clamper(valeur - ABSOLUTE_STEP_MIN)
    return clamper(valeur + rng.choice((-1, 1)) * ABSOLUTE_STEP_MIN)


def generer_serie(
    baseline: int,
    nombre_tests: int,
    rng: random.Random,
    *,
    fluctue: bool,
) -> list[int]:
    """Série annuelle d'un antigène stable ou en dérive lente.

    Un antigène constant répète exactement sa valeur initiale. Un antigène
    du profil B change par petits pas, au moins une fois dès qu'il existe
    deux tests.
    """
    if not fluctue or nombre_tests == 1:
        return [baseline] * nombre_tests

    valeurs = [baseline]
    courant = baseline
    for _ in range(nombre_tests - 1):
        courant = pas_suivant(courant, rng)
        valeurs.append(courant)

    if len(set(valeurs)) == 1:
        valeurs[-1] = valeur_differente(valeurs[-2], rng)
    if fluctue and len(set(valeurs)) == 1:
        raise RuntimeError("Un antigène fluctuant est resté constant.")
    return valeurs


def valeur_tres_fluctuante(rng: random.Random) -> int:
    """Une mesure isolée du profil C : zéro, négatif, ou positif sur une échelle large."""
    tirage = rng.random()
    if tirage < C_ZERO_PROBABILITY:
        return 0
    if tirage < C_ZERO_PROBABILITY + C_NEGATIVE_PROBABILITY:
        return rng.randint(1, POSITIVITY_THRESHOLD - 1)
    exposant = rng.uniform(math.log(POSITIVITY_THRESHOLD), math.log(C_HIGH_MAX))
    return min(C_HIGH_MAX, max(POSITIVITY_THRESHOLD, int(round(math.exp(exposant)))))


def serie_assez_variable(valeurs: list[int]) -> bool:
    """L'écart est large et, dès trois tests, le seuil est franchi dans les deux sens."""
    if len(set(valeurs)) <= 1 or max(valeurs) - min(valeurs) < C_MIN_RANGE:
        return False
    if len(valeurs) < 3:
        return True
    return any(valeur < POSITIVITY_THRESHOLD for valeur in valeurs) and any(
        valeur >= POSITIVITY_THRESHOLD for valeur in valeurs
    )


def serie_tres_fluctuante(nombre_tests: int, rng: random.Random) -> list[int]:
    """Retire chaque année indépendamment, sur toute l'échelle du profil C.

    Contrairement au profil B, il n'y a pas de petit pas d'une année sur
    l'autre : la valeur peut passer de 0 à plusieurs milliers.
    """
    if nombre_tests == 1:
        return [valeur_tres_fluctuante(rng)]

    valeurs = [valeur_tres_fluctuante(rng) for _ in range(nombre_tests)]
    for _ in range(40):
        if serie_assez_variable(valeurs):
            return valeurs
        valeurs = [valeur_tres_fluctuante(rng) for _ in range(nombre_tests)]
    if not serie_assez_variable(valeurs):
        valeurs[0] = 0
        valeurs[-1] = C_HIGH_MAX
    return valeurs


def antigene_fluctuants(profil: str, rng: random.Random) -> set[str]:
    bas, haut = FLUCTUATING_ANTIGEN_COUNTS[profil]
    if haut == 0:
        return set()
    return set(rng.sample(ANTIGENS, rng.randint(bas, haut)))


def charger_patients() -> pd.DataFrame:
    if not SOURCE_CSV.is_file():
        raise FileNotFoundError(f"Fichier source introuvable : {SOURCE_CSV}")
    patients = pd.read_csv(SOURCE_CSV, dtype={SOURCE_ID_COLUMN: "string"})
    colonnes_manquantes = {SOURCE_ID_COLUMN, SOURCE_GRAFT_COLUMN} - set(patients.columns)
    if colonnes_manquantes:
        raise ValueError(f"Colonnes absentes du fichier source : {sorted(colonnes_manquantes)}")
    patients[SOURCE_GRAFT_COLUMN] = pd.to_datetime(
        patients[SOURCE_GRAFT_COLUMN],
        format="%Y-%m-%d",
        errors="coerce",
    )
    selection = patients.head(PATIENT_LIMIT).copy()
    invalides = selection[SOURCE_ID_COLUMN].isna() | selection[SOURCE_GRAFT_COLUMN].isna()
    if invalides.any():
        lignes = selection.index[invalides].tolist()
        raise ValueError(f"Identifiant ou date de greffe manquant aux lignes source {lignes}.")
    if selection[SOURCE_ID_COLUMN].duplicated().any():
        raise ValueError("La sélection contient des patient_id en double.")
    return selection


def generer_historique(patients: pd.DataFrame, fin_suivi: date, rng: random.Random) -> pd.DataFrame:
    """Construit une ligne par patient et par année de suivi.

    L'ordre de tirage est fixe : profils, puis patients dans l'ordre du fichier,
    puis dates, antigènes fluctuants et séries dans l'ordre de ``ANTIGENS``.
    """
    profils = attribuer_profils(len(patients), rng)
    lignes: list[dict[str, object]] = []

    for profil, patient in zip(profils, patients.itertuples(index=False)):
        greffe = getattr(patient, SOURCE_GRAFT_COLUMN).date()
        fenetres = fenetres_annuelles(greffe, fin_suivi)
        if not fenetres:
            continue

        dates = [date_aleatoire(debut, fin, rng) for debut, fin in fenetres]
        fluctuants = antigene_fluctuants(profil, rng)
        series = {}
        for antigene in ANTIGENS:
            if profil == "C" and antigene in fluctuants:
                series[antigene] = serie_tres_fluctuante(len(dates), rng)
            else:
                series[antigene] = generer_serie(
                    valeur_initiale(rng),
                    len(dates),
                    rng,
                    fluctue=antigene in fluctuants,
                )

        for index, jour in enumerate(dates):
            ligne = {
                "patient_id": str(getattr(patient, SOURCE_ID_COLUMN)),
                GRAFT_DATE_COLUMN: greffe.isoformat(),
                TEST_DATE_COLUMN: jour.isoformat(),
                PROFILE_COLUMN: profil,
            }
            for antigene in ANTIGENS:
                valeur = series[antigene][index]
                ligne[antigene] = valeur
                # 1 au seuil ou au-dessus, 0 en dessous. Indépendant du profil.
                ligne[colonne_output(antigene)] = int(valeur >= POSITIVITY_THRESHOLD)
            lignes.append(ligne)

    historique = pd.DataFrame(lignes, columns=OUTPUT_COLUMNS)
    if not historique.empty:
        for antigene in ANTIGENS:
            historique[antigene] = historique[antigene].astype(int)
            historique[colonne_output(antigene)] = historique[colonne_output(antigene)].astype(int)
    return historique


def verifier(historique: pd.DataFrame, patients: pd.DataFrame, fin_suivi: date) -> dict[str, int]:
    """Recontrôle le CSV produit, sans refaire confiance à la génération."""
    erreurs: list[str] = []
    if list(historique.columns) != list(OUTPUT_COLUMNS):
        erreurs.append("Les colonnes de sortie ne respectent pas le format demandé.")

    greffes = pd.to_datetime(historique[GRAFT_DATE_COLUMN], format="%Y-%m-%d")
    tests = pd.to_datetime(historique[TEST_DATE_COLUMN], format="%Y-%m-%d")
    fin = pd.Timestamp(fin_suivi)

    tests_avant_greffe = int((tests < greffes).sum())
    tests_apres_limite = int((tests > fin).sum())
    if tests_avant_greffe:
        erreurs.append(f"{tests_avant_greffe} test(s) précèdent la date de greffe.")
    if tests_apres_limite:
        erreurs.append(f"{tests_apres_limite} test(s) dépassent le {fin_suivi.isoformat()}.")

    annees = tests.dt.year
    doublons = int(historique.assign(annee=annees).duplicated(["patient_id", "annee"]).sum())
    if doublons:
        erreurs.append(f"{doublons} doublon(s) patient-année.")

    hors_echelle = 0
    for antigene in ANTIGENS:
        valeurs = historique[antigene]
        hors_echelle += int(((valeurs < MFI_MIN) | (valeurs > MFI_MAX)).sum())
        if ((valeurs >= POSITIVITY_THRESHOLD).sum() == 0) or ((valeurs < POSITIVITY_THRESHOLD).sum() == 0):
            erreurs.append(f"{antigene} ne contient pas à la fois des résultats positifs et négatifs.")
        attendu = (valeurs >= POSITIVITY_THRESHOLD).astype(int)
        sortie = historique[colonne_output(antigene)]
        if not sortie.isin([0, 1]).all() or not sortie.to_numpy().tolist() == attendu.to_numpy().tolist():
            erreurs.append(f"{colonne_output(antigene)} ne correspond pas au seuil de {POSITIVITY_THRESHOLD}.")
    if hors_echelle:
        erreurs.append(f"{hors_echelle} valeur(s) hors de l'échelle [{MFI_MIN}, {MFI_MAX}].")

    profils_par_patient = historique.groupby("patient_id", sort=False)[PROFILE_COLUMN].nunique()
    if (profils_par_patient != 1).any():
        erreurs.append("Un patient porte plusieurs profils.")

    attendus = comptes_profils(len(patients))
    observes = (
        historique.drop_duplicates("patient_id")[PROFILE_COLUMN]
        .value_counts()
        .reindex(PROFILE_DISTRIBUTION, fill_value=0)
        .astype(int)
        .to_dict()
    )
    patients_sans_test = 0
    for _, patient in patients.iterrows():
        greffe = patient[SOURCE_GRAFT_COLUMN].date()
        if greffe > fin_suivi:
            patients_sans_test += 1
    patients_traites = int(historique["patient_id"].nunique())
    if patients_traites + patients_sans_test != len(patients):
        erreurs.append("Le nombre de patients traités ne correspond pas à la sélection.")
    # Un patient greffé après la date limite a un profil, mais aucune ligne.
    # Tant qu'aucun patient n'est dans ce cas, les effectifs doivent être exacts.
    if patients_sans_test == 0 and observes != attendus:
        erreurs.append(f"Répartition observée {observes}, attendue {attendus}.")

    suivi_trop_court = 0
    for patient_id, groupe in historique.groupby("patient_id", sort=False):
        groupe = groupe.sort_values(TEST_DATE_COLUMN)
        greffe = pd.Timestamp(groupe[GRAFT_DATE_COLUMN].iloc[0])
        annees_observees = set(pd.to_datetime(groupe[TEST_DATE_COLUMN]).dt.year)
        annees_attendues = set(range(greffe.year, fin_suivi.year + 1))
        if annees_observees != annees_attendues:
            erreurs.append(f"{patient_id} n'a pas exactement un test par année de suivi.")
            break
        profil = groupe[PROFILE_COLUMN].iloc[0]
        nombre_tests = len(groupe)
        if nombre_tests < 2:
            suivi_trop_court += 1
            continue
        variables = [antigene for antigene in ANTIGENS if groupe[antigene].nunique() > 1]
        bas, haut = FLUCTUATING_ANTIGEN_COUNTS[profil]
        if not bas <= len(variables) <= haut:
            erreurs.append(
                f"{patient_id} ({profil}) fait varier {len(variables)} antigène(s), attendu {bas}-{haut}."
            )
            break
        if profil == "C":
            for antigene in variables:
                valeurs = [int(valeur) for valeur in groupe[antigene].tolist()]
                if max(valeurs) > C_HIGH_MAX or not serie_assez_variable(valeurs):
                    erreurs.append(f"{patient_id} : {antigene} ne suit pas le profil très fluctuant.")
                    break

    if erreurs:
        details = "\n".join(f"- {erreur}" for erreur in erreurs)
        raise RuntimeError(f"Contraintes non respectées :\n{details}")

    return {
        "tests_avant_greffe": tests_avant_greffe,
        "tests_apres_limite": tests_apres_limite,
        "doublons_patient_annee": doublons,
        "patients_sans_test": patients_sans_test,
        "suivi_trop_court": suivi_trop_court,
    }


def afficher_resume(
    patients: pd.DataFrame,
    historique: pd.DataFrame,
    controles: dict[str, int],
    source_total: int,
) -> None:
    traites = int(historique["patient_id"].nunique())
    tests = len(historique)
    moyenne = tests / traites if traites else 0
    profils = (
        historique.drop_duplicates("patient_id")[PROFILE_COLUMN].value_counts().reindex(["A", "B", "C"], fill_value=0)
    )

    print("Historique synthétique de tests sériques")
    print("Ces valeurs sont simulées pour une démonstration technique.")
    print("Elles ne constituent pas des résultats biologiques cliniques.")
    print()
    print(f"Patients dans le fichier source : {source_total}")
    print(f"Patients sélectionnés : {len(patients)}")
    print(f"Patients traités : {traites}")
    if controles["patients_sans_test"]:
        print(f"Patients sans test (greffe après {END_DATE}) : {controles['patients_sans_test']}")
    print(f"Tests générés : {tests}")
    print(f"Nombre moyen de tests par patient : {moyenne:.2f}")
    print()
    print("Répartition des patients par profil :")
    for profil, effectif in profils.items():
        part = 100 * effectif / traites if traites else 0
        print(f"  {profil} — {PROFILE_LABELS[profil]} : {int(effectif)} ({part:.1f} %)")
    if controles["suivi_trop_court"]:
        print(
            f"Patients avec un seul test, profil non observable dans le temps : "
            f"{controles['suivi_trop_court']}"
        )
    print()
    print(f"Résultats par antigène (positif si valeur >= {POSITIVITY_THRESHOLD}) :")
    for antigene in ANTIGENS:
        positifs = int((historique[antigene] >= POSITIVITY_THRESHOLD).sum())
        negatifs = int((historique[antigene] < POSITIVITY_THRESHOLD).sum())
        print(f"  {antigene} : {positifs} positifs, {negatifs} négatifs")
    print()
    print("Contraintes chronologiques : respectées")
    print(f"  tests avant la date de greffe : {controles['tests_avant_greffe']}")
    print(f"  tests après le {END_DATE} : {controles['tests_apres_limite']}")
    print(f"  doublons pour un même patient et une même année : {controles['doublons_patient_annee']}")
    print("Cohérence temporelle des profils : respectée")
    print(f"Fichier écrit : {OUTPUT_CSV}")


def main() -> None:
    fin_suivi = valider_configuration()
    source = pd.read_csv(SOURCE_CSV, usecols=[SOURCE_ID_COLUMN])
    patients = charger_patients()
    # Un seul flux, consommé dans l'ordre documenté par generer_historique.
    rng = random.Random(RANDOM_SEED)
    historique = generer_historique(patients, fin_suivi, rng)
    controles = verifier(historique, patients, fin_suivi)
    historique.to_csv(OUTPUT_CSV, index=False)
    afficher_resume(patients, historique, controles, source_total=len(source))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        sys.exit(1)
