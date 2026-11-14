import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

# Table `serum_tests` : une ligne de `data-model/data/serum_test_history.csv`.
SERUM_TESTS_TABLE_NAME: Final = "serum_tests"
PROFILE_MAX_LENGTH: Final = 16

# L'id d'un test est déduit du couple (`patient_id`, `test_date`) : relancer le seed
# retrouve la même ligne et ne crée pas de doublon.
SEED_SERUM_UUID_NAMESPACE: Final = uuid.UUID("c3a91e47-6b20-4f58-9d14-8e2a7c0b5f61")

# Colonnes du CSV qui ne sont pas des colonnes de la table (en-tête brut, avant minuscules).
SERUM_NON_CSV_COLUMNS: Final = frozenset({"id", "created_at"})

# `*_output` vaut 1 quand la valeur de l'antigène atteint ce seuil.
SERUM_POSITIVE_THRESHOLD: Final = 500


class SerumProfile(StrEnum):
    """Stabilité du suivi. VARCHAR en base, pas un type enum PostgreSQL.

    A : toutes les spécificités stables. B : une partie fluctue. C : le suivi est très fluctuant.
    """

    CONSTANT = "A"
    INTERMEDIATE = "B"
    FLUCTUATING = "C"


SERUM_PROFILE_LABELS: Final[dict[SerumProfile, str]] = {
    SerumProfile.CONSTANT: "constant",
    SerumProfile.INTERMEDIATE: "intermédiaire",
    SerumProfile.FLUCTUATING: "fluctuant",
}


@dataclass(frozen=True)
class SerumAntigen:
    """Un antigène du CSV : son code (colonne), son libellé affiché, sa colonne de résultat."""

    code: str
    label: str
    output_code: str


SERUM_ANTIGENS: Final[tuple[SerumAntigen, ...]] = (
    SerumAntigen("b12", "B12", "b12_output"),
    SerumAntigen("b13", "B13", "b13_output"),
    SerumAntigen("dr53", "DR53", "dr53_output"),
    SerumAntigen("dr51", "DR51", "dr51_output"),
    SerumAntigen("dq10", "DQ10", "dq10_output"),
)
