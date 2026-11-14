import uuid
from enum import StrEnum
from typing import Final

from app.constants.seed import CSV_COLUMN_PATIENT_ID

# Routes
SYNTHETIC_PATIENTS_ROUTER_PREFIX: Final = "/synthetic-patients"
SYNTHETIC_PATIENTS_ROUTER_TAG: Final = "synthetic-patients"

# Table `patients_synthetiques`
SYNTHETIC_PATIENTS_TABLE_NAME: Final = "patients_synthetiques"
SYNTHETIC_CODE_COLUMN: Final = "code_synthetique"
SYNTHETIC_CODE_MAX_LENGTH: Final = 50
# Colonnes catégorielles (statut, type, libellé) : texte court.
CATEGORY_MAX_LENGTH: Final = 100


class SyntheticPatientSortField(StrEnum):
    """Liste blanche des colonnes sur lesquelles le client peut trier."""

    CODE = "code_synthetique"
    DATE_REFERENCE = "date_reference"
    DATE_NAISSANCE = "date_naissance"
    AGE = "age"
    JEU = "jeu"
    PHASE = "phase"
    STATUT_PARCOURS = "statut_parcours"
    STATUT_DATE = "statut_date"
    ORGANE = "organe"
    CREATED_AT = "created_at"


DEFAULT_SYNTHETIC_PATIENT_SORT_FIELD: Final = SyntheticPatientSortField.CODE

# Seed ---------------------------------------------------------------------------------------
# La table reprend toutes les colonnes du CSV, avec le même nom en minuscules (`hla_A` → `hla_a`),
# sauf une : la colonne CSV `patient_id` (« SYN-0001 ») devient `code_synthetique`, car
# `patient_id` est la clé étrangère vers `patients`.
CSV_COLUMN_ALIASES: Final = {CSV_COLUMN_PATIENT_ID: SYNTHETIC_CODE_COLUMN}
# Colonnes de la table qui ne viennent pas du CSV.
SYNTHETIC_NON_CSV_COLUMNS: Final = frozenset({"id", "patient_id", "created_at"})

# L'id d'un patient synthétique est dérivé de son code (UUID v5) : relancer le seed retrouve les
# mêmes id, donc ne crée pas de doublons.
SEED_SYNTHETIC_UUID_NAMESPACE: Final = uuid.UUID("b3d7e1f0-5a2c-4e68-9f14-7c8a0d2b6e35")
