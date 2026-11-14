import uuid
from enum import StrEnum
from typing import Final

from app.constants.patients import PATIENTS_ROUTER_PREFIX

# Routes
SYNTHETIC_PATIENTS_ROUTER_PREFIX: Final = "/synthetic-patients"
SYNTHETIC_PATIENTS_ROUTER_TAG: Final = "synthetic-patients"
# Route imbriquée : les patients synthétiques d'un patient, /patients/{id}/synthetic-patients.
# `{id}` est l'UUID du patient (son `id`), pas son `patient_id` fonctionnel (« SYN-0001 »).
PATIENT_SYNTHETIC_PATIENTS_ROUTER_PREFIX: Final = (
    f"{PATIENTS_ROUTER_PREFIX}/{{id}}{SYNTHETIC_PATIENTS_ROUTER_PREFIX}"
)

# Table `patients_synthetiques`
SYNTHETIC_PATIENTS_TABLE_NAME: Final = "patients_synthetiques"
# Colonnes catégorielles (statut, type, libellé) : texte court.
CATEGORY_MAX_LENGTH: Final = 100


class SyntheticPatientSortField(StrEnum):
    """Liste blanche des colonnes sur lesquelles le client peut trier."""

    PATIENT_ID = "patient_id"
    DATE_REFERENCE = "date_reference"
    DATE_NAISSANCE = "date_naissance"
    AGE = "age"
    JEU = "jeu"
    PHASE = "phase"
    STATUT_PARCOURS = "statut_parcours"
    STATUT_DATE = "statut_date"
    ORGANE = "organe"
    CREATED_AT = "created_at"


DEFAULT_SYNTHETIC_PATIENT_SORT_FIELD: Final = SyntheticPatientSortField.PATIENT_ID

# Seed ---------------------------------------------------------------------------------------
# La table reprend toutes les colonnes du CSV, avec le même nom en minuscules (`hla_A` → `hla_a`).
# Colonnes de la table qui ne viennent pas du CSV :
SYNTHETIC_NON_CSV_COLUMNS: Final = frozenset({"id", "created_at"})

# L'id d'un patient synthétique est dérivé de son `patient_id` (UUID v5) : relancer le seed
# retrouve les mêmes id, donc ne crée pas de doublons.
SEED_SYNTHETIC_UUID_NAMESPACE: Final = uuid.UUID("b3d7e1f0-5a2c-4e68-9f14-7c8a0d2b6e35")
