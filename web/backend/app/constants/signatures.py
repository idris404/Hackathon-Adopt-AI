from typing import Final

from app.constants.serum_tests import SerumProfile

# Routes
SIGNATURES_ROUTER_PREFIX: Final = "/signatures"
SIGNATURES_ROUTER_TAG: Final = "signatures"
SIGN_QUEUE_PATH: Final = "/queue"
PATIENT_ALREADY_SIGNED_CODE: Final = "PATIENT_ALREADY_SIGNED"

# Table `patient_signatures` : une validation clinique par patient.
PATIENT_SIGNATURES_TABLE_NAME: Final = "patient_signatures"

# File « À signer » : les cas simples que l'algorithme traite seul et que le soignant valide.
# Un cas simple : profil sérique constant et un historique court.
SIGN_QUEUE_SIZE: Final = 5
SIGN_QUEUE_MAX_HISTORY_EVENTS: Final = 3
SIGN_QUEUE_PROFILE: Final = SerumProfile.CONSTANT
