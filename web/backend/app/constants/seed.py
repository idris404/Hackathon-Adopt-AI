from enum import StrEnum
from pathlib import Path
from typing import Final

# seed.py → constants → app → backend → web → racine du dépôt (parents[4])
DEFAULT_PATIENTS_CSV_PATH: Final = (
    Path(__file__).resolve().parents[4] / "data-model" / "data" / "patients_synthetiques_v3.csv"
)
DEFAULT_SERUM_HISTORY_CSV_PATH: Final = (
    Path(__file__).resolve().parents[4] / "data-model" / "data" / "serum_test_history.csv"
)

# Ligne 1 du fichier = en-tête : les données commencent à la ligne 2.
FIRST_CSV_DATA_LINE: Final = 2

# asyncpg refuse plus de 32 767 paramètres par requête. Un lot = (lignes × colonnes) paramètres :
# la table patients_synthetiques (~70 colonnes) impose donc moins de ~460 lignes par lot.
ASYNCPG_MAX_QUERY_ARGUMENTS: Final = 32767
SEED_BATCH_SIZE: Final = 400

# Colonne du CSV qui identifie une ligne ; les deux contextes (patients, patients synthétiques) la lisent.
CSV_COLUMN_PATIENT_ID: Final = "patient_id"


class SeedStage(StrEnum):
    """Étapes du seed, dans l'ordre : synthétiques, tests sériques et historique partent des patients."""

    PATIENTS = "patients"
    SYNTHETIC_PATIENTS = "synthetic"
    SERUM_TESTS = "serum"
    PATIENT_HISTORY = "history"
