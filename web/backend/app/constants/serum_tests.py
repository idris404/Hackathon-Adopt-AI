import uuid
from typing import Final

# Table `serum_tests` : une ligne de `data-model/data/serum_test_history.csv`.
SERUM_TESTS_TABLE_NAME: Final = "serum_tests"
PROFILE_MAX_LENGTH: Final = 16

# L'id d'un test est déduit du couple (`patient_id`, `test_date`) : relancer le seed
# retrouve la même ligne et ne crée pas de doublon.
SEED_SERUM_UUID_NAMESPACE: Final = uuid.UUID("c3a91e47-6b20-4f58-9d14-8e2a7c0b5f61")

# Colonnes du CSV qui ne sont pas des colonnes de la table (en-tête brut, avant minuscules).
SERUM_NON_CSV_COLUMNS: Final = frozenset({"id", "created_at"})
