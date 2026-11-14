import uuid
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Final

# Table `patient_history` : événements fictifs (greffe, accident, transfusion, autre pathologie,
# plus les étapes du parcours affichées sur la fiche). Pas de CSV : la liste ci-dessous.
PATIENT_HISTORY_TABLE_NAME: Final = "patient_history"
TITLE_MAX_LENGTH: Final = 80
DETAIL_MAX_LENGTH: Final = 200

# L'id d'un événement est déduit de `patient_id|code` : relancer le seed retrouve la même ligne.
SEED_HISTORY_UUID_NAMESPACE: Final = uuid.UUID("a7e4c1b2-8d30-4f19-9c55-1b6e0a4d7f82")


class HistoryKind(StrEnum):
    """Nature d'un événement. VARCHAR en base, pas un type enum PostgreSQL."""

    ILLNESS = "illness"
    ACCIDENT = "accident"
    TRANSFUSION = "transfusion"
    PREOP = "preop"
    GRAFT = "graft"
    POSTOP = "postop"
    CONSULTATION = "consultation"


@dataclass(frozen=True)
class DemoPatient:
    """Un des dix patients de démonstration.

    `listed_id` est l'UUID fourni pour ce patient : c'est `patients_synthetiques.id`
    (UUID v5 du `patient_id`), pas `patients.id`. L'historique est lié par `patient_id`.
    """

    listed_id: uuid.UUID
    patient_id: str
    graft_date: date


# Les dix UUID demandés, avec le `patient_id` et la date de greffe du CSV.
DEMO_PATIENTS: Final[tuple[DemoPatient, ...]] = (
    DemoPatient(uuid.UUID("166e3f06-d57f-519f-950d-465cb0ef1866"), "HIS-00055", date(2022, 5, 18)),
    DemoPatient(uuid.UUID("22489233-aaf4-5e73-8218-c8655a457dcd"), "SYN-0038", date(2015, 7, 10)),
    DemoPatient(uuid.UUID("361da500-1dce-5d26-96c3-fb3aa94ae19e"), "HIS-00355", date(2015, 8, 18)),
    DemoPatient(uuid.UUID("4d83a198-e2f5-5af6-9554-367281410d06"), "HIS-00073", date(2016, 3, 9)),
    DemoPatient(uuid.UUID("4e070832-2fd5-562e-9536-4614570aecf0"), "HIS-00407", date(2014, 1, 6)),
    DemoPatient(uuid.UUID("62da6611-9a33-5222-a414-c62e667b749c"), "SYN-0712", date(2020, 7, 28)),
    DemoPatient(uuid.UUID("6ebb4129-43e3-51fc-a5a0-85837095462d"), "HIS-00584", date(2018, 1, 8)),
    DemoPatient(uuid.UUID("d8cc7415-ffdc-5c13-ac3a-704d48e8430c"), "HIS-00485", date(2012, 3, 1)),
    DemoPatient(uuid.UUID("f1017696-468f-52d3-90b0-c0c54301e0d6"), "HIS-00047", date(2015, 11, 6)),
    DemoPatient(uuid.UUID("fa9c4d67-063a-50f6-a371-e0b27f846d65"), "HIS-00230", date(2014, 9, 18)),
)


@dataclass(frozen=True)
class HistoryEventSpec:
    """Un événement type, daté par rapport à la greffe du patient. Textes fictifs."""

    code: str
    kind: HistoryKind
    title: str
    detail: str
    years: int = 0
    days: int = 0


# Ordre chronologique une fois appliqué à une date de greffe.
HISTORY_EVENTS: Final[tuple[HistoryEventSpec, ...]] = (
    HistoryEventSpec(
        "illness",
        HistoryKind.ILLNESS,
        "Autre pathologie",
        "Néphropathie à IgA · exemple fictif",
        years=-6,
    ),
    HistoryEventSpec(
        "accident",
        HistoryKind.ACCIDENT,
        "Accident",
        "Traumatisme · exemple fictif",
        years=-3,
    ),
    HistoryEventSpec(
        "transfusion",
        HistoryKind.TRANSFUSION,
        "Transfusion",
        "Concentrés érythrocytaires · exemple fictif",
        years=-1,
    ),
    HistoryEventSpec(
        "preop",
        HistoryKind.PREOP,
        "Bilan préopératoire",
        "Avant transplantation · exemple fictif",
        days=-1,
    ),
    HistoryEventSpec(
        "graft",
        HistoryKind.GRAFT,
        "Greffe rénale",
        "Donneur décédé · ABO compatible · exemple fictif",
    ),
    HistoryEventSpec(
        "postop",
        HistoryKind.POSTOP,
        "Suivi postopératoire",
        "J7 · exemple fictif",
        days=7,
    ),
    HistoryEventSpec(
        "consultation",
        HistoryKind.CONSULTATION,
        "Prochaine consultation",
        "J10 · exemple fictif",
        days=10,
    ),
)
